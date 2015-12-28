"""Feature module for stripping debug symbols at install-time

This feature strips debug symbols (all unneeded symbols, actually) at
install-time, prior to checksums getting recorded.
"""

import subprocess

import srp
from srp.features import *

# NOTE: This has to happen AFTER core (i.e., after the files are installed
#       on the system) because we can't modify the files in the BLOB archive.
#
# FIXME: We COULD change this, but we'd have to add new, stripped versions
#        of all files back to the BLOB archive... or create a new one
#        entirely and replace it prior to running core...  We'll see.
#
#        It would be nice to be able to do it prior to core, if we can make
#        it work efficiently, because that way the user won't have to have
#        as much disk space available at install time.  And if stripping
#        fails, we won't have a half-installed package on our hands...
#
#        Although, a hidden benefit of doing it after core is that the
#        install_func and our strip_debug action can use the exact same
#        function.
def install_func(fname):
    """strip --strip-unneeded from a file"""
    x = srp.work.install.manifest[fname]

    # only strip actual files
    if not x['tinfo'].isreg():
        return

    # FIXME: DESTDIR or --root
    try:
        path = os.environ["DESTDIR"] + fname
    except:
        path = fname

    go = ["strip", "--strip-unneeded", path]
    # NOTE: I'd love to do a check_call here, but strip returns error if
    #       the file isn't an elf binary... and I really don't feel like
    #       checking for that.
    #
    # FIXME: should I check error status somehow?
    subprocess.call(go)



# FIXME: this should also register an action so we can strip after
#        installation if we want to

register_feature(
    feature_struct("strip_debug",
                   __doc__,
                   False,
                   install_iter = stage_struct("strip_debug", install_func,
                                               ["core"],
                                               ["?checksum", "?size"]),
                   action = [("strip_debug",
                              stage_struct("strip_debug", install_func,
                                           [], []))]))

# FIXME: what happens if checksum isn't enabled?
