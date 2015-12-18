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

    sourcedir = work['dir'] + '/source'

    # setup source dir(s)
    #
    # NOTE: If src is a dir, we will set things up so that the build
    #       script can easily build out-of-tree using a seperate build
    #       dir.  If --copysrc was specified, we'll make a copy of src in
    #       the build dir.  If src is a source tarball, we'll extract it
    #       in dir.
    if os.path.isfile(n.header.src):
        print("extracting source tarball {}".format(n.header.src))
        with tarfile.open(n.header.src) as f:
            f.extractall(sourcedir)

        # put source dir in source, not souce/source-x.y.z/
        #
        # FIXME: This means if the source tarball is some odd tar that isn't
        #        all contained in a toplevel dir, we have problems...
        d = os.listdir(sourcedir)
        if len(d) == 1:
            d = d[0]
            for x in os.listdir(sourcedir + "/" + d):
                os.rename(sourcedir + "/" + d + "/" + x,
                          sourcedir + "/" + x)
            os.rmdir(sourcedir + "/" + d)

    else:
        # user provided external source tree

        # copy source tree if requested
        #
        # FIXME: setup_generic from the ruckus bootstrap scripts has
        #        special code for excluding .git and for fixing relative
        #        paths in .git when recursively copying a souce tree... do
        #        we need that here?
        #
        if n.header.copysrc:
            print("copying external sourcetree...")
            shutil.copytree(n.header.src, sourcedir)

        else:
            sourcedir = n.header.src

        # src is a source tree, do we need to bootstrap?
        #
        # NOTE: If this source tree doesn't use autotools, this block should
        #       just quietly boil down to a no-op.
        if not os.path.exists(sourcedir + '/configure'):
            # try to bootstrap source tree
            #
            # NOTE: Each of these subprocess calls uses sets NOCONFIGURE in
            #       the environment because it's fairly common for
            #       bootstrap/autogen scripts to invoke configure when
            #       they're finished and we don't want that.
            new_env = dict(os.environ)
            new_env['NOCONFIGURE'] = "1"
            if os.path.exists(sourcedir + '/bootstrap.sh'):
                subprocess.check_call(["./bootstrap.sh"],
                                      cwd=sourcedir, env=new_env)

            elif os.path.exists(sourcedir + '/bootstrap'):
                subprocess.check_call(["./bootstrap"],
                                      cwd=sourcedir, env=new_env)

            elif os.path.exists(sourcedir + '/autogen.sh'):
                subprocess.check_call(["./autogen.sh"],
                                      cwd=sourcedir, env=new_env)

            elif (os.path.exists(sourcedir + '/configure.in') or
                  os.path.exists(sourcedir + '/configure.ac')):
                subprocess.check_call(["autoreconf", "--force", "--install"],
                                      cwd=sourcedir, env=new_env)


    # create build script
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
    #        SOURCE_DIR: Toplevel dir of the source tree.
    #
    #        BUILD_DIR: Toplevel dir of build process (may or may not
    #            match SOURCE_DIR).
    #
    #        EXTRA_DIR: Directory where extra_content is located (e.g.,
    #            patches).
    #
    #        PAYLOAD_DIR: The payload dir (was called SRP_ROOT in v2).
    #            This is where files must get installed (e.g., w/
    #            DESTDIR=$PAYLOAD_DIR) in build scripts.  The SRP_ROOT
    #            variable has been removed in v3.
    #
    #        FUNCTIONS: Absolute path to our helpful functions file.
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
    #
    new_env = dict(os.environ)
    new_env['SOURCE_DIR'] = sourcedir
    new_env['BUILD_DIR'] = work['dir']+"/build"
    new_env['PAYLOAD_DIR'] = work['dir']+"/payload"
    new_env['EXTRA_DIR'] = work['dir']+"/extra_content"
    new_env['FUNCTIONS'] = srp.config.build_functions
    os.mkdir(work['dir'] + '/build')
    os.mkdir(work['dir'] + '/payload')
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
    #
    # FIXME: why is manifest_create inside blob.py?
    #
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
