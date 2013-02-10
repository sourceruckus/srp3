"""Feature module for the core functionality of SRP.

This feature module implements the core functionality of the package manager
(i.e., creating, building, installing packages).
"""

import hashlib
import io
import os
import stat
import subprocess
import tarfile
import tempfile

from srp.features import *

def create_func(n):
    """create tar of NOTES, source, SHA"""
    # locate all needed files
    #
    # NOTE: We expect these to all be relative to the directory containing
    #       the notes file.
    flist = [os.path.basename(n.filename), n.info.sourcefilename]
    try:
        flist.extend(n.info.extra.split())
    except:
        pass

    print(flist)

    # create tarball
    #
    # NOTE: At this point, the tarball is unnamed and spooled in RAM.  When
    #       we're all done, we'll write the file to disk in the original working
    #       directory
    #
    # FIXME: The max_size should be configurable... systems that have little RAM
    #        might want to not spool anything, whereas systems with tons might
    #        want to improve performace by using a huge size.
    #
    # FIXME: It's not clear from the docs, but reading the tempfile sources
    #        indicates that max_size=0 (the default) means there is no max
    #        size (i.e., won't ever rollover automatically).
    #
    # NOTE: We add the source file and any extra files specified in the
    #       NOTES file, the NOTES file itself, and a SHA file containing
    #       checksums of all added files.
    sha = []
    max_spool=10*2**20
    # create our tempfile obj
    with tempfile.SpooledTemporaryFile(max_size=max_spool) as pkg:
        # create a TarFile obj using the tempfile obj
        with tarfile.open(fileobj=pkg, mode="w") as tar:
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
                    print("adding {} as {}".format(f.name, arcname))
                    tar.addfile(tar.gettarinfo(arcname=arcname, fileobj=f),
                                fileobj=f)
                    # rewind and generate a SHA entry
                    f.seek(0)
                    sha.append("  ".join((hashlib.sha1(f.read()).hexdigest(),
                                           arcname)))

            # create the SHA file and add it to the pkg
            #
            # NOTE: Can't use SpooledTemporaryFile here because it has to be a
            #       real file in order for gettarinfo to work properly
            with tempfile.TemporaryFile() as f:
                f.write("\n".join(sha).encode())
                f.seek(0)
                tar.addfile(tar.gettarinfo(arcname="SHA", fileobj=f),
                            fileobj=f)

        # copy pkg to pwd
        pkg.seek(0)
        pname = "{}-{}-{}.srp".format(n.info.name, n.info.version,
                                      n.info.revision)
        print(pname)
        with open(pname, "wb") as f:
            f.write(pkg.read())


def build_func(work):
    """run build script to populate payload dir, then create TarInfo objects for
    all files"""
    # create ruckus dir in tmp
    work['dir'] = tempfile.mkdtemp(prefix="srp-")

    # create ruckus dir tree
    for x in ["package", "build", "tmp"]:
        os.makedirs(work['dir'] + "/" + x)

    # extract package contents
    #
    # NOTE: This is needed so that build scripts can access other misc files
    #       they've included in the srp (e.g., apply a patch, install an
    #       externally maintained init script)
    work['tar'].extractall(work['dir'] + "/package")

    # extract source tarball
    t = tarfile.open(work['dir'] + "/package/" + work['n'].info.sourcefilename)
    t.extractall(work['dir'] + "/build")
    sourcedir=

    # create build script
    #
    # FIXME: do i really need to create an executable script file?  or can i
    #        just somehow spawn a subprocess using the contents of the buf?
    with open(work['dir'] + "/build/srp_go", 'w') as f:
        f.write(work['n'].script.buf)
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
    subprocess.check_call(["./srp_go"], cwd=work['dir']+'/build/'+work['n'].info., env=new_env)

    # create global BLOB objects
    #
    # NOTE: The global TarFile object and list of TarInfo objects are created
    #       now, but nothing is added to the archive yet.  This is to allow
    #       other features a chance to tweak things.  At the very end (i.e.,
    #       when all other feature functions have been executed), all the
    #       TarInfo objects (and their associated file objects) will be added to
    #       the archive.

    # append brp section to NOTES file in mem

    # add NOTES file to toplevel pkg archive (the brp)


def install_func():
    """untar payload, install tarinfo in ruckus/installed/pkgname/sha"""
    pass

def uninstall_func():
    """remove files listed in pkg manifest"""
    pass

def commit_func():
    """update pkg manifest"""
    pass

register_feature(feature_struct("core",
                                __doc__,
                                True,
                                create = stage_struct("core", create_func, [], []),
                                build = stage_struct("core", build_func, [], []),
                                install = stage_struct("core", install_func, [], []),
                                uninstall = stage_struct("core", uninstall_func, [], []),
                                action = [("commit", stage_struct("core", commit_func, [], []))]))
