"""Feature module for tracking installed size

This feature keeps tabs on disk utilization during install.
"""

import os
import stat

from srp.features import *

def increment_notes(work, fname):
    """add size of fname to total in NOTES"""
    x = work["manifest"][fname]

    # only count regular files
    if not x['tinfo'].isreg():
        return

    n = work["notes"]

    try:
        total = int(n.additions["installed"]["size"])
    except:
        total = 0

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

    total += os.stat(path)[stat.ST_SIZE]

    n.additions["installed"]["size"] = str(total)


# FIXME: this should also register a commit action so we can recalc size
#        after installation if we want to

register_feature(
    feature_struct("size",
                   __doc__,
                   True,
                   install_iter = stage_struct("size", increment_notes,
                                               ["core"], [])))
