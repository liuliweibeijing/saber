import argparse
import ftrace
from ftrace import Ftrace
from pandas import DataFrame

LITTLE_CLUSTER_MASK = 0x0F
BIG_CLUSTER_MASK = 0xF0

LITTLE_CPUS = ftrace.common.unpack_bitmap(LITTLE_CLUSTER_MASK)
BIG_CPUS = ftrace.common.unpack_bitmap(BIG_CLUSTER_MASK)
ALL_CPUS = LITTLE_CPUS.union(BIG_CPUS)


FREQ_ALL_CORES_RAW = [300000, 403200, 499200, 576000, 672000, 768000, 844800, 940800, 1036800, 1113600, 1209600, 1305600, 1382400, 1478400, 1555200, 1632000, 1708800, 1785600
                  , 710400, 825600, 940800, 1056000, 1171200, 1286400, 1401600, 1497600, 1612800, 1708800, 1804800, 1920000, 2016000, 2131200, 2227200, 2323200, 2419200
                  ,825600, 940800, 1056000, 1171200, 1286400, 1401600, 1497600, 1612800, 1708800, 1804800, 1920000, 2016000, 2131200,2227200, 2323200, 2419200, 2534400, 2649600, 2745600, 2841600]


FREQ_ALL_CORES = []
for i in FREQ_ALL_CORES_RAW:
    if not i in FREQ_ALL_CORES:
        FREQ_ALL_CORES.append(i)
FREQ_ALL_CORES.sort()
print FREQ_ALL_CORES


parser = argparse.ArgumentParser(description='Per-core frequencies')

parser.add_argument('-f', '--file', dest='file',
                    help='File to parse')

args = parser.parse_args()

trace = Ftrace(args.file)

df_freq = DataFrame(index = ALL_CPUS, columns=FREQ_ALL_CORES)

df_freq.fillna(0, inplace=True)
for cpu in ALL_CPUS:
    for busy_interval in trace.cpu.busy_intervals(cpu=cpu):

        for freq in trace.cpu.frequency_intervals(cpu=cpu, interval=busy_interval.interval):

            df_freq.loc[cpu, freq.frequency] += freq.interval.duration

df_freq.to_html(r'parse_core_frequencies_stats.html')