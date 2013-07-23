"""The toplevel srp module.

This module contains all the python back-end code for the Source Ruckus
Packager.  Importing it will automatically include all submodules.
"""

# FIXME: was there some reason for the strange ordering here?
__all__ = ["config", "features", "notes", "cli", "blob"]

for x in __all__:
    __import__(".".join([__name__, x]))
