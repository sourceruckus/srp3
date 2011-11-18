#!/usr/bin/python

import os

from features import *
import toc
import trackfiles

# generate list of funcs for install
install_funcs = get_function_list("inst", ["trackfiles"])
print install_funcs
print "\n\n"

# walk fs node calling funcs
for path, dirs, files in os.walk("FOO"):
    if files:
        for f in files:
            fname = os.path.join(path, f)
            print fname
            for func in install_funcs:
                print "%s(%s)" % (func, fname)
                func(fname)

print "\n\n"

print "contents of toc"
print toc.data


