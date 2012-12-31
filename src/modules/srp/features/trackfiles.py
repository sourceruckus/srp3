"""Feature module for TrackFiles, the core feature of any package manager"""

# this will add/remove filename from the recorded package contents.  other
# Features will track other details of installed files (e.g.,
# TrackFilesChecksum, TrackFilesPerms, TrackFilesLinks).

import srp

from srp.features import *

# FIXME: I haven't decided yet whether the trackfiles features actually installs
# the file...  I think it just tracks the name in toc, and later on we actually
# install...?

def track_fname(fname):
    srp.toc.add_item(fname)


# actually, we don't really have to do anything at uninstall time...  we're
# removing the whole pacakge, so it's not like we have to remove every
# tracked file from the package's toc and then remove the toc itself...
#def uninstall():
#    toc.remove_file(fobj)


register_feature(feature_struct("trackfiles",
                                __doc__,
                                install = stage_struct("trackfiles", track_fname, [], [])))


import os
def track_stat(fname):
    srp.toc.add_item(fname, 'stat', os.lstat(fname))

register_feature(feature_struct("trackfilesstat",
                                "stat for file",
                                install = stage_struct("trackfilesstat", track_stat, ["trackfiles"], [])))


def track_foo(fname):
    pass

register_feature(feature_struct("trackfilesfoo",
                                "foo",
                                install = stage_struct("trackfilesfoo", track_foo, ["trackfiles"], ["trackfilesstat"])))
