#!/usr/bin/env python3

import os
import sys
from pprint import pprint

import srp
import srp.features.trackfiles

pprint(srp.registered_features)
print("\n\n")

# generate list of funcs for install
#install_funcs = srp.get_function_list("install", ["trackfiles"])
install_funcs = srp.get_function_list("install")
for x in install_funcs:
    print(x.name)
print("\n\n")

# walk fs node calling funcs
for path, dirs, files in os.walk("FOO"):
    if files:
        for f in files:
            fname = os.path.join(path, f)
            print(fname)
            for f in install_funcs:
                print("%s(%s)" % (f.func, fname))
                f.func(fname)

print("\n\n")

print("--- contents of toc ---")
pprint(srp.toc.data)
