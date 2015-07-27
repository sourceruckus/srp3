AC_PREREQ([2.65])
AC_INIT([srp-example], [3.0.0], [michael.d.labriola@gmail.com])
AC_CONFIG_AUX_DIR([.])
AC_CONFIG_SRCDIR([src/foo.cpp])
AC_CONFIG_HEADERS([config.h])

AM_INIT_AUTOMAKE(dist-xz no-dist-gzip foreign)

AC_PROG_CXX
AC_PROG_CC
AC_PROG_INSTALL
AC_PROG_MKDIR_P
AC_PROG_LN_S

AC_CHECK_LIB(pthread, main,
  [PTHREAD_LIBS=-lpthread],
  [AC_MSG_FAILURE(cannot find libpthread)])
AC_SUBST(PTHREAD_LIBS)

# NOTE: It would appear that libreadline.so has undefined references unless
#       you also link against libncurses.  I think that means that
#       libreadline itself should be linked against libncurses, but
#       whatever.
#
#       This is here as a test-case in our example specifically because
#       libreadline has given srp problems in the past and I thought it
#       was my bad.  I'm thinking it was the packager of readline's
#       mistake (ironically, probably me as well).
#
AC_CHECK_LIB(ncurses, main, [], AC_MSG_WARN(ncurses test failed))
AC_CHECK_LIB([readline], [main], [], [AC_MSG_WARN([readline test failed])], [-lncurses])

AC_CONFIG_FILES([Makefile \
		 src/Makefile \
		 docs/Makefile \
		 headers/Makefile])

AC_OUTPUT
