"""pawns -
this module contains classes for lowly peon objects...  tell 'em what to do,
and they do it.  ;-)

generally, these objects are used to interface with the operating system and
they just wrap nicely around commands.getstatusoutput() for the most part.

classes:

worker -- executes a command within the current thread
worker_thread -- executes a command in a new thread
"""

import os, sys
import commands
import time
import thread
import string
import status


class worker:
    """worker(command[, label, cols, output])
    this class takes a command, runs it, and gives some feedback when the
    command is done.
    
    optional arguments:
        label: a heading for the status line (default: \"working...\")
        cols: how many columns on your terminal (default: autodetected)
        output: open logfile to append worker output to (default: none)
    
    available methods:
        go() -> status
    """
    
    def __init__(self, command, label="working...", cols="", output=""):
        """__init__(command[, label, cols, output])
        """
        self.command = command
        self.label = label
        if cols:
            self.cols = cols
        else:
            try:
                self.cols = os.environ['COLUMNS']
            except:
                status = commands.getstatusoutput("stty -a")
                if status[0] != 0:
                    self.cols = 80
                else:
                    self.cols = int(status[1].split(';')[2].split()[1])
        
        if len(self.label) >= (self.cols - 11):
            self.label = "working"
            
        self.output = output
        self.status = []
    
    
    def info(self):
        """info()
        """
        print "----- worker object info -----"
        print "%s%s" % (string.ljust("command:", 10), self.command)
        print "%s%s" % (string.ljust("label:", 10), self.label)
        print "%s%s" % (string.ljust("cols:", 10), self.cols)
        print "%s%s" % (string.ljust("output:", 10), self.output)
    
        
    def go(self):
        """go() -> status
        this tells our worker instance to go
        retval: 1 = success, 0 = failure
        """
        sys.stdout.write(string.ljust(self.label, self.cols-11))
        sys.stdout.flush()
        
        self.status = commands.getstatusoutput(self.command)
        
        # write output to log file, if specified
        if self.output:
            self.output.writelines(self.status[1])
            self.output.write("\n")
            
        # display status of command
        if self.status[0] == 0:
            print "[  done  ]"
            return 1
        else:
            print "[ failed ]"
            return 0


class worker_thread(worker):
    """worker_thread(command[, label, cols, output, hz])
    this class takes a command, fires off a worker thread, and gives
    some feedback while the thread is working.
    
    optional arguments:
        label: a heading for the status line (default: \"working:\")
        cols: how many columns on your terminal (default: autodetected)
        output: open logfile to append worker output to (default: none)
        hz: full spinner rotations per second (default: 2)
    
    available methods:
        go() -> status
    """
    
    def __init__(self, command, label="working:", cols="", output="", hz=2):
        """__init__(command[, label, cols, output, hz])
        """
        worker.__init__(self, command, label, cols, output)
        
        self.hz = hz
        self.done = 0
        self.status = []
        self.lock = thread.allocate_lock()
        
    
    def info(self):
        """info()
        """
        worker.info(self)
        print "%s%s" % (string.ljust("hz:", 10), self.hz)
    
    
    def work(self):
        """work()
        this function gets passed to the thread
        DO NOT CALL THIS METHOD DIRECTLY
        """
        self.lock.acquire()
        self.status = commands.getstatusoutput(self.command)
        self.done = 1
        self.lock.release()
    
    
    def go(self):
        """go() -> status
        this tells our worker_thread instance to go
        retval: 1 = success, 0 = failure
        """
        # fire off our thread
        id = thread.start_new_thread(self.work, ())
        
        line = status.spinner(cols=self.cols, head=self.label)
        
        sleeptime = 1.0/(self.hz * (len(line.spinner) - 1))
        while not self.done:
            line.update()
            time.sleep(sleeptime)

        # write output to log file, if specified
        if self.output:
            self.output.writelines(self.status[1])
            self.output.write("\n")
        
        # display status of thread
        if self.status[0] == 0:
            line.update(1)
            return 1
        else:
            line.tail = "[ failed ]"
            line.update(1)
            return 0



