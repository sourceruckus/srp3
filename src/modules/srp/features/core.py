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




def build_func():
    """run build script to populate payload dir, then create TarInfo objects for
    all files"""

    # get some local refs with shorter names
    n = srp.work.build.notes

    # define paths once
    sourcedir = srp.work.topdir + '/source'
    extradir = srp.work.topdir + '/extra_content'
    buildscript = srp.work.topdir + '/srp_go'
    builddir = srp.work.topdir + '/build'
    payloaddir = srp.work.topdir + '/payload'

    # setup source dir(s)
    #
    # NOTE: If src is a dir, we will set things up so that the build
    #       script can easily build out-of-tree using a seperate build
    #       dir.  If --copysrc was specified, we'll make a copy of src in
    #       the build dir.  If src is a source tarball, we'll extract it
    #       in dir.
    if os.path.isfile(srp.params.build.src):
        print("extracting source tarball {}".format(srp.params.build.src))
        with tarfile.open(srp.params.build.src) as f:
            f.extractall(sourcedir)

        # put source dir in source, not souce/source-x.y.z/
        #
        # FIXME: This means if the source tarball is some odd tar that isn't
        #        all contained in a toplevel dir, we have problems...
        #
        #        maybe use TarFile object to check for messy source
        #        tarball and skip this code if detected?
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
        if srp.params.build.copysrc:
            print("copying external sourcetree...")
            shutil.copytree(srp.params.build.src, sourcedir)

        elif srp.params.build.gitsrc:
            print("cloning external sourcetree...")
            go = ["git", "clone", "--shared"]
            if srp.params.build.gitsrc != "HEAD":
                go += ["--branch", srp.params.build.gitsrc]
            go += [srp.params.build.src, sourcedir]
            if not srp.params.verbosity:
                # be silent
                subprocess.check_call(go, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
            else:
                subprocess.check_call(go)

        else:
            sourcedir = srp.params.build.src

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
    with open(buildscript, 'w') as f:
        f.write(n.script.buffer)
        os.chmod(f.name, stat.S_IMODE(os.stat(f.name).st_mode) | stat.S_IXUSR)

    # create extra_content dir
    #
    # NOTE: The extra_content files are not symlinks, so that bogus build
    #       scripts can't mangle system files
    #
    os.mkdir(extradir)
    for x in n.header.extra_content:
        shutil.copy(x, extradir)

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
    new_env['BUILD_DIR'] = builddir
    new_env['PAYLOAD_DIR'] = payloaddir
    new_env['EXTRA_DIR'] = extradir
    new_env['FUNCTIONS'] = srp.config.build_functions
    os.mkdir(builddir)
    os.mkdir(payloaddir)
    n.brp.time_build_script = time.time()
    subprocess.check_call([buildscript], cwd=builddir, env=new_env)

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
    n.brp.time_build_script = time.time() - n.brp.time_build_script
    n.brp.time_manifest_creation = time.time()
    srp.work.build.manifest = srp.blob.Manifest.fromdir(payloaddir)
    n.brp.time_manifest_creation = time.time() - n.brp.time_manifest_creation


def build_final():
    """package finalization"""
    # create the toplevel brp archive
    #
    # FIXME: we should remove this file if we fail...
    mach = platform.machine()
    if not mach:
        mach = "unknown"
    pname = "{}.{}.brp".format(n.header.fullname, mach)
    n.brp.pname = pname
    print("finalizing", pname)

    if srp.params.dry_run:
        # nothing more to do, since we didn't actually build anything to
        # finalize into a brp...
        return

    # FIXME: compression should be configurable globally and also via
    #        the command line when building.
    #
    if srp.config.default_compressor == "lzma":
        import lzma
        __brp = lzma.LZMAFile(pname, mode="w",
                              preset=srp.config.compressors["lzma"])
    elif srp.config.default_compressor == "bzip2":
        import bz2
        __brp = bz2.BZ2File(pname, mode="w",
                            compresslevel=srp.config.compressors["bz2"])
    elif srp.config.default_compressor == "gzip":
        import gzip
        __brp = gzip.GzipFile(pname, mode="w",
                              compresslevel=srp.config.compressors["gzip"])
    else:
        # shouldn't really ever happen
        raise Exception("invalid default compressor: {}".format(
            srp.config.default_compressor))

    brp = tarfile.open(fileobj=__brp, mode="w|")
    sha = hashlib.new("sha1")

    # populate the BLOB archive
    #
    # NOTE: This is where we actually add TarInfo objs and their associated
    #       fobjs to the BLOB, then add the BLOB to the brp archive.
    #
    # NOTE: This is implemented using a temporary file as the fileobj for a
    #       tarfile.  When the fobj is closed it's contents are lost, but
    #       that's fine because we will have already added it to the toplevel
    #       brp archive.
    n.brp.time_blob_creation = time.time()
    blob = srp.blob.BlobFile()
    blob.manifest = srp.work.build.manifest
    blob.fobj = tempfile.TemporaryFile()
    blob.tofile()
    n.brp.time_blob_creation = time.time() - n.brp.time_blob_creation
    # add BLOB file to toplevel pkg archive
    blob.fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="BLOB", fileobj=blob.fobj),
                fileobj=blob.fobj)
    # rewind and generate a SHA entry
    blob.fobj.seek(0)
    sha.update(blob.fobj.read())
    blob.fobj.close()

    # add NOTES (pickled instance) to toplevel pkg archive (the brp)
    n_fobj = tempfile.TemporaryFile()
    # last chance toupdate time_total
    n.brp.time_total = time.time() - n.brp.time_total
    pickle.dump(n, n_fobj)
    n_fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="NOTES", fileobj=n_fobj),
                fileobj=n_fobj)
    # rewind and generate a SHA entry
    n_fobj.seek(0)
    sha.update(n_fobj.read())
    n_fobj.close()

    # create the SHA file and add it to the pkg
    with tempfile.TemporaryFile() as f:
        f.write(sha.hexdigest().encode())
        f.seek(0)
        brp.addfile(brp.gettarinfo(arcname="SHA", fileobj=f),
                    fileobj=f)

    # close the toplevel brp archive
    brp.close()
    __brp.close()

    # clean out topdir
    for g in glob.glob("{}/*".format(srp.work.topdir)):
        if os.path.isdir(g):
            shutil.rmtree(g)
        else:
            os.remove(g)

    # FIXME: should i clear srp.work.build at this point?  it shouldn't
    #        really hurt anything if i leave it... and maybe it will be
    #        helpful during a --build-and-install?


