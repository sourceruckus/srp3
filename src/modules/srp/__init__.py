"""
The toplevel srp module.  This contains all the python back-end code for the
Source Ruckus Packager
"""
# make sure that our __path__ variable is absolute!  if not, and we change the
# working directory, we won't be able to import any more submodules!
#
# FIXME: is this true for python3?
#
#        yes, it is.  however, the only time this is a problem is if we've
#        specified a non-absolute path in sys.path to find our module.  all
#        the default entries are absolute paths (excpept for '').  so this
#        shouldn't really be needed.
#
##import os.path
#
#for x in __path__[:]:
#    __path__.remove(x)
#    __path__.append(os.path.abspath(x))
#
# make __file__ absolute, too, just for consistency
#__file__ = os.path.abspath(__file__)
#
## clean up
#del os
#del x
