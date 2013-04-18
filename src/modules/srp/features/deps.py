"""Feature module for tracking library dependencies.

This feature compiles a list of required libraries (i.e., system libs that
files in the payload are linked against) to add to the brp.  It also
registers an install function to ensure that the requirements are met prior
to installing.

NOTE: This is probably not as portable as it could/should be...
"""

from srp.features import *

import ctypes
import os
import subprocess


def build_func(work):
    """add library deps to the brp"""
    deps = []
    for root, dirs, files in os.walk(work['dir']+"/tmp"):
        tmp = dirs[:]
        tmp.extend(files)
        for x in tmp:
            realname = os.path.join(root, x)
            if os.path.islink(realname) or os.path.isdir(realname):
                continue

            #print("calculating deps for: ", realname)

            # NOTE: We're using objdump here instead of ldd.  The difference
            #       is that objdump will only tell us what libraries this
            #       executable EXPLICITLY requires, whereas ldd will
            #       recursively gather all libraries needed by this
            #       executable and all its libs and all its libs' libs, etc,
            #       etc.  From a package manager's standpoint, I don't think
            #       we really care what other libs a library we need
            #       needs... if the system has it, we'll assume that the
            #       system has it AND ALL ITS DEPS already.
            p = subprocess.Popen(["objdump", "-p", realname],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            buf = p.communicate()[0]
            if p.returncode != 0:
                continue

            for line in buf.decode().split('\n'):
                line = line.strip().split()
                if not line:
                    continue
                if line[0] == "NEEDED":
                    deps.append(line[1])

    # FIXME: should we sort this list?  i'm tempted, but it might also be
    #        nice to preserve the order that the libs are listed in the ELF
    #        headers...
    #deps.sort()
    work['notes'].additions['brp']['deps'] = " ".join(deps)


def install_func(work):
    """check system for required libs"""
    # FIXME: libreadline stupidly has unresolved symbols unless you link it
    #        with libncurses (or libtermcap, if memory serves).  so,
    #        ctypes.cdll.LoadLibrary("libreadline.so.6") will fail, even
    #        though we DO have the library.
    #
    # FIXME: sooo, i think this should be fixed by the distro when
    #        installing readline (e.g., LFS does a 'make
    #        SHLIB_LIBS=-lncurses')... but should i print a warning about
    #        this particular lib if we encounter one w/ unresolved refs?  we
    #        should be able to pick this out by looking at the error msg.
    #        for undefined refs we get:
    #
    #        OSError: /home/mike/staging/lib/libreadline.so.6: undefined
    #        symbol: PC
    #
    #        but for a completely missing lib, we got:
    #
    #        OSError: libasdf.so.5: cannot open shared object file: No such
    #        file or directory
    n = work['notes']
    deps = n.brp.deps.split()
    # NOTE: We iterate all the way through so that the user can see ALL the
    #       missing libs as apposed to just the first one
    missing = []
    for d in deps:
        try:
            ctypes.cdll.LoadLibrary(d)
        except:
            missing.append(d)
    
    if missing:
        raise Exception("missing required libraries:\n  --> " + "\n  --> ".join(missing))



register_feature(feature_struct("deps",
                                __doc__,
                                True,
                                build = stage_struct("deps", build_func, ["core"], []),
                                install = stage_struct("deps", install_func, [], ["core"])))