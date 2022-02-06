# builtin libs
# import sys
import subprocess
# import os
# import threading
import time

# PyQt5 libs
from PyQt5 import QtCore

# time profiler decorator
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print ('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed

# A wrapper for a QtCore.pyqtSignal(str) used by Ticker and ShellCommandsRunner
class Signal(QtCore.QObject):
    signal = QtCore.pyqtSignal(str)

# A thread that ticks every 'interval' seconds if started or 0.1 seconds otherwise
class Ticker(QtCore.QRunnable):
    def __init__(self, interval):
        super(Ticker, self).__init__()
        self.interval = interval
        self.signal = Signal()
        self.is_active = False  # while button is pressed
        self.is_busy = False # while photo is taken, camera is busy
        self.kill_me_ASAP = False

    def setInteval(self, interval):
        self.interval = interval

    def run(self):
        while True:
            if self.kill_me_ASAP: return()
            if self.is_active and not self.is_busy:
                self.signal.signal.emit(str(True))
                time.sleep(self.interval)
            else:
                time.sleep(0.1) # reduce cpu load


    def kill(self):
        self.kill_me_ASAP = True


    def cancel(self):
        self.is_active = False

    def start(self):
        self.is_active = True

    def busy(self):
        self.is_busy = True

    def ready(self):
        self.is_busy = False

# A thread executes shell commands and signals when finished
class ShellCommandsRunner(QtCore.QRunnable):
    def __init__(self, commands):
        super(ShellCommandsRunner, self).__init__()
        self.commands = commands
        self.signal = Signal()
        self.is_active = False  # while it is usable
        self.is_busy = False # while photo is taken, camera is busy

    def setCommands(self, commands):
        self.commands = commands

    def run(self):
        if not self.is_active: return()
        if self.is_busy: return()
        self.busy()
        for cmd in self.commands:
            print(cmd)
            proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            o, e = proc.communicate()
            # print('Output: ' + o.decode('ascii'))
            # print('Errors: ' + e.decode('ascii'))
            # break

        self.ready()
        self.signal.signal.emit(str(True))


    def cancel(self):
        self.is_active = False

    def start(self):
        self.is_active = True

    def busy(self):
        self.is_busy = True

    def ready(self):
        self.is_busy = False
