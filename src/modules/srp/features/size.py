"""Feature module for tracking installed size

This feature keeps tabs on disk utilization during install.
"""

import os
import stat

import srp
from srp.features import *


class NotesSize(srp.SrpObject):
    def __init__(self):
        self.total = 0


def reset_notes():
    srp.work.notes.size.total = 0


def increment_notes_build(fname):
    x = srp.work.manifest[fname]['tinfo']
    if not x.isreg():
        return
    srp.work.notes.size.total += x.size


# NOTE: The size is recalculated at install-time because some other
#       Feature may have changed the file once installed (i.e., size
#       stored at build-time may be wrong).
#
def increment_notes_install(fname):
    """add size of fname to total in NOTES"""
    x = srp.work.manifest[fname]

    # only count regular files
    #
    # FIXME: Do we want to add an arbitrary ammount to size for non-reg
    #        files?  Directories do indeed take up some space, right?
    #        What about symlinks?  Hardlinks?  Fifos?  Devnodes?
    if not x['tinfo'].isreg():
        return

    n = srp.work.notes

    # NOTE: The file is already installed on disk, so we don't need to mess
    #       with the old BLOB
    #
    # FIXME: DESTDIR or --root
    try:
        path = os.environ["DESTDIR"] + fname
    except:
        path = fname

    n.size.total += os.stat(path)[stat.ST_SIZE]


def size_info(p):
    return "Size: {} bytes".format(p.notes.size.total)


# FIXME: this should also register a commit action so we can recalc size
#        after installation if we want to

register_feature(
    feature_struct("size",
                   __doc__,
                   True,
                   info = size_info,
                   build_iter = stage_struct("size", increment_notes_build,
                                             ["core"], []),
                   install = stage_struct("size", reset_notes, ["core"], []),
                   install_iter = stage_struct("size", increment_notes_install,
                                               ["core"], [])))
