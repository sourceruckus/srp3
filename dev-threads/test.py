#!/usr/bin/python

import os, sys, time

import status


def run_it(x):
    rate=0.01
    num=0
    while num < 100:
        x.update()
        num = num + 1
        time.sleep(rate)
    x.update(1)


def run_it_percent(x):
    rate=0.01
    num=0.0
    done=0
    while not done:
        p = int(num*100)
        x.update(p)
        if p == 100:
            done=1
        else:
            num = num + 0.01
            time.sleep(rate)


#----------------------------------------------------------------------
print "hello"


line = status.spinner()
run_it(line)
line = status.line()
run_it_percent(line)
line = status.spinner_line()
run_it_percent(line)


#line.update(95)