def install_iter(fname):
    """install a file"""
    srp.work.install.blob.extract(fname, srp.params.root)


def install_final():
    """db registration and cleanup"""
    # commit NOTES to disk in srp db
    #
    # NOTE: We need to refresh our copy of n because feature funcs may have
    #       modified the copy in work[].
    #
    n = srp.work.install.notes

    # commit MANIFEST to disk in srp db
    #
    # NOTE: We need to refresh our copy because feature funcs may have
    #       modified it
    #
    m = srp.work.install.manifest

    # register w/ srp db
    inst = srp.db.InstalledPackage(n, m)
    srp.db.register(inst)

    # commit db to disk
    #
    # FIXME: is there a better place for this?
    if not srp.params.dry_run:
        srp.db.commit()

    # clean out topdir
    for g in glob.glob("{}/*".format(srp.work.topdir)):
        if os.path.isdir(g):
            shutil.rmtree(g)
        else:
            os.remove(g)


def uninstall_func():
    """remove files listed in pkg manifest"""
    # FIXME: MULTI: why not?  i guess directory removal might get odd, but
    #        that's already a hard question... where does the removal of
    #        /usr/local/share/foo happen?  when i remove the last file in
    #        foo?  what keeps us from accidentally removing share when i
    #        remove foo if there are no other files in share?
    pass


def uninstall_iter(unused, fname):
    """remove a file"""
    pass


def commit_func():
    """update pkg manifest"""
    # FIXME: MULTI:
    pass


# FIXME: add something to either register_feature or feature_struct to
#        enforce the following:
#
#        - all build/install/uninstall toplevel funcs happen AFTER core
#        - all final funcs happen BEFORE core
#
register_feature(
    feature_struct("core",
                   __doc__,
                   True,
                   build = stage_struct("core", build_func, [], []),
                   build_final = stage_struct("core", build_final, [], []),
                   install_iter = stage_struct("core", install_iter, [], []),
                   install_final = stage_struct("core", install_final, [], []),
                   uninstall = stage_struct("core", uninstall_func, [], []),
                   uninstall_iter = stage_struct("core", uninstall_iter,
                                                 [], []),
                   action = [("commit",
                              stage_struct("core", commit_func, [], []))]))
