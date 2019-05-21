import argparse
import os
import ftrace
from ftrace import Ftrace
from pandas import DataFrame

def execCmd(cmd):
    r = os.popen(cmd)
    text = r.read()
    r.close()
    return text