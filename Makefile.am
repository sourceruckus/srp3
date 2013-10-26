ACLOCAL_AMFLAGS = -I m4

SUBDIRS =
SUBDIRS += src
SUBDIRS += examples

EXTRA_DIST =
EXTRA_DIST += README-3.0

all-local:
	$(MAKE) -C examples/foo-3.0 dist

install-data-local:
	$(MKDIR_P) $(DESTDIR)$(pkgdatadir)
	$(INSTALL_DATA) examples/foo-3.0/*.tar.* $(DESTDIR)$(pkgdatadir)/
	$(INSTALL_DATA) examples/foo-3.0/*.notes $(DESTDIR)$(pkgdatadir)/
