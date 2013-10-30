"""Feature module for tracking installed size

This feature keeps tabs on disk utilization during install.
"""

import os
import stat

from srp.features import *


class notes_size:
    def __init__(self):
        self.total = 0


def increment_notes(work, fname):
    """add size of fname to total in NOTES"""
    x = work["manifest"][fname]

    # only count regular files
    #
    # FIXME: Do we want to add an arbitrary ammount to size for non-reg
    #        files?  Directories do indeed take up some space, right?
    #        What about symlinks?  Hardlinks?  Fifos?  Devnodes?
    if not x['tinfo'].isreg():
        return

    n = work["notes"]

    # NOTE: We can't use the size recorded in TarInfo here because some
    #       other Feature may have changed the file once installed
    # NOTE: The file is already installed on disk, so we don't need to mess
    #       with the old BLOB
    #
    # FIXME: DESTDIR or --root
    try:
        path = os.environ["DESTDIR"] + fname
    except:
        path = fname

    n.size.total += os.stat(path)[stat.ST_SIZE]


# FIXME: this should also register a commit action so we can recalc size
#        after installation if we want to

register_feature(
    feature_struct("size",
                   __doc__,
                   True,
                   install_iter = stage_struct("size", increment_notes,
                                               ["core"], [])))
