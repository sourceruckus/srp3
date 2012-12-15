#!/usr/bin/env python3

import os
import sys
from pprint import pprint

import srp
import srp.features.trackfiles

pprint(srp.registered_features)
print("\n\n")

# generate list of funcs for install
#install_funcs = srp.get_function_list("inst", ["trackfiles"])
install_funcs = srp.get_function_list("inst")
print(install_funcs)
print("\n\n")

# walk fs node calling funcs
for path, dirs, files in os.walk("FOO"):
    if files:
        for f in files:
            fname = os.path.join(path, f)
            print(fname)
            for func in install_funcs:
                print("%s(%s)" % (func, fname))
                func(fname)

print("\n\n")

print("--- contents of toc ---")
pprint(srp.toc.data)
