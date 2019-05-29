import os

CLUSTER_CFG = []
CLUSTER_RELATED_CPUS = {}
CLUSTER_AVAILABLE_FREQS = {}
ALL_CPUS = set()

def execCmd(cmd):
    r = os.popen(cmd)
    text = r.read()
    r.close()
    return text

# write "data" to file-filename
def writeFile(filename, data):
    f = open(filename, "w")
    f.write(data)
    f.close()

def init_phone_config():
    txt = execCmd('adb shell ls /sys/devices/system/cpu/cpufreq/')
    policys = txt.split()
    for policy in policys:
        related_cpus = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/related_cpus')
        # relative cpus for cluster
        CLUSTER_RELATED_CPUS[policy] = set();
        for cpu in (related_cpus.strip('\n').split()):
            CLUSTER_RELATED_CPUS[policy].add(int(cpu))
            ALL_CPUS.add(int(cpu))

        CLUSTER_CFG.append(policy)
        available_freqs = execCmd(
            'adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/scaling_available_frequencies')
        CLUSTER_AVAILABLE_FREQS[policy] = set()
        for freq in available_freqs.strip('\n').split():
            CLUSTER_AVAILABLE_FREQS[policy].add(int(freq))

        CLUSTER_RELATED_CPUS[policy] = sorted(CLUSTER_RELATED_CPUS[policy])
        CLUSTER_AVAILABLE_FREQS[policy] = sorted(CLUSTER_AVAILABLE_FREQS[policy])

def get_cluster_config():
    if 0 == len(CLUSTER_CFG):
        init_phone_config()
    return CLUSTER_CFG

def get_cluster_related_cpus():
    if 0 == len(CLUSTER_CFG):
        init_phone_config()
    return CLUSTER_RELATED_CPUS

def get_available_freqs():
    if 0 == len(CLUSTER_CFG):
        init_phone_config()
    return CLUSTER_AVAILABLE_FREQS

def get_all_cpus() :
    if 0 == len(CLUSTER_CFG):
        init_phone_config()
    return ALL_CPUS

def get_out_dir() :
    ABS_DIR = os.getcwd() + '/' + 'OUT'
    if False == os.path.exists(ABS_DIR):
        os.mkdir(ABS_DIR)
    return ABS_DIR

def get_out_systrace_path() :
    SYSTRACE_FILE = get_out_dir() + '/' + 'systrace.html'
    return SYSTRACE_FILE