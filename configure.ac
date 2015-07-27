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

AM_INIT_AUTOMAKE(dist-xz no-dist-gzip tar-pax foreign subdir-objects color-tests)

AC_PROG_INSTALL
AC_PROG_MKDIR_P
AC_PROG_LN_S

LT_INIT([disable-static])

# NOTE: I've tested w/ 3.2 enough to be pretty sure it works.  We have
#       switched to using xz compression, though, and the lzma module
#       wasn't officially added until 3.3.  Theoretically, you could
#       backport lzma to 3.2 and it would work...
#
AM_PATH_PYTHON(3.3.0)
AM_CHECK_PYTHON_HEADERS()

PYTHON_CFLAGS=$($PYTHON-config --cflags)
AC_SUBST(PYTHON_CFLAGS)
PYTHON_LDFLAGS=$($PYTHON-config --ldflags)
AC_SUBST(PYTHON_LDFLAGS)

# check for required python modules
#
# NOTE: By setting the Python requirement to >= 3.3 above, we *should*
#       have all these.  But let's double-check just to be absolutely
#       sure.  Specifically, lzma could have been left out of the system's
#       Python compilation if the lzma libraries were missing.
#
AC_DEFUN([NEEDED_MODS],
  [dnl NOTE: comment out via dnl inside AC_DEFUN
   tarfile
   multiprocessing
   lzma
  ])
m4_foreach_w([M], NEEDED_MODS,
  [AM_CHECK_PYMOD(M, [],
     [],
     [AC_MSG_ERROR([Missing required Python module: M])])
  ])

# check for sed /w --in-place
#
# NOTE: Using sed -i in makefiles is frowned upon because it's not
#       portable.  We make 'sed -i' a requirement and check for it here
#       because... I like it and I think pretty much everyone has it.  But
#       I do want to get bonked upside the head if it's going to cause
#       problems.
AC_PROG_SED
AS_TMPDIR(srp-)
AC_CACHE_CHECK([whether $ac_cv_path_SED supports -i], [srp_cv_sed_i],
  [AS_IF([touch $tmp/sed && $ac_cv_path_SED -i 's|||' $tmp/sed 2>/dev/null],
      srp_cv_sed_i=yes,
      srp_cv_sed_i=no)])
rm -f $tmp/sed && rmdir $tmp
if test $srp_cv_sed_i != yes; then
    AC_MSG_ERROR([SRP requires sed -i])
fi


AC_CONFIG_FILES([Makefile
		 src/Makefile
		 src/modules/Makefile
		 src/modules/srp/Makefile
		 src/modules/srp/config.py
		 src/modules/srp/features/Makefile
		 ])

AC_OUTPUT
