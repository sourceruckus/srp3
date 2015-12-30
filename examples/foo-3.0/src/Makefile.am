bin_PROGRAMS = foo pizza

foo_SOURCES = foo.cpp

pizza_CFLAGS = -I$(top_srcdir)/headers
pizza_LDADD = $(builddir)/libpizzacrust.la
pizza_LDFLAGS = $(PTHREAD_LIBS)

lib_LTLIBRARIES = libpizzacrust.la
libpizzacrust_la_LDFLAGS = -release $(VERSION) -no-undefined


install-exec-hook:
	$(RM) -f $(DESTDIR)$(bindir)/foosymlink
	(cd $(DESTDIR)$(bindir) && $(LN_S) foo foosymlink)
	$(RM) -f $(DESTDIR)$(bindir)/foohardlink
	(cd $(DESTDIR)$(bindir) && ln foo foohardlink)
