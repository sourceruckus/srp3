"""Feature module for the core functionality of SRP.

This feature module implements the core functionality of the package manager
(i.e., creating, building, installing packages).
"""

import hashlib
import io
import os
import pickle
import pwd
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

    # create ruckus dir tree
    for x in ["package", "build", "tmp"]:
        os.makedirs(d + "/" + x)

    return d



# FIXME: migrate bits of this to build_func, then remove
def create_func(work):
    """create tar of NOTES, source, SHA"""

    n = work["notes"]

    # locate all needed files
    #
    # NOTE: We expect these to all be relative to the directory containing
    #       the notes file.
    flist = [n.header.source_filename]
    flist.extend(n.header.extra_content)

    # cleanup paths in notes_file
    #
    # NOTE: Files get added to the toplevel of the pkg, so we need to remove
    #       path info from associated entries in notes_file so we can find
    #       the files in the pkg later
    n.header.source_filename = os.path.basename(n.header.source_filename)
    for x in n.header.extra_content[:]:
        n.header.extra_content.remove(x)
        n.header.extra_content.append(os.path.basename(x))

    # create tarball
    #
    # NOTE: We add the pickled notes_file instance, the source tarball, any
    #       extra files specified in the NOTES file, and a SHA file
    #       containing a single checksum of the archive (all files
    #       concatenated together into a single stream).
    sha = hashlib.new("sha1")
    tar = tarfile.open(work["pname"], mode="w")

    # pickle our notes_file instance and add it to the pkg
    with tempfile.TemporaryFile() as f:
        pickle.dump(n, f)
        # rewind for tar.addfile
        f.seek(0)
        tar.addfile(tar.gettarinfo(arcname="NOTES", fileobj=f),
                    fileobj=f)
        # rewind and generate a SHA entry
        f.seek(0)
        sha.update(f.read())

    # add all the files in flist
    for fname in flist:
        # create an open file object
        with open(fname, mode='rb') as f:
            # we need to remove all leading path segments so that all
            # files end up at the toplevel of the pkg file
            arcname = os.path.basename(fname)
            #print("adding {} as {}".format(f.name, arcname))
            tar.addfile(tar.gettarinfo(arcname=arcname, fileobj=f),
                        fileobj=f)
            # rewind and generate a SHA entry
            f.seek(0)
            sha.update(f.read())

    # create the SHA file and add it to the pkg
    with tempfile.TemporaryFile() as f:
        f.write(sha.hexdigest().encode())
        f.seek(0)
        tar.addfile(tar.gettarinfo(arcname="SHA", fileobj=f),
                    fileobj=f)

    tar.close()


def build_func(work):
    """run build script to populate payload dir, then create TarInfo objects for
    all files"""
    # create ruckus dir in tmp
    work['dir'] = create_tmp_ruckus()

    n = work["notes"]

    # locate all needed files
    #
    # NOTE: We expect these to all be relative to the directory containing
    #       the notes file.
    flist = []
    if n.header.source_dir:
        flist.append(n.header.source_dir)
    else:
        flist.append(n.header.source_filename)
    flist.extend(n.header.extra_content)

    for fname in flist:
        # fname may be a file or a dir, so we just check for existence
        if not os.path.exists(fname):
            raise Exception("Missing required file/dir: " + fname)

    # FIXME: should i make a symlink forest in dir/package so that build
    #        scripts can assume all their files are relative to there?
    #        would be easy enough, and would add a bit of backwards
    #        compatibility in old build scripts.


    # FIXME: make sure system default features are enabled.  defaults were
    #        populated when the notes_file was instantiated during creation,
    #        but we may now be on a different host with different defaults.

    # extract package contents
    #
    # NOTE: This is needed so that build scripts can access other misc files
    #       they've included in the srp (e.g., apply a patch, install an
    #       externally maintained init script)
    with tarfile.open(work["fname"]) as f:
        f.extractall(work['dir'] + "/package")

    # extract source tarball
    with tarfile.open(work['dir'] + "/package/" + work['notes'].header.source_filename) as f:
        sourcedir=f.firstmember.name
        f.extractall(work['dir'] + "/build")

    # create build script
    #
    # FIXME: do i really need to create an executable script file?  or can i
    #        just somehow spawn a subprocess using the contents of the buf?
    with open(work['dir'] + "/build/srp_go", 'w') as f:
        f.write(work['notes'].script.buffer)
        os.chmod(f.name, stat.S_IMODE(os.stat(f.name).st_mode) | stat.S_IXUSR)

    # run build script
    #
    # FIXME: we need to standardize and document what variables are exposed
    #        to build scripts.  v2 just added RUCKUS_DIR.  i think we should
    #        add the following:
    #
    #        SRP_ROOT: The tmp payload dir (just like in v2). This is
    #            DEPRECATED (to go away in 3.1?) and is just here for
    #            backwards compatibility with v2 build scripts (it's used to
    #            get at misc package files SRP_ROOT/../package)
    #
    #        PACKAGE_DIR: The package dir (where the srp got extracted).
    #
    #        BUILD_DIR: Parent dir of the extracted source tarball.
    #
    #        PAYLOAD_DIR: The tmp payload dir (was called SRP_ROOT in v2).
    #            This is the preferred way to refer to the payload dir.
    #            SRP_ROOT is deprecated.
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
    new_env = dict(os.environ)
    new_env['SRP_ROOT'] = work['dir']+"/tmp"
    new_env['PACKAGE_DIR'] = work['dir']+"/package"
    new_env['BUILD_DIR'] = work['dir']+"/build"
    new_env['PAYLOAD_DIR'] = work['dir']+"/tmp"
    subprocess.check_call(["../srp_go"], cwd=work['dir']+'/build/'+sourcedir, env=new_env)

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


# FIXME: dead code.  db init is done in db module now and we've unregistered
#        this func in the feature_struct
def install_func(work):
    """prep db stuff"""
    # NOTE: In order to test this (and later on, to test new packages) as an
    #       unprivileged, we need to have to have some sort of fake root
    #       option (e.g., the old SRP_ROOT_PREFIX trick).
    #
    #       I'm waffling between using a DESTDIR environment variable
    #       (because that's what autotools and tons of other Makefiles use)
    #       and adding a --root command line arg (because that's what RPM
    #       does and it's easier to document)
    #
    # FIXME: For now, it's DESTDIR.  Perhaps revisit this later...
    try:
        work["DESTDIR"] = os.environ["DESTDIR"]
    except:
        work["DESTDIR"] = "/"

    m = work['manifest']

    n = work["notes"]

    # setup the db dir for later
    #
    # FIXME: /var/lib/srp should probably be configurable...
    #
    # FIXME: is this really where we should be doing this?  shouldn't some
    #        method in the db module take care of it?
    #
    # FIXME: and that's the wrong sha... that's the sha of the brp we're
    #        installing from... don't we want to calc a final sha?
    path = "/var/lib/srp/"+n.header.name+"/"+n.installed.installed_from_sha
    # FIXME: DESTDIR or --root.  see FIXME in core.install_func...
    work["db"] = work["DESTDIR"] + path

    # FIXME: if sha already installed, this will throw OSError
    os.makedirs(work["db"])


def install_iter(work, fname):
    """install a file"""
    # FIXME: can we make blob() take a previously read manifest to speed
    #        up instantiation?
    blob = srp.blob.blob(work["dir"]+"/package/BLOB")
    blob.extract(fname, work["DESTDIR"])


def uninstall_func():
    """remove files listed in pkg manifest"""
    # FIXME: MULTI: why not?  i guess directory removal might git odd, but
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
