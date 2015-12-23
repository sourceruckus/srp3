pkgpyexec_PYTHON =
pkgpyexec_PYTHON += __init__.py
pkgpyexec_PYTHON += blob.py
pkgpyexec_PYTHON += cli.py
pkgpyexec_PYTHON += core.py
pkgpyexec_PYTHON += db.py
pkgpyexec_PYTHON += notes.py

nodist_pkgpyexec_PYTHON = config.py

SUBDIRS =
SUBDIRS += features

pkgpyexec_LTLIBRARIES =
pkgpyexec_LTLIBRARIES += _blob.la

_blob_la_CFLAGS = $(PYTHON_CFLAGS)
_blob_la_LDFLAGS = $(PYTHON_LDFLAGS) -module -avoid-version
_blob_la_SOURCES = blob.c

# this is so we can import srp from inside the source tree during development
#
# NOTE: Obviously, this will only work if we're compiling in-tree.  When
#       building out-of-tree, the resulting symlink is useless, but won't
#       hurt anything else.
all-local:
	$(RM) -f _blob.so
	$(LN_S) .libs/_blob.so _blob.so

clean-local:
	$(RM) -f _blob.so
