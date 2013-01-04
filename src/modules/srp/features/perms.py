"""Feature module for specifying permissions.

This feature allows package maintainers to override file permissions resulting
from the build script via the NOTES file (as apposed to putting chmod/chown
statements in the script).

NOTE: This is the only appropriate way to set file ownership.  Using chown in
      the NOTES file's build script will not work if a package is built as
      non-root.
"""

from srp.features import *

def install_func():
    """gen sha of each file, update pkg manifest"""
    pass

def verify_func():
    """gen sha of each file, compare with pkg manifest"""
    pass

register_feature(feature_struct("perms",
                                __doc__,
                                install = stage_struct("perms", install_func, [], ["core"]),
                                action = [("verify", stage_struct("perms", verify_func, [], []))]))
