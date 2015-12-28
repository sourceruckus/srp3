"""The toplevel srp module.

This module contains all the python back-end code for the Source Ruckus
Packager.  Importing it will automatically include all submodules.
"""

from srp.core import *

params = core.RunTimeParameters()

# FIXME: was there some reason for the strange ordering here?
#
# FIXME: was setting __all__ and iterating over it... but not sure why now
#
for x in ["config", "features", "notes", "cli", "blob", "db"]:
    __import__(".".join([__name__, x]))
del x

work = features.WorkBag()


# FIXME: log = SrpLogger()
