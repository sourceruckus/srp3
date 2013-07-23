"""Feature module for managing checksums.

This feature records checksums for each installed file and allows the user to
verify files on demand after installation.
"""

import hashlib

from srp.features import *

# FIXME: MULTI:
def gen_sum(work, fname):
    """gen sha of a file, update pkg manifest"""
    x = work["manifest"][fname]

    # only record checksum of regular files
    if not x['tinfo'].isreg():
        return

    # FIXME: we don't really want to hardcode sha1 do we?
    sha = hashlib.new("sha1")

    # NOTE: The file is already installed on disk, so we don't need to mess
    #       with the old BLOB
    #
    # FIXME: DESTDIR or --root
    try:
        path = os.environ["DESTDIR"] + fname
    except:
        path = fname
    with open(path, "rb") as f:
        sha.update(f.read())

    # FIXME: crap.  i can't do this because TarInfo is implemented using
    #        __slots__...  looks like i need to go back to
    #        work['manifest'][fname] = {tinfo: TarInfo} so that I can add to
    #        this bugger.
    #
    #        i wonder if i should throw the NOTES file in there too and
    #        pickle the whole thing into a single file on disk...? or leave
    #        NOTES seperate so it's easier for users to go look at?
    x["checksum"] = sha.hexdigest().encode()

    # put our updated manifest entry back into the global map
    work['manifest'][fname] = x


def verify_sums(work):
    """verify, issue warning"""
    # FIXME: MULTI: this one can't be an iter func, because we would want it
    #        to happen before anything else.  But we COULD put an
    #        independant multiprocessing block in here to use multiple cores
    #        nicely.
    pass

# FIXME: i don't really remember how i was planning on implementing this.
#        if i have a commit action, i'll want it to have it's own iter
#        stages... we'll want to redo parts of the perms, core, deps, and
#        checksum features here...
def commit_func():
    """update pkg manifest"""
    # FIXME: MULTI:
    pass


register_feature(
    feature_struct("checksum",
                   __doc__,
                   True,
                   install_iter = stage_struct("checksum", gen_sum,
                                               ["core"], []),
                   uninstall = stage_struct("checksum", verify_sums,
                                            [], ["core"]),
                   action = [("commit",
                              stage_struct("checksum", commit_func, [], [])),
                             ("verify",
                              stage_struct("checksum", verify_sums, [], []))]))
