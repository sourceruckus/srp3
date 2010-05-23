"""
The main srp command line application
"""

from __future__ import with_statement

import os
import pwd
import shutil
import subprocess
import sys

import config
import package
import work
import utils


def cleanup():
    for x in config.RUCKUS_DIRS:
        x = os.path.join(config.RUCKUS, x)
        for y in os.listdir(x):
            y = os.path.join(x, y)
            utils.vprint("removing: %s" % y)
            try:
                os.remove(y)
            except:
                shutil.rmtree(y)
    unlock()


def lock():
    with open(config.LOCK, 'w') as f:
        pass


def unlock():
    if is_locked():
        os.remove(config.LOCK)


def is_locked():
    return os.access(config.LOCK, os.F_OK)


def create_ruckus_dirs():
    utils.vprint("create_ruckus_dirs")
    for x in config.RUCKUS_DIRS:
        try:
            os.makedirs("%s/%s" % (config.RUCKUS, x))
        except:
            pass





# For now, we're just going to automatically test things out...


# set up our fakeroot
uid = os.getuid()
homedir = pwd.getpwuid(uid).pw_dir
os.environ["SRP_ROOT_PREFIX"] = os.path.join(homedir, "fakeroot")
reload(config)
create_ruckus_dirs()
cleanup()


# figure out where our source tree is, so we can find all our package
# files
toplevel = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


# create v3 package from dir
p3 = package.source(dirname="%s/dev-3.0/v3/SRP_files" % toplevel)
p3.commit("%s/dev-3.0/v3" % toplevel)

# instantiate v3 package from previously created package
p3_fromfile = package.source("foo-1.0-1.srp")

# build binary package(s) from p
b = work.builder()
p3_built = b.build(p3)
