AC_PREREQ([2.65])
AC_INIT([srp-example], [3.0.0], [michael.d.labriola@gmail.com])
AC_CONFIG_SRCDIR([src/foo.cpp])
AC_CONFIG_HEADERS([config.h])

AM_INIT_AUTOMAKE(dist-bzip2 no-dist-gzip)

AC_PROG_CXX
AC_PROG_CC
AC_PROG_INSTALL
AC_PROG_MKDIR_P
AC_PROG_LN_S

# look for pkg-config
PKG_PROG_PKG_CONFIG

# detect python
PKG_CHECK_MODULES(PYTHON, python3)

# NOTE: It would appear that libreadline.so has undefined references unless
#       you also link against libncurses.  I think that means that
#       libreadline itself should be linked against libncurses, but
#       whatever.
AC_CHECK_LIB(ncurses, main, [], AC_MSG_FAILURE(ncurses test failed))
AC_CHECK_LIB([readline], [main], [], [AC_MSG_FAILURE([readline test failed])], [-lncurses])


AC_CONFIG_FILES([Makefile \
		 src/Makefile \
		 docs/Makefile \
		 headers/Makefile])

AC_OUTPUT
