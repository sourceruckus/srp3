bin_PROGRAMS = foo pizza

foo_SOURCES = foo.cpp

pizza_CFLAGS = -I$(top_srcdir)/headers
pizza_LDADD = $(builddir)/libcrust.la
pizza_LDFLAGS = $(PTHREAD_LIBS)

lib_LTLIBRARIES = libcrust.la
libcrust_la_LDFLAGS = -release $(VERSION) -no-undefined


install-exec-hook:
	$(RM) -f $(DESTDIR)$(bindir)/bar
	(cd $(DESTDIR)$(bindir) && $(LN_S) foo bar)
	$(RM) -f $(DESTDIR)$(bindir)/baz
	(cd $(DESTDIR)$(bindir) && ln foo baz)
