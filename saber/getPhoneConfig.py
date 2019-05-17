import os
import sys
import csv
import openpyxl
import pandas as pd
from pandas import Series, DataFrame, MultiIndex, Timestamp


ABS_DIR = os.getcwd() + '/data/'

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


if __name__ == '__main__':

    if False == os.path.exists(ABS_DIR):
        os.mkdir(ABS_DIR)

    os.system('adb root')
    # read cpu freq info
    txt =  execCmd('adb shell ls /sys/devices/system/cpu/cpufreq/')
    policys = txt.split()
    policyConfig = {}
    governorConfig = {}

    for policy in policys:
        txt = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/scaling_available_frequencies')
        policyConfig[policy] = txt.split()

    with open(ABS_DIR + 'cpufreqinfo.csv', 'wb') as f:
        w = csv.DictWriter(f, policyConfig.keys())
        w.writeheader()
        w.writerow(policyConfig)


    ABS_PATH = ABS_DIR  + 'RESULT' + '_' + 'test.xlsx'
    writer = pd.ExcelWriter(ABS_PATH, engine='openpyxl')

    governorTmp = {}
    governorConfig = {}
    governorSeries = []
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
                    content = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/schedutil/' + schedutilDir)
                    governorTmp ['schedutil_' + schedutilDir] = content.strip('\n')
                continue

            content = execCmd('adb shell cat /sys/devices/system/cpu/cpufreq/' + policy + '/' + sub)
            governorTmp[sub] = content.strip('\n')

        ssss = DataFrame(data=governorTmp.values(), index=governorTmp.keys())
        print ssss
        if os.path.exists(ABS_PATH):
            writer = pd.ExcelWriter(ABS_PATH, mode='a', engine='openpyxl')
        ssss.to_excel(writer, sheet_name=policy)
        writer.save()
        governorSeries.append(ssss)
        governorConfig[policy] = governorTmp


    # os.system('adb shell ls /sys/devices/system/cpu/cpufreq/')
    # print log.messages

