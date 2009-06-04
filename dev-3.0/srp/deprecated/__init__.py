import os.path

# make sure that our __path__ variable is absolute!  if not, and we change the
# working directory, we won't be able to import any more submodules!
for x in __path__[:]:
    __path__.remove(x)
    __path__.append(os.path.abspath(x))

# make __file__ absolute, too, just for consistency
__file__ = os.path.abspath(__file__)

# clean up
del os
del x
