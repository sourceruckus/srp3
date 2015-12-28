"""Feature module for tracking library dependencies.

This feature compiles a list of required libraries (i.e., system libs that
files in the payload are linked against) to add to the brp.  It also
registers an install function to ensure that the requirements are met prior
to installing.

NOTE: This is probably not as portable as it could/should be...
"""

import srp
from srp.features import *

import ctypes
import glob
import os
import subprocess


class NotesDeps(srp.SrpObject):
    def __init__(self):
        self.libs_needed = []
        self.libs_provided = []


# FIXME: MULTI: why don't i iterate over the list of TarInfo objects
#        instead of re-walking the filesystem.  not only will that be
#        faster, i could split the TarInfo list into chunks and use
#        multiprocessing to take advantage of multiple CPUs.  we would
#        need a Manager for the deps list, but probably not anything
#        else.
def build_func(fname):
    """add library deps to the brp"""
    x = srp.work.build.manifest[fname]["tinfo"]

    # we only care about regular files
    if not x.isreg():
        return

    n = srp.work.build.notes
    deps = []

    realname = srp.work.topdir+"/payload"+fname
    print("calculating deps for: ", realname)

    # NOTE: We're using objdump here instead of ldd.  The difference is that
    #       objdump will only tell us what libraries this executable EXPLICITLY
    #       requires, whereas ldd will recursively gather all libraries needed
    #       by this executable and all its libs and all its libs' libs, etc,
    #       etc.  From a package manager's standpoint, I don't think we really
    #       care what other libs a library we need needs... if the system has
    #       it, we'll assume that the system has it AND ALL ITS DEPS already.
    p = subprocess.Popen(["objdump", "-p", realname],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    buf = p.communicate()[0]
    if p.returncode != 0:
        # objdump failed, must not be an elf binary
        return

    # We do a whole bunch with this output.
    #
    #  1. file_format - This is the elf file_format of fname (and it's
    #     required libs).
    #
    #  2. soname - If this is set, fname is a library.
    #
    #  3. deps - This list gets populated with (file_format, soname)
    #     tuples of any libraries needed by this file.
    #
    file_format = None
    soname = None
    for line in buf.decode().split('\n'):
        line = line.strip().split()
        if not line:
            continue
        if line[-3:-1] == ['file', 'format']:
            file_format = line[-1]
        if line[0] == "NEEDED":
            deps.append((file_format, line[1]))
        if line[0] == "SONAME":
            soname = line[1]
    
    print("needed:", deps)

    # stash our libinfo tuple into this file's section of the manifest
    if file_format and soname:
        libinfo = (file_format, soname)
        srp.work.build.manifest[fname]["libinfo"] = libinfo
        print("provides:", libinfo)
        
        # also stash this info in the deps section of the notes file for
        # easy weeding out
        #
        # FIXME: as with deps.libs_needed, this will need some type of
        #        locking if we do multiproc stuff...
        #
        n.deps.libs_provided.append(libinfo)

    # NOTE: At this point, deps contains a sorted list of deps for THIS FILE.
    #       We still need to update our global list of deps for this package.
    #
    # FIXME: if we use multiproc iter stage, we need to use some sort of
    #        locking here so that we can modify the notes file from within each
    #        subproc
    #
    # FIXME: is n a ref to the entry in srp.work? or a copy?
    #
    big_deps = n.deps.libs_needed[:]
    for d in deps:
        if d not in big_deps:
            big_deps.append(d)
    big_deps.sort()
    n.deps.libs_needed = big_deps


def install_func():
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
    #
    # FIXME: for now, when tesing on systems with broken libreadline, you
    #        can get the deps check to pass by setting
    #        LD_PRELOAD=libncurses.so.5 on the command line.
    n = srp.work.install.notes
    deps = n.deps.libs_needed[:]
    print(deps)
    for x in n.deps.libs_provided:
        print(x)
        try:
            deps.remove(x)
        except:
            pass

    # NOTE: We iterate all the way through so that the user can see ALL the
    #       missing libs as apposed to just the first one
    #
    # FIXME: MULTI: this could also be split into chunks and passed to
    #        worker processes to take advantage of multiple CPUs.
    #
    # FIXME: MULTI: this one might be kinda silly, though... given that most
    #        packages aren't gonna have many deps, the speedup may not
    #        outway the overhead induced... we'll have to benchmark it and
    #        see.
    missing = []
    for d in deps:
        if not lookup_lib(*d):
            missing.append(d)
    
    if missing:
        raise Exception("missing required libraries:\n  --> " + "\n  --> ".join(missing))



# takes an InstalledPackage
def info_func(p):
    lines = ["Required Libraries:"]
    for l in p.notes.deps.libs_needed:
        lines.append("  {}".format(l))
    lines.append("Provided Libraries:")
    for l in p.notes.deps.libs_provided:
        lines.append("  {}".format(l))
    return "\n".join(lines)


# objdump -p fname | grep "file format"
def lookup_file_format(fname):
    p = subprocess.Popen(["objdump", "-p", fname],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    buf = p.communicate()[0]
    if p.returncode != 0:
        # objdump failed, must not be an elf binary
        return

    file_format = None
    for line in buf.decode().split('\n'):
        line = line.strip().split()
        if not line:
            continue
        if line[-3:-1] == ['file', 'format']:
            file_format = line[-1]
            break

    return file_format


# grep ld-linux $(which ldd)
def lookup_elf_interpreters():
    p = subprocess.Popen(["which", "ldd"],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buf = p.communicate()[0]
    if p.returncode != 0:
        raise Exception("Failed to locate ldd")
    
    ldd = buf.decode().split('\n')[0]
    with open(ldd) as f:
        retval = {}
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("RTLDLIST="):
                line = line[9:].strip('"').split()
                for x in line:
                    if os.path.exists(x):
                        retval[lookup_file_format(x)] = x
    
    if not retval:
        raise Exception("Failed to detect any valid elf interpreters")
    
    return retval


# FIXME: this could look in tons of other dirs... but really, what's the
#        chance that there are no libraries in the directory alongside
#        ld-linux.so?
#
def lookup_matching_lib(elf, file_format):
    # start in dirname(elf)
    for x in glob.glob("{}/lib*.so*".format(os.path.dirname(elf))):
        print("checking for {}: {}".format(file_format, x))
        fmt = lookup_file_format(x)
        print("file_format:", fmt)
        if file_format == fmt:
            return x
    
    raise Exception("Failed to find any libs of format {}".format(file_format))


# LD_PRELOAD=libfoo.so /lib64/ld-linux-x86-64.so.2 \
#    --list /lib64/libdl.so
def lookup_lib(file_format, libname):
    # get list of available elf interpreters
    elf = lookup_elf_interpreters()[file_format]
    
    # find an appropriate lib to interrogate
    piggy = lookup_matching_lib(elf, file_format)
    
    # add the lib we're checking for via LD_PRELOAD (basically pretend
    # that whatever library we're using as our guinea pig was linked
    # against it) and have the interpreter go find all the libraries on
    # the system.
    #
    # "LD_PRELOAD={} {} --list {}".format(libname, elf, piggy))
    #
    p = subprocess.Popen([elf, "--list", piggy],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env = {"LD_PRELOAD": libname})
    out,err = p.communicate()
    print(err)
    print(out)
    
    for line in out.decode().split('\n'):
        line = line.strip().split()
        print(line)
        if not line:
            continue
        if line[0] == libname:
            return line[2]




register_feature(
    feature_struct("deps",
                   __doc__,
                   True,
                   build_iter = stage_struct("deps", build_func, [], []),
                   install = stage_struct("deps", install_func, [], ["core"]),
                   info = info_func))
