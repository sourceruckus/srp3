AC_PREREQ([2.65])
AC_INIT([srp], [3.0.0-alpha], [michael.d.labriola@gmail.com])
AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE(dist-bzip2 no-dist-gzip)

AC_PROG_INSTALL
AC_PROG_MKDIR_P
AC_PROG_LN_S

LT_INIT([disable-static])

# FIXME: I want to eventually use xz for compression, so this will become 3.3
AM_PATH_PYTHON(3.2.0)
AM_CHECK_PYTHON_HEADERS()

PYTHON_CFLAGS=$($PYTHON-config --cflags)
AC_SUBST(PYTHON_CFLAGS)
PYTHON_LDFLAGS=$($PYTHON-config --ldflags)
AC_SUBST(PYTHON_LDFLAGS)

# FIXME: These macros can be used to disable functionality... but I don'
#        think they're really needed here.  Although, I could require >3.2
#        and then check explicitly for xz module.
#AM_CHECK_PYMOD(tarfile)
#AM_CHECK_PYMOD(multiprocessing)
#AM_CHECK_PYMOD(asdfooo)
#AM_CHECK_PYMOD()

AC_CONFIG_FILES([Makefile \
		 src/Makefile \
		 src/modules/Makefile \
		 src/modules/srp/Makefile \
		 src/modules/srp/features/Makefile])

# Do this one seperate, so we can add the chmod
#AC_CONFIG_FILES([src/ruckusrd], [chmod +x src/ruckusrd])

AC_OUTPUT
