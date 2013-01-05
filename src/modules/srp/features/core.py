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
    flist = [n.info.sourcefilename]
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
    # FIXME: the max_size should be configurable... systems that have little RAM
    #        might want to not spool anything, whereas systems with tons might
    #        want to improve performace by using a huge size.
    sha = []
    max_spool=10*2**20
    with tempfile.SpooledTemporaryFile(max_size=max_spool) as pkg:
        with tarfile.open(fileobj=pkg, mode="w") as tar:
            for fname in flist:
                with open(os.path.join(os.path.dirname(n.filename), fname),
                          mode='rb') as f:
                    arcname = os.path.basename(fname)
                    tar.addfile(tar.gettarinfo(arcname=arcname, fileobj=f))
                    #tar.add(f, arcname=os.path.basename(fname))
                    f.seek(0)
                    sha.append("  ".join((hashlib.sha1(f.read()).hexdigest(),
                                           arcname)))
            #with tempfile.SpooledTemporaryFile(max_size=max_spool) as f:
            with tempfile.TemporaryFile() as f:
                f.write("\n".join(sha).encode())
                f.seek(0)
                tar.addfile(tar.gettarinfo(arcname="SHA", fileobj=f))

        # copy pkg to pwd
        pkg.seek(0)
        pkg.rollover()
        with open("foo.srp", "wb") as f:
            f.write(pkg.read())

    # locate source tarball
    #print(n.info.sourcefilename, n.info.extra.split())

    # grab extra content

    # generate checksums of all files in package

    # write package to disk


def build_func():
    """run build script to create tar of payload"""
    pass

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
