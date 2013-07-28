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



def create_func(work):
    """create tar of NOTES, source, SHA"""

    n = work["notes"]

    # locate all needed files
    #
    # NOTE: We expect these to all be relative to the directory containing
    #       the notes file.
    flist = [os.path.basename(n.filename), n.info.sourcefilename]
    try:
        flist.extend(n.info.extra.split())
    except:
        pass

    # create tarball
    #
    # NOTE: We add the source file and any extra files specified in the
    #       NOTES file, the NOTES file itself, and a SHA file containing a
    #       single checksum of the archive (all files concatenated together
    #       into a single stream).
    sha = hashlib.new("sha1")
    tar = tarfile.open(work["pname"], mode="w")
    for fname in flist:
        # create an open file object
        with open(os.path.join(os.path.dirname(n.filename), fname),
                  mode='rb') as f:
            # we need to remove all leading path segments so that all
            # files end up at the toplevel of the pkg file
            arcname = os.path.basename(fname)
            if arcname == os.path.basename(n.filename):
                # we also need to rename the notes file inside the
                # pkg
                arcname = "NOTES"
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

    # extract package contents
    #
    # NOTE: This is needed so that build scripts can access other misc files
    #       they've included in the srp (e.g., apply a patch, install an
    #       externally maintained init script)
    with tarfile.open(work["fname"]) as f:
        f.extractall(work['dir'] + "/package")

    # extract source tarball
    with tarfile.open(work['dir'] + "/package/" + work['notes'].info.sourcefilename) as f:
        sourcedir=f.firstmember.name
        f.extractall(work['dir'] + "/build")

    # create build script
    #
    # FIXME: do i really need to create an executable script file?  or can i
    #        just somehow spawn a subprocess using the contents of the buf?
    with open(work['dir'] + "/build/srp_go", 'w') as f:
        f.write(work['notes'].script.buf)
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

    # append to brp section of NOTES file
    #
    # FIXME: hmmm... i might have to rethink using namedtuples for NOTES'
    #        data... if i need to append to it here (and i do), and then
    #        write it back out (which i do), i probably want to keep the
    #        parser around.  and if i'm going to keep the parser around
    #        anyway, why not just use it for all the data all the time?
    #
    #        well, i could update the parser as i go along (inside the notes
    #        constructor, default expansions, etc), but still access the
    #        data via the exposed struct (which should be much
    #        faster)... the question really is, is it a big enough speed
    #        improvement to justify the extra complexity.  it's not going to
    #        be a mem improvement, unless i ditch the parser after
    #        construction...
    #
    #        it might not actually be that hard to iterate through our named
    #        tuples and spit the data back into a new ConfigParser instance
    #        when we want to write back to file... but we will have to
    #        decide how we want to go about appending to the data while
    #        we're working here... keeping the parser around just for that
    #        seems silly.  maybe we just add a appendage dict for new data
    #        and serialize it all into a new ConfigParser when we're done.
    n = work['notes']

    # FIXME: should have a .srprc file to specify a full name (e.g., 'Joe
    #        Bloe <bloe@mail.com>'), and fallback to user id if it's not set
    n.additions['brp']['builder'] = pwd.getpwuid(os.getuid()).pw_gecos

    # FIXME: this should probably be a bit more complicated...
    n.additions['brp']['build_host'] = socket.gethostname()

    # FIXME: should i store seconds since epoch, struct_time, or a human
    #        readable string here...?
    n.additions['brp']['build_date'] = time.asctime()


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

    # setup the db dir for later
    #
    # FIXME: /var/lib/srp should probably be configurable...
    path = "/var/lib/srp/"+work["notes"].info.name+"/"+work["sha"]
    # FIXME: DESTDIR or --root.  see FIXME in core.install_func...
    work["db"] = work["DESTDIR"] + path

    # FIXME: if sha already installed, this will throw OSError
    os.makedirs(work["db"])

    # add fields to NOTES
    n = work['notes']

    # FIXME: should i store seconds since epoch, struct_time, or a human
    #        readable string here...?
    n.additions['installed']['date'] = time.asctime()


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
                   create = stage_struct("core", create_func, [], []),
                   build = stage_struct("core", build_func, [], []),
                   install = stage_struct("core", install_func, [], []),
                   install_iter = stage_struct("core", install_iter, [], []),
                   uninstall = stage_struct("core", uninstall_func, [], []),
                   uninstall_iter = stage_struct("core", uninstall_iter,
                                                 [], []),
                   action = [("commit",
                              stage_struct("core", commit_func, [], []))]))
