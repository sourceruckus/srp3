"""Feature module for the core functionality of SRP.

This feature module implements the core functionality of the package manager
(i.e., creating, building, installing packages).
"""

import hashlib
import io
import os
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


def build_func(p, brp):
    """run build script to populate payload dir, then create TarInfo objects for
    all files"""
    # create tmp dir
    brp['foo'] = "hello"

    # extract source tarball

    # run build script

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
