import os, os.path, sys, string
import sr, sr_package2, utils

def preinstall(p):
    utils.vprint("--preinstall--")
    try:
        #os.chdir("asdf")
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)

def postinstall(p):
    utils.vprint("--postinstall--")
    try:
        #os.chdir("asdf")
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)

def preuninstall(p):
    utils.vprint("--preuninstall--")
    try:
        #os.chdir("asdf")
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)

def postuninstall(p):
    utils.vprint("--postuninstall--")
    try:
        #os.chdir("asdf")
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)
