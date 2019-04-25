import glob
import os
import sys
import ftrace
import argparse
from ftrace import Ftrace, Interval
from pandas import Series, DataFrame, MultiIndex, Timestamp
from pandas.tseries.offsets import Micro
import pandas as pd
import xlsxwriter
import time


############################### cpu config. wo need check################################
CLUSTER_CFG = ['LITTLE', 'BIG', 'SUPPER']
CLUSTER_CORE_MASK = [0X0F, 0X70, 0X80]
CLUSTER_AVAILABLE_FREQS = \
    {
        'LITTLE':[300000, 403200, 499200, 576000, 672000, 768000, 844800, 940800, 1036800, 1113600, 1209600,1305600, 1382400, 1478400, 1555200, 1632000, 1708800, 1785600],
        'BIG':[710400, 825600, 940800, 1056000, 1171200, 1286400, 1401600, 1497600, 1612800, 1708800, 1804800, 1920000, 2016000, 2131200, 2227200, 2323200, 2419200],
        'SUPPER':[825600, 940800, 1056000, 1171200, 1286400, 1401600, 1497600, 1612800, 1708800, 1804800, 1920000, 2016000, 2131200, 2227200, 2323200, 2419200, 2534400, 2649600, 2745600, 2841600]
     }

LITTLE_CPUS = ftrace.common.unpack_bitmap(CLUSTER_CORE_MASK[CLUSTER_CFG.index('LITTLE')])
BIG_CPUS = ftrace.common.unpack_bitmap(CLUSTER_CORE_MASK[CLUSTER_CFG.index('BIG')])
SUPPER_CPUS = ftrace.common.unpack_bitmap(CLUSTER_CORE_MASK[CLUSTER_CFG.index('SUPPER')])
ALL_CPUS = (LITTLE_CPUS.union(BIG_CPUS)).union(SUPPER_CPUS)

ABS_DIR = os.getcwd() + '/' + 'OUT'

XML_FILE_NAME = 'systrace-{DATE}.xlsx'.format(DATE=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))

ABS_PATH = ABS_DIR + '/' + XML_FILE_NAME

############################### cpu config. wo need check################################


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

    parser.add_argument('-f', '--file', dest='file',
                        help='File (systrace/ftrace log) to parse')

    args = parser.parse_args()

    trace = Ftrace(args.file)
    total_duration = trace.duration

    # Multi-core usage
    sb_all = DataFrame(columns=ALL_CPUS)
    arrays = [['SUPPER']*2 + ['BIG']*4 + ['LITTLE']*5, range(2) + range(4) + range(5)]
    multi_index = MultiIndex.from_tuples(list(zip(*arrays)), names=['cluster', 'num_cores'])
    sb_by_cluster = DataFrame(index=multi_index)

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

    writer = pd.ExcelWriter(ABS_PATH, engine='openpyxl')
    for cpu in ALL_CPUS: # assumes 8-cores
        # top tasks
        df_tasks = DataFrame(columns=['Name', 'PID', 'Priority', 'Exec Time (s)'])
        for task in trace.cpu.seen_tasks(cpu=cpu):
            if task.pid != 0:
                df_tasks.loc[task.pid] = [task.name,
                    task.pid, task.prio,
                        trace.cpu.task_time(task=task, cpu=cpu,
                                            interval=None)]
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
    for cpu in range(8):
        for lpm in trace.cpu.lpm_intervals(cpu=cpu, interval=None):
            df_lpm.loc[cpu, LPM_states[lpm.state]] += lpm.interval.duration
        # accounting for time in idle loop.
        df_lpm.loc[cpu, 'Busy'] = total_duration - df_lpm.loc[cpu].sum()

    df_lpm = df_lpm / total_duration
    df_lpm.to_excel(writer, sheet_name='LPM')
    writer.save()

    # Multi-core usage
    sb_all.loc[trace.filename] = sim_busy_all_clusters(trace)
    supper_sim_usage = sim_busy_by_clusters(trace, cpus=SUPPER_CPUS)
    big_sim_usage = sim_busy_by_clusters(trace, cpus=BIG_CPUS)
    little_sim_usage = sim_busy_by_clusters(trace, cpus=LITTLE_CPUS)

    merged = supper_sim_usage.append(big_sim_usage)
    merged = merged.append(little_sim_usage)
    merged.index = multi_index
    sb_by_cluster['usage'] = merged
    sb_by_cluster.to_excel(writer, sheet_name='summary_by_cluster')
    writer.save()
    sb_all.to_excel(writer, sheet_name='summary_all_cluster')
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

    df_clk = df_clk / total_duration
    #df_clk.sort_values(axis=1, inplace=True)
    df_clk.to_excel(writer, sheet_name='CLOCK')
    writer.sheets['CLOCK'].column_dimensions['A'].width = 25
    writer.sheets['CLOCK'].column_dimensions['B'].width = 15
    writer.sheets['CLOCK'].column_dimensions['C'].width = 15
    writer.sheets['CLOCK'].column_dimensions['D'].width = 15
    writer.sheets['CLOCK'].column_dimensions['E'].width = 15
    writer.sheets['CLOCK'].column_dimensions['F'].width = 15
    writer.sheets['CLOCK'].column_dimensions['G'].width = 15
    writer.sheets['CLOCK'].column_dimensions['H'].width = 15
    writer.sheets['CLOCK'].column_dimensions['I'].width = 15
    writer.sheets['CLOCK'].column_dimensions['J'].width = 15
    writer.sheets['CLOCK'].column_dimensions['K'].width = 15
    writer.sheets['CLOCK'].column_dimensions['L'].width = 15
    writer.sheets['CLOCK'].column_dimensions['M'].width = 15
    writer.sheets['CLOCK'].column_dimensions['N'].width = 15
    writer.sheets['CLOCK'].column_dimensions['O'].width = 15
    writer.sheets['CLOCK'].column_dimensions['P'].width = 15
    writer.sheets['CLOCK'].column_dimensions['Q'].width = 15
    writer.save()

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

    FREQ_ALL_CORES_RAW = [300000, 403200, 499200, 576000, 672000, 768000, 844800, 940800, 1036800, 1113600, 1209600,
                          1305600, 1382400, 1478400, 1555200, 1632000, 1708800, 1785600
        , 710400, 825600, 940800, 1056000, 1171200, 1286400, 1401600, 1497600, 1612800, 1708800, 1804800, 1920000,
                          2016000, 2131200, 2227200, 2323200, 2419200
        , 825600, 940800, 1056000, 1171200, 1286400, 1401600, 1497600, 1612800, 1708800, 1804800, 1920000, 2016000,
                          2131200, 2227200, 2323200, 2419200, 2534400, 2649600, 2745600, 2841600]

    FREQ_ALL_CORES = []
    for i in FREQ_ALL_CORES_RAW:
        if not i in FREQ_ALL_CORES:
            FREQ_ALL_CORES.append(i)
    FREQ_ALL_CORES.sort()
    print FREQ_ALL_CORES

    df_freq = DataFrame(index=ALL_CPUS, columns=FREQ_ALL_CORES)

    df_freq.fillna(0, inplace=True)
    for cpu in ALL_CPUS:
        for busy_interval in trace.cpu.busy_intervals(cpu=cpu):

            for freq in trace.cpu.frequency_intervals(cpu=cpu, interval=busy_interval.interval):
                df_freq.loc[cpu, freq.frequency] += freq.interval.duration
    df_freq.to_excel(writer, sheet_name='CoreFreqStats')
    writer.save()