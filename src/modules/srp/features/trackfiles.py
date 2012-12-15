"""Feature module for TrackFiles, the core feature of any package manager"""

# this will add/remove filename from the recorded package contents.  other
# Features will track other details of installed files (e.g.,
# TrackFilesChecksum, TrackFilesPerms, TrackFilesLinks).

#from srp.features import *
#from srp.toc import *

import srp

def install(fname):
    """at install time, we need to log the file and actually install it"""
    #srp.toc.add_file(fname)
    #srp.toc.data[fname] = {'fname': fname}
    srp.toc.add_item(fname, 'fname', fname)


# actually, we don't really have to do anything at uninstall time...  we're
# removing the whole pacakge, so it's not like we have to remove every
# tracked file from the package's toc and then remove the toc itself...
#def uninstall():
#    toc.remove_file(fobj)


srp.register_feature("trackfiles",
                     __doc__,
                     inst = (install, []))

#register_feature("foo", "", inst = (lambda: None, ["trackfiles", "bar"]))
#register_feature("bar", "", inst = (lambda: None, ["baz"]))
#register_feature("baz", "", inst = (lambda: None, []))

# requesting 'foo' should get [trackfiles, baz, bar, foo]


import os
def foostat(fname):
    srp.toc.add_item(fname, 'stat', os.lstat(fname))

srp.register_feature("trackfilesstat",
                     "stat for file",
                     inst = (foostat, ["trackfiles"]))
