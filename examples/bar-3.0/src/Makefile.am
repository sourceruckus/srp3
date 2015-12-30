bin_PROGRAMS = bar bread

bar_SOURCES = bar.cpp

bread_CFLAGS = -I$(top_srcdir)/headers
bread_LDADD = $(builddir)/libbreadcrust.la
bread_LDFLAGS = $(PTHREAD_LIBS)

lib_LTLIBRARIES = libbreadcrust.la
libbreadcrust_la_LDFLAGS = -release $(VERSION) -no-undefined
