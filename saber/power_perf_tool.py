import glob
import os
import types
import sys
import ftrace
import argparse
from ftrace import Ftrace, Interval
from pandas import Series, DataFrame, MultiIndex, Timestamp
from pandas.tseries.offsets import Micro
import pandas as pd
import openpyxl
from openpyxl import load_workbook
from openpyxl.styles import Font, colors, Alignment, numbers
import time


############################### cpu config. wo need check################################

ABS_DIR = os.getcwd() + '/' + 'OUT'

XML_FILE_NAME = 'systrace-{DATE}.xlsx'.format(DATE=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
SYSTRACE_FILE =ABS_DIR + '/' + 'systrace.html'

############################### cpu config. wo need check################################

def execCmd(cmd):
    r = os.popen(cmd)
    text = r.read()
    r.close()
    return text

def sim_busy_all_clusters(trace):
    """
    Returns DataFrame of simultaneously busy cores irrespectively of cluster.
    """
    data = {num_cores: trace.cpu.simultaneously_busy_time(num_cores, interval=None) for num_cores in xrange(len(ALL_CPUS)+1)}
    # total_duration = trace.duration if not INTERVAL else INTERVAL.duration
    return Series(data=data.values(), index=data.keys(), name=trace.filename) / total_duration

def sim_busy_by_clusters(trace, cpus):
    """
    Returns Series of simultaneously busy cores per `cpus` in cluster.
    """
    data = {num_cores: trace.cpu.simultaneously_busy_time(num_cores, cpus=list(cpus), interval=None) for num_cores in xrange(len(cpus)+1)}
    #total_duration = trace.duration if not INTERVAL else INTERVAL.duration
    return Series(data=data.values(), index=data.keys(), name=trace.filename) / total_duration

def parse_file(filepath):
    trace = Ftrace(filepath)
    return (filepath, trace)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Power/Performance analysis of HMP platforms!')

    parser.add_argument('-t', '--time', dest='time',
                        help='hope to capture how long logs')

    args = parser.parse_args()

    #get phone config
    #os.system('python getPhoneConfig.py')

    #get all logs for analysis
    os.system('python getPhoneLogs.py -t ' + args.time)

    if os.path.exists(SYSTRACE_FILE):
        trace = Ftrace(SYSTRACE_FILE)
    else:
        print 'error'
        exit(1)

    total_duration = trace.duration


    txt = execCmd('adb shell ls /sys/devices/system/cpu/cpufreq/')
    policys = txt.split()

    CLUSTER_CFG = []
    CLUSTER_RELATED_CPUS = {}
    CLUSTER_AVAILABLE_FREQS = {}
    ALL_CPUS = set()
    for policy in policys:
        related_cpus = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/related_cpus')
        # relative cpus for cluster
        CLUSTER_RELATED_CPUS[policy] = set();
        for cpu in (related_cpus.strip('\n').split()):
            CLUSTER_RELATED_CPUS[policy].add(int(cpu))
            ALL_CPUS.add(int(cpu))

        CLUSTER_CFG.append(policy)
        available_freqs = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/scaling_available_frequencies')
        CLUSTER_AVAILABLE_FREQS[policy] = set()
        for freq in available_freqs.strip('\n').split():
            CLUSTER_AVAILABLE_FREQS[policy].add(int(freq))

        CLUSTER_RELATED_CPUS[policy]=sorted(CLUSTER_RELATED_CPUS[policy])
        CLUSTER_AVAILABLE_FREQS[policy]=sorted(CLUSTER_AVAILABLE_FREQS[policy])

    # Multi-core usage
    sb_all = DataFrame(columns=ALL_CPUS)

    # Freq
    df_freq = DataFrame(index = ALL_CPUS)
    df_freq.fillna(0, inplace=True)

    # LPM
    LPM_states = {-1: 'Busy', 0: 'WFI', 1: 'Retention', 2: 'SPC (GDHS)', 3: 'PC'}
    df_lpm = DataFrame(index=ALL_CPUS, columns= LPM_states.values())
    df_lpm.fillna(0, inplace=True)

    # CLock Active
    df_clk = DataFrame(index=trace.clock.names, columns = ['0', 'UNKNOWN'])
    df_clk.fillna(0, inplace=True)

    if False == os.path.exists(ABS_DIR):
        os.mkdir(ABS_DIR)


    ABS_PATH = ABS_DIR + '/' + 'RESULT' + '_' + XML_FILE_NAME
    writer = pd.ExcelWriter(ABS_PATH, engine='openpyxl')

    for cpu in ALL_CPUS: # assumes 8-cores
        # top tasks
        df_tasks = DataFrame(columns=['Name', 'PID', 'Priority', 'Exec Time (s)'])
        for task in trace.cpu.seen_tasks(cpu=cpu):
            if task.pid != 0:
                df_tasks.loc[task.pid] = [task.name,
                    task.pid, task.prio,
                        trace.cpu.task_time(task=task, cpu=cpu, interval=None)]

        busy_time = trace.cpu.busy_time(cpu=cpu, interval=None)
        if busy_time != 0.0:
            df_tasks['Exec Time %'] = df_tasks['Exec Time (s)'] / busy_time

        df_tasks.sort_values(['Exec Time (s)'], inplace=True, ascending=False)
        df_tasks.set_index('PID', inplace=True)
        if os.path.exists(ABS_PATH):
            writer = pd.ExcelWriter(ABS_PATH, mode='a', engine='openpyxl')
        df_tasks.to_excel(writer, sheet_name='top_tasks_cpu{cpu}'.format(cpu=cpu))
        writer.sheets['top_tasks_cpu{cpu}'.format(cpu=cpu)].column_dimensions['B'].width=25
        writer.sheets['top_tasks_cpu{cpu}'.format(cpu=cpu)].column_dimensions['D'].width=15
        writer.sheets['top_tasks_cpu{cpu}'.format(cpu=cpu)].column_dimensions['E'].width=15
        writer.save()

    # LPM
    for cpu in ALL_CPUS:
        for lpm in trace.cpu.lpm_intervals(cpu=cpu, interval=None):
            df_lpm.loc[cpu, LPM_states[lpm.state]] += lpm.interval.duration
        # accounting for time in idle loop.
        df_lpm.loc[cpu, 'Busy'] = total_duration - df_lpm.loc[cpu].sum()

    df_lpm = df_lpm / total_duration
    df_lpm.to_excel(writer, sheet_name='LPM')
    writer.save()

    # Multi-core usage
    sb_all.loc[trace.filename] = sim_busy_all_clusters(trace)
    sb_all.to_excel(writer, sheet_name='summary_all_cluster')
    writer.save()

    cluster_usage = []
    arrays_a = []
    arrays_b = []
    for idx in range(0, len(CLUSTER_CFG)) :
        if CLUSTER_CFG[idx] in CLUSTER_RELATED_CPUS.keys():
            RELATER_CPUS_SET = CLUSTER_RELATED_CPUS.get(CLUSTER_CFG[idx])
            RELATER_CPUS_SET_SORTS = sorted(RELATER_CPUS_SET)
        cluster_usage.append(sim_busy_by_clusters(trace, cpus=RELATER_CPUS_SET_SORTS))
        arrays_a.extend([CLUSTER_CFG[idx]]*(len(RELATER_CPUS_SET_SORTS) + 1))
        arrays_b.extend(range(len(RELATER_CPUS_SET_SORTS) + 1))

    arrays = [arrays_a, arrays_b]
    multi_index = MultiIndex.from_tuples(list(zip(*arrays)), names=['cluster', 'num_cores'])
    sb_by_cluster = DataFrame(index=multi_index)

    merged = cluster_usage[1].append(cluster_usage[0])
    merged.index = multi_index

    sb_by_cluster['usage'] = merged
    sb_by_cluster.to_excel(writer, sheet_name='summary_by_cluster')
    writer.save()


    for clk in trace.clock.names:
        for clk_event in trace.clock.clock_intervals(clock=clk, state=ftrace.clock.ClockState.ENABLED, interval=None):
            for freq_event in trace.clock.frequency_intervals(clock=clk, interval=clk_event.interval):
                freq = 'UNKNOWN' if freq_event.frequency == -1 else freq_event.frequency
                if not freq in df_clk.columns:
                  df_clk[freq] = 0 # assign it
                df_clk.loc[clk, freq] += freq_event.interval.duration

        for clk_event in trace.clock.clock_intervals(clock=clk, state=ftrace.clock.ClockState.DISABLED, interval=None):
            df_clk.loc[clk, '0'] += clk_event.interval.duration

        if df_clk.loc[clk].sum() != total_duration: # unaccounted.
            df_clk.loc[clk, 'UNKNOWN'] = total_duration - df_clk.loc[clk].sum()


    df_clk = df_clk/total_duration

    # for a
    for indexs in df_clk.columns:
        print df_clk[indexs]
    #df_clk.sort_values(axis=1, inplace=True)
    df_clk.to_excel(writer, sheet_name='CLOCK')
    writer.save()
    # set disaplay format for percent
    wb = load_workbook(ABS_PATH)
    a_sheet = wb.get_sheet_by_name('CLOCK')
    a_sheet.row_dimensions[2].height = 40
    a_sheet['C4'] = '0.77'
    a_sheet['C4'].number_format=''
    a_sheet.sheet_properties.tabColor = "1072BA"
    a_sheet['B4']=1000

    # frame rate
    frame_durations = Series((event.interval.duration for event in trace.android.render_frame_intervals(interval=None)))
    # frame_durations = frame_durations * 1000. # to milliseconds
    summary = frame_durations.describe()
    summary['90%'] = frame_durations.quantile(.9)
    summary['Janks'] = trace.android.num_janks(interval=None)
    summary['Janks Per Second'] = summary['Janks']/trace.duration
    summary['Average FPS'] = trace.android.framerate(interval=None)
    summary.to_excel(writer, sheet_name='FrameStats')
    writer.sheets['FrameStats'].column_dimensions['A'].width = 15
    writer.save()

    #parse_core_frequencies

    for cluster in CLUSTER_CFG :
        df_freq = DataFrame(index=CLUSTER_RELATED_CPUS[cluster], columns=CLUSTER_AVAILABLE_FREQS[cluster])
        df_freq.fillna(0, inplace=True)
        for cpu in CLUSTER_RELATED_CPUS[cluster]:
            for busy_interval in trace.cpu.busy_intervals(cpu=cpu):
                for freq in trace.cpu.frequency_intervals(cpu=cpu, interval=busy_interval.interval):
                    df_freq.loc[cpu, freq.frequency] += freq.interval.duration
            df_freq.to_excel(writer, sheet_name='CoreFreqStats' + cluster)
            writer.save()

    # find ddr log
    files = os.listdir('./data/tmp/')
    for file in files:
        if 'ddr' in file:
            ddr_freq_file = file
            print 'ddr log is ' + ddr_freq_file

    ddr_freq_data = [];

    with open(os.getcwd() + '/' + 'data/tmp/' + ddr_freq_file) as f:
        for line in f.readlines():
            ddr_freq_tmp_data = line.split(':');
            if ddr_freq_tmp_data.__len__() != 2 :
                continue
            time = ddr_freq_tmp_data[0];
            freq = ddr_freq_tmp_data[1];

            ddr_freq_data.append((int(time), int(freq)));

    ddr_freq = DataFrame(ddr_freq_data, columns=['time','freq'])
    ddr_freq.to_excel(writer, sheet_name='DDRFreq')
    writer.sheets['DDRFreq'].column_dimensions['B'].width = 25
    writer.sheets['DDRFreq'].column_dimensions['C'].width = 25
    writer.save()

    # find snoc  log
    for file in files:
        if 'snoc' in file:
            snoc_freq_file = file
            print 'snoc log is ' + snoc_freq_file

    snoc_freq_data = [];

    with open(os.getcwd() + '/' + 'data/tmp/' + snoc_freq_file) as f:
        for line in f.readlines():
            snoc_freq_tmp_data = line.split(':');
            if snoc_freq_tmp_data.__len__() != 2 :
                continue
            time = snoc_freq_tmp_data[0];
            freq = snoc_freq_tmp_data[1];

            snoc_freq_data.append((int(time), int(freq)));

    snoc_freq = DataFrame(snoc_freq_data, columns=['time','freq'])
    snoc_freq.to_excel(writer, sheet_name='SNOCFreq')
    writer.sheets['SNOCFreq'].column_dimensions['B'].width = 25
    writer.sheets['SNOCFreq'].column_dimensions['C'].width = 25
    writer.save()

    # find snoc  log
    for file in files:
        if 'gpu' in file:
            gpu_freq_file = file
            print 'gpu log is ' + gpu_freq_file

    gpu_freq_data = [];

    with open(os.getcwd() + '/' + 'data/tmp/' + gpu_freq_file) as f:
        for line in f.readlines():
            gpu_freq_tmp_data = line.split(':');
            if gpu_freq_tmp_data.__len__() != 2:
                continue
            time = gpu_freq_tmp_data[0];
            freq = gpu_freq_tmp_data[1];

            gpu_freq_data.append((int(time), int(freq)));

    gpu_freq = DataFrame(gpu_freq_data, columns=['time', 'freq'])
    gpu_freq.to_excel(writer, sheet_name='GpuFreq')
    writer.sheets['GpuFreq'].column_dimensions['B'].width = 25
    writer.sheets['GpuFreq'].column_dimensions['C'].width = 25
    writer.save()

    # governor config
    txt = execCmd('adb shell ls /sys/devices/system/cpu/cpufreq/')
    policys = txt.split()

    governorTmp = {}
    governorConfig = {}
    for policy in policys:
        txt = execCmd('adb shell ls /sys/devices/system/cpu/cpufreq/' + policy)
        subs = txt.split()
        for sub in subs:
            if 'stats' in sub:
                continue
            if 'schedutil' in sub:
                txt = execCmd('adb shell ls /sys/devices/system/cpu/cpufreq/' + policy + '/' + sub)
                schedutilDirs = txt.split()
                for schedutilDir in schedutilDirs:
                    content = execCmd(
                        'adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/schedutil/' + schedutilDir)
                    governorTmp['schedutil_' + schedutilDir] = content.strip('\n')
                continue

            content = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/' + sub)
            governorTmp[sub] = content.strip('\n')
        tmp = DataFrame(data=governorTmp.values(), index=governorTmp.keys())
        tmp.to_excel(writer, sheet_name='Governor_' + policy)
        writer.sheets['Governor_' + policy].column_dimensions['A'].width = 35
        writer.sheets['Governor_' + policy].column_dimensions['B'].width = 35
        writer.save()
        governorConfig[policy] = governorTmp

    # schedule config
    txt = execCmd('adb shell ls /proc/sys/kernel/')
    subs = txt.split()
    schedDirs = []
    for sub in subs :
        if 'sched' in sub:
            if 'sched_domain' in sub:
                continue
            schedDirs.append(sub)

    scheduConfig = {}
    for schedsub in schedDirs:
        txt = execCmd('adb shell cat /proc/sys/kernel/' + schedsub)
        scheduConfig[schedsub] = txt.strip('\n')
    temSched = DataFrame(data=scheduConfig.values(), index=scheduConfig.keys())
    temSched.to_excel(writer, sheet_name='Schedule')
    writer.sheets['Schedule'].column_dimensions['A'].width = 35
    writer.sheets['Schedule'].column_dimensions['B'].width = 35
    writer.save()

