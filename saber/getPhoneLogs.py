import glob
import os
import sys
import ftrace
import argparse
import time
from ftrace import Ftrace, Interval
from pandas import Series
from saber_common import execCmd
from saber_common import get_out_systrace_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='get atrace/ddr/gpu/snoc logs')
    parser.add_argument('-t', '--time', dest='time', help='hope to capture time')
    args = parser.parse_args()
    print args.time

    # check system/bin/ddr_clock_read.sh. if dont , push it to phone
    os.system('adb root')
    # clear phone /data/local/tmp/

    os.system('adb shell rm -r /data/local/tmp/')
    os.system('adb shell mkdir /data/local/tmp/')

    # clear pc tmp dir
    os.system('rm -r ./data/tmp/')

    status = os.system('adb shell ls /system/bin/ |grep -i ddr_clock_read.sh')
    if status != 0:
        txt = execCmd('adb push ./toolsForAndroid/ddr_clock_read.sh    /system/bin/')
        if 'Read-only file system' in txt:
            txt = execCmd('adb root')
            print txt
            txt = execCmd('adb disable-verity')
            print txt
            os.system('adb reboot')
            time.sleep(60)
            os.system('adb root')
            os.system('adb remount')
            txt = execCmd('adb push ./toolsForAndroid/ddr_clock_read.sh    /system/bin/')
        os.system('adb shell chmod a+x /system/bin/ddr_clock_read.sh')

    status = os.system('adb shell ls /system/bin/ |grep -i snoc_clock_read.sh')
    if status != 0:
        os.system('adb push ./toolsForAndroid/snoc_clock_read.sh /system/bin/')
        os.system('adb shell chmod a+x /system/bin/snoc_clock_read.sh')

    status = os.system('adb shell ls /system/bin/ |grep -i gpu_clock_read.sh')
    if status != 0:
        os.system('adb push ./toolsForAndroid/gpu_clock_read.sh /system/bin/')
        os.system('adb shell chmod a+x /system/bin/gpu_clock_read.sh')

    # clear /data/local/tmp/
    # ddr freq analysis

    # start get data
    CATEGORYS = 'gfx input view webview wm am sm audio video hal res dalvik rs bionic ' \
          ' power pm ss database network adb aidl sched irq freq ' \
          ' idle disk  memreclaim workq regulators binder_driver binder_lock '

    CMD = 'adb shell atrace  -b 10240 -t '\
          + args.time + ' -o /data/local/tmp/atrace.out ' + CATEGORYS + ' & '
    os.system(CMD)
    os.system('adb shell ./system/bin/ddr_clock_read.sh -i 1 -t ' + args.time + ' -o & ')
    os.system('adb shell ./system/bin/snoc_clock_read.sh -i 1 -t ' + args.time + ' -o & ')
    os.system('adb shell ./system/bin/gpu_clock_read.sh -i 1 -t ' + args.time + ' -o & ')

    # wait for data is out
    time.sleep(int(args.time) + 20 )

    # get all data for data/local/tmp
    os.system('adb pull /data/local/tmp/  ./data/')

    # use systrace.py to vert atrace.out to systrace.html
    os.system('python ./toolsForAndroid/systrace/systrace.py --from-file ./data/tmp/atrace.out -o ' + get_out_systrace_path())