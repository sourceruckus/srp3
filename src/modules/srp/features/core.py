"""Feature module for the core functionality of SRP.

This feature module implements the core functionality of the package manager
(i.e., creating, building, installing packages).
"""

import hashlib
import io
import os
import pickle
import pwd
import shutil
import socket
import stat
import subprocess
import tarfile
import tempfile
import time

import srp
from srp.features import *

# FIXME: put this as a function somewhere useful... we'll be doing it in
#        other places
def partition_list(full_list, n):
    """return a tuple containing n equal-ish length sublists of full_list

    For this, equal-ish means that at least N-1 of the returned sublists
    will be the same length, with the last sublist possibly being smaller if
    length of full_list wasn't an even multiple of N
    """
    per_sub = int(len(full_list)/n)
    # if it's not an even multiple, use a larger value for per_sub such that
    # we at least have N-1 workers with an even load (i.e., worker-N will
    # have a shorter list and finish first)
    if per_sub*n != len(full_list):
        per_sub+=1
    # slice it up
    sub_lists = []
    for x in range(n):
        sub_lists.append(full_list[x*per_sub:(x+1)*per_sub])
    
    return sub_lists



def create_tmp_ruckus():
    d = tempfile.mkdtemp(prefix="srp-")
    return d



def build_func(work):
    """run build script to populate payload dir, then create TarInfo objects for
    all files"""
    # create ruckus dir in tmp
    work['dir'] = create_tmp_ruckus()

    n = work["notes"]

    # setup build dir(s)
    #
    # NOTE: If src is a dir, we will attempt to build out-of-tree using a
    #       seperate build dir.  If --intree was specified, we'll make a
    #       copy of src in the build dir.  If src is a source tarball, we'll
    #       extract it in dir.
    if os.path.isfile(n.header.src):
        print("extracting source tarball {}".format(n.header.src))
        with tarfile.open(n.header.src) as f:
            f.extractall(work['dir'] + '/build')

        # put source dir in build, not build/source-x.y.z/
        #
        # FIXME: This means if the source tarball is some odd tar that isn't
        #        all contained in a toplevel dir, we have problems...
        d = os.listdir(work["dir"] + "/build")
        if len(d) == 1:
            d = d[0]
            for x in os.listdir(work["dir"] + "/build/" + d):
                os.rename(work["dir"] + "/build/" + d + "/" + x,
                          work["dir"] + "/build/" + x)
            os.rmdir(work["dir"] + "/build/" + d)

    else:
        # src is a source tree, do we need to bootstrap?
        #
        # NOTE: If this source tree doesn't use autotools, this block should
        #       just quietly boil down to a no-op.
        if not os.path.exists(n.header.src + "/configure"):
            # try to bootstrap source tree
            #
            # NOTE: Each of these subprocess calls uses sets NOCONFIGURE in
            #       the environment because it's fairly common for
            #       bootstrap/autogen scripts to invoke configure when
            #       they're finished and we don't want that.
            new_env = dict(os.environ)
            new_env['NOCONFIGURE'] = "1"
            if os.path.exists(n.header.src + "/bootstrap.sh"):
                subprocess.check_call(["./bootstrap.sh"],
                                      cwd=n.header.src, env=new_env)

            elif os.path.exists(n.header.src + "/bootstrap"):
                subprocess.check_call(["./bootstrap"],
                                      cwd=n.header.src, env=new_env)

            elif os.path.exists(n.header.src + "/autogen.sh"):
                subprocess.check_call(["./autogen.sh"],
                                      cwd=n.header.src, env=new_env)

            elif (os.path.exists(n.header.src + "/configure.in") or
                  os.path.exists(n.header.src + "/configure.ac")):
                subprocess.check_call(["autoreconf", "--force", "--install"],
                                      cwd=n.header.src, env=new_env)

        # attempt to make sure srcdir is clean before we start
        #
        # NOTE: Specifically, building out-of-tree requires that the source
        #       tree be bootstrapped but NOT configured.
        #
        # FIXME: This could use subprocess.DEVNULL to hide output, but that
        #        would requier Python >= 3.3
        #
        # FIXME: Should we really be doing this here?  What if not using
        #        autotools?  This is really the responsibility of the
        #        user, not us, I think...
        #
        #subprocess.call(["make", "distclean"], cwd=n.header.src)

        # copy source tree if not building out-of-tree
        if n.header.build_intree:
            print("copying sourcetree for in-tree building...")
            shutil.copytree(n.header.src, work['dir'] + '/build')

        else:
            # build out-of-tree in build dir.  we do this by creating a
            # wrapper script build/configure which simply executes the
            # srcdir/configure script via absolute path with the specified
            # args
            os.mkdir(work['dir'] + '/build')
            with open(work['dir'] + '/build/configure', 'w') as f:
                f.write("#!/bin/sh\n")
                f.write("{}/configure $* || exit 1\n".format(n.header.src))
                os.chmod(f.name,
                         stat.S_IMODE(os.stat(f.name).st_mode) | stat.S_IXUSR)

    # create build script
    #
    # FIXME: do i really need to create an executable script file?  or can i
    #        just somehow spawn a subprocess using the contents of the buf?
    with open(work['dir'] + "/srp_go", 'w') as f:
        f.write(work['notes'].script.buffer)
        os.chmod(f.name, stat.S_IMODE(os.stat(f.name).st_mode) | stat.S_IXUSR)

    # create extra_content dir
    #
    # NOTE: The extra_content files are not symlinks, so that bogus build
    #       scripts can't mangle system files
    os.mkdir(work['dir'] + "/extra_content")
    for x in n.header.extra_content:
        shutil.copy(x, work['dir'] + "/extra_content")

    # run build script
    #
    # FIXME: we need to standardize and document what variables are exposed
    #        to build scripts.  v2 just added RUCKUS_DIR.  i think we should
    #        add the following:
    #
    #        BUILD_DIR: Toplevel dir of the source tree.
    #
    #        EXTRA_DIR: Directory where extra_content is located (e.g.,
    #            patches).
    #
    #        PAYLOAD_DIR: The tmp payload dir (was called SRP_ROOT in v2).
    #            This is where files must get installed (e.g., w/
    #            DESTDIR=$PAYLOAD_DIR) in build scripts.  The SRP_ROOT
    #            variable has been removed in v3.
    #
    # FIXME: the v2 code is really bad at keeping output synchronized when
    #        redirecting stdout to a logfile (i.e., output coming directly
    #        from srp and output coming from subprocesses do not apear in
    #        the same order in the logfile that they would have w/out
    #        redirection...).  This has always driven me nuts, but i don't
    #        know how to fix it.  perhaps we should play with different
    #        invocations here.  I'm pretty sure that the problem could be
    #        avoided by returning the output from the subprocess to the
    #        parent process and then printing it... but that will lead to no
    #        output from the build until it's all finished, then spamming it
    #        all to the screen...
    #
    #        in C i'd say to use popen and read chunks of stdout from the
    #        resulting pipe... can we do that easily using subprocess
    #        module?
    new_env = dict(os.environ)
    new_env['BUILD_DIR'] = work['dir']+"/build"
    new_env['PAYLOAD_DIR'] = work['dir']+"/tmp"
    new_env['EXTRA_DIR'] = work['dir']+"/extra_content"
    os.mkdir(work['dir'] + '/tmp')
    subprocess.check_call(["../srp_go"], cwd=work['dir']+'/build/', env=new_env)

    # create manifest
    #
    # NOTE: This is a map of all the files and associated meta-data that
    #       will be included in the package upon completion.  The core of
    #       each file's data is a TarInfo object.  This makes tons of sense
    #       because we're using tarfile already and TarInfo tracks all the
    #       core meta-data we need.  Other features can add other items
    #       (e.b., checksum) to each file's entry as needed.
    #
    # NOTE: Keep in mind, the TarInfo objects are created now, but nothing
    #       is added to an archive yet.  This is to allow other features a
    #       chance to tweak things (e.g., permissions, ownership).  At the
    #       very end (i.e., when all other feature functions have been
    #       executed), all the TarInfo objects (and their associated file
    #       objects) will be added to the archive.
    #
    # FIXME: straighten out these comments
    work['manifest'] = srp.blob.manifest_create(new_env['PAYLOAD_DIR'])


def install_iter(work, fname):
    """install a file"""
    # FIXME: can we make blob() take a previously read manifest to speed
    #        up instantiation?
    blob = srp.blob.blob(work["dir"]+"/package/BLOB")
    blob.extract(fname, work["DESTDIR"])


def uninstall_func():
    """remove files listed in pkg manifest"""
    # FIXME: MULTI: why not?  i guess directory removal might get odd, but
    #        that's already a hard question... where does the removal of
    #        /usr/local/share/foo happen?  when i remove the last file in
    #        foo?  what keeps us from accidentally removing share when i
    #        remove foo if there are no other files in share?
    pass


def uninstall_iter(work, fname):
    """remove a file"""
    pass


def commit_func():
    """update pkg manifest"""
    # FIXME: MULTI:
    pass

register_feature(
    feature_struct("core",
                   __doc__,
                   True,
                   build = stage_struct("core", build_func, [], []),
                   install_iter = stage_struct("core", install_iter, [], []),
                   uninstall = stage_struct("core", uninstall_func, [], []),
                   uninstall_iter = stage_struct("core", uninstall_iter,
                                                 [], []),
                   action = [("commit",
                              stage_struct("core", commit_func, [], []))]))
