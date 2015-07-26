AC_PREREQ([2.65])

m4_define(srp_major_version, 3)
m4_define(srp_minor_version, 0)
m4_define(srp_micro_version, 0)
m4_define(srp_devtag, [alpha2])
m4_ifnblank(srp_devtag,
	[m4_define(srp_version, srp_major_version.srp_minor_version.srp_micro_version-srp_devtag)],
	[m4_define(srp_version, srp_major_version.srp_minor_version.srp_micro_version)])

AC_INIT([The Source Ruckus Packager], [srp_version], [michael.d.labriola@gmail.com], [srp])
AC_CONFIG_AUX_DIR([.])
AC_CONFIG_MACRO_DIR([m4])

AC_SUBST(SRP_MAJOR_VERSION, srp_major_version)
AC_SUBST(SRP_MINOR_VERSION, srp_minor_version)
AC_SUBST(SRP_MICRO_VERSION, srp_micro_version)
AC_SUBST(SRP_DEVTAG, srp_devtag_version)
AC_SUBST(SRP_BUILD_YEAR, 2015)

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

# FIXME: These macros can be used to disable functionality... but I don't
#        think they're really needed here.  Although, I could require >3.2
#        and then check explicitly for xz module.
#AM_CHECK_PYMOD(tarfile)
#AM_CHECK_PYMOD(multiprocessing)
#AM_CHECK_PYMOD(asdfooo)
#AM_CHECK_PYMOD()

AC_CONFIG_FILES([Makefile
		 src/Makefile
		 src/modules/Makefile
		 src/modules/srp/Makefile
		 src/modules/srp/config.py
		 src/modules/srp/features/Makefile
		 examples/Makefile
		 ])

# Do this one seperate, so we can add the chmod
#AC_CONFIG_FILES([src/ruckusrd], [chmod +x src/ruckusrd])

AC_CONFIG_SUBDIRS(examples/foo-3.0)

AC_OUTPUT
