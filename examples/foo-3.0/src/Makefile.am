AM_DEFAULT_SOURCE_EXT = .cpp

if !DIST_ONLY

bin_PROGRAMS = foo pizza

pizza_LDFLAGS = $(PYTHON_LIBS)

install-exec-hook:
	$(RM) -f $(DESTDIR)$(bindir)/bar
	(cd $(DESTDIR)$(bindir) && $(LN_S) foo bar)
	$(RM) -f $(DESTDIR)$(bindir)/baz
	(cd $(DESTDIR)$(bindir) && ln foo baz)

endif
