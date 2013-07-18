"""Feature module for managing checksums.

This feature records checksums for each installed file and allows the user to
verify files on demand after installation.
"""

from srp.features import *

# FIXME: MULTI:
def gen_sum(work, fname):
    """gen sha of a file, update pkg manifest"""
    pass

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
                                               [], []),
                   uninstall = stage_struct("checksum", verify_sums,
                                            [], ["core"]),
                   action = [("commit",
                              stage_struct("checksum", commit_func, [], [])),
                             ("verify",
                              stage_struct("checksum", verify_sums, [], []))]))
