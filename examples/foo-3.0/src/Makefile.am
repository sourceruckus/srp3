bin_PROGRAMS = foo

AM_DEFAULT_SOURCE_EXT = .cpp

install-exec-hook:
	$(RM) -f $(DESTDIR)$(bindir)/bar
	(cd $(DESTDIR)$(bindir) && $(LN_S) foo bar)
