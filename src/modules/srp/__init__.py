"""
The toplevel srp module.  This contains all the python back-end code for the
Source Ruckus Packager
"""

__all__ = ["cli", "notes", "toc", "features"]

for x in __all__:
    __import__(".".join([__name__, x]))
