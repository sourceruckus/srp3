"""Feature module for stripping documentation from pkg at install-time

This feature removes all documentation (*/share/docs/*) from a package at
install-time, prior to the docs getting installed or the manifest getting
recorded.
"""

import fnmatch

import srp
from srp.features import *

# NOTE: This is implemented as an install_func instead of an iter func to
#       save us the effort of running through any other funcs for the
#       removed files.

doc_patterns = ["*/share/doc", "*/share/doc/*"]


def install_func():
    """remove all documentation from manifest"""
    for x in srp.work.install.manifest:
        for pat in doc_patterns:
            if fnmatch.fnmatch(x, pat):
                # remove from manifest
                del srp.work.install.manifest[x]

                # skip to next file
                break


# FIXME: this should also register an action so we can strip after
#        installation if we want to

def action_func():
    pass


register_feature(
    feature_struct("strip_docs",
                   __doc__,
                   False,
                   install = stage_struct("strip_docs", install_func,
                                          [], ["core"]),
                   action = [("strip_docs",
                              stage_struct("strip_docs", action_func,
                                           [], []))]))
