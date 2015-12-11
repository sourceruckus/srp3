dist_bin_SCRIPTS = srp

dist_pkgdata_DATA = functions

SUBDIRS =
SUBDIRS += modules

install-exec-hook:
	sed -i 's|^#!.*|#!$(PYTHON)|' $(DESTDIR)$(bindir)/srp
	sed -i 's|__DEV__||' $(DESTDIR)$(bindir)/srp
