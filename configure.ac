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
AC_SUBST(SRP_DEVTAG, srp_devtag)
AC_SUBST(SRP_BUILD_YEAR, 2015)

AM_INIT_AUTOMAKE(dist-xz no-dist-gzip tar-pax foreign subdir-objects color-tests)

AC_PROG_INSTALL
AC_PROG_MKDIR_P
AC_PROG_LN_S

LT_INIT([disable-static])

# enable/disable different compressors
#
min_python=3.2.0
AC_ARG_ENABLE(gzip,
  AS_HELP_STRING(--enable-gzip=LEVEL,
    [Enable gzip compressor with specified default compression level
     [default: 9]]),
  comp_gzip=$enableval,
  comp_gzip=9)
AS_IF([test x$comp_gzip = xyes], comp_gzip=9)
AS_IF([test x$comp_gzip != xno], comp_mod_gzip=gzip, comp_gzip=-1)
AC_SUBST(COMP_GZIP, $comp_gzip)

AC_ARG_ENABLE(bzip2,
  AS_HELP_STRING(--enable-bzip2=LEVEL,
    [Enable bzip2 compressor with specified default compression level
     [default: 9]]),
  comp_bzip2=$enableval,
  comp_bzip2=9)
AS_IF([test x$comp_bzip2 = xyes], comp_bzip2=9)
AS_IF([test x$comp_bzip2 != xno], comp_mod_bzip2=bz2, comp_bzip2=-1)
AC_SUBST(COMP_BZIP2, $comp_bzip2)

AC_ARG_ENABLE(lzma,
  AS_HELP_STRING(--enable-lzma=LEVEL,
    [Enable lzma compressor with specified default compression level
     [default: 0]]),
  comp_lzma=$enableval,
  comp_lzma=0)
AS_IF([test x$comp_lzma = xyes], comp_lzma=0)
AS_IF([test x$comp_lzma != xno],
  [comp_mod_lzma=lzma
   min_python=3.3.0],
  [comp_lzma=-1])
AC_SUBST(COMP_LZMA, $comp_lzma)

AC_ARG_WITH(default-compressor,
  AS_HELP_STRING(--with-default-compressor=COMP,
    [Use COMP as default compressor [default: lzma]]),
  comp_default=$withval,
  AS_IF([test $comp_lzma -ne -1], comp_default=lzma,
    AS_IF([test $comp_bzip2 -ne -1], comp_default=bzip2,
      AS_IF([test $comp_gzip -ne -1], comp_default=gzip,
        AC_MSG_ERROR([No suitable compressor sellected])))))
AC_SUBST(COMP_DEFAULT, $comp_default)

# check for python
#
# NOTE: We decide on min_python based on desired compressor.  The lzma
#       module wasn't added until 3.3.0, otherwise 3.2.0 would work for
#       us.
#
AM_PATH_PYTHON($min_python)
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
   $comp_mod_gzip
   $comp_mod_bzip2
   $comp_mod_lzma
  ])
m4_foreach_w([M], NEEDED_MODS,
  [AS_IF([test "M" != ""],
     AM_CHECK_PYMOD(M, [],
       [],
       [AC_MSG_ERROR([Missing required Python module: "M"])]))
  ])


# check for sed /w --in-place
#
# NOTE: Using sed -i in makefiles is frowned upon because it's not
#       portable.  We make 'sed -i' a requirement and check for it here
#       because... I like it and I think pretty much everyone has it.  But
#       I do want to get bonked upside the head if it's going to cause
#       problems.
#
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


echo
echo
echo
echo "------------------------------------------------------------------------"
echo "$PACKAGE_STRING"
echo "------------------------------------------------------------------------"
echo
echo "Configuration Options Summary:"
echo
echo "Python.................: $PYTHON ($PYTHON_VERSION)"
echo
echo "Compressors (disabled or default compression level):"
echo "  gzip.................: $comp_gzip"
echo "  bzip2................: $comp_bzip2"
echo "  lzma.................: $comp_lzma"
echo
echo "Options:"
echo "  Default Compressor...: $comp_default"
echo
echo "Installation:"
echo "  prefix...............: $prefix"
echo
