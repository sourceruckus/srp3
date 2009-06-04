MAKEFILE      =	Makefile

PRODUCT	      =	srp
VERSION	      =	3.0.0
PACKAGEREV    =	1
DEVTAG	      = 

# Whereas the core SRP source files don't really require anythong beyond
# Python 2.3 or so, setting this officially to 2.5 means package maintainers
# can use anything added in 2.4 or 2.5 in their PREPOSTLIBs (the subprocess
# module, function decorators, etc).
MIN_PYTHON=2.5
PYTHON_INTERPRETER:=$(shell ./python-test ${MIN_PYTHON})

PREFIX = /usr
BINDIR = ${PREFIX}/bin
LIBDIR = ${PREFIX}/lib/srp
MANDIR = ${PREFIX}/share/man/man8
INFODIR = ${PREFIX}/share/info
DOCDIR = ${PREFIX}/share/doc/${PRODUCT}-${VERSIONSTRING}

# this is used to install into another rootfs
# example: you've booted up into source ruckus linux 3.0 and you
# want to install into your redhat rootfs which is mounted on
# /mnt/rh_root...  you just change SRP_ROOT_PREFIX to /mnt/rh_root
# and everything is taken care of.
SRP_ROOT_PREFIX = 

RUCKUS = ${PREFIX}/src/ruckus

RUCKUS_for_makefile = ${SRP_ROOT_PREFIX}${PREFIX}/src/ruckus

# how can we recursively create directories?
# works on: linux, hpux 10.20
RMKDIR = /bin/mkdir -p

# how can we get archive copies of a file?
# works on: linux
ACOPY = /bin/cp -a
# works on: hpux 10.20
#ACOPY="/bin/cp -pr"

# what shell should we invoke for our scripts?
SH = /bin/bash

# what is the preferred checksum algorithm?
CHECKSUM = "sha1"

BIN =	srp

LIBS =	sr.py \
	sr_package2.py \
	utils.py \
	Makefile.common

DOCS =	AUTHORS \
	BUGS \
	BUGS-SQUASHED \
	COPYING \
	ChangeLog \
	INSTALL \
	NEWS \
	README \
	TODO \
	examples

CONFIG = 	sr.py

MAN = 		srp.8
TEXINFO	= 	srp.texinfo
INFO = 		srp.info
PDF =		srp.pdf

SUBDIRS=examples

OFFICIALDIR=.
TEMPLATE_KEYS =	PYTHON_INTERPRETER LIBDIR VERSIONSTRING SRP_ROOT_PREFIX RUCKUS RMKDIR ACOPY SH CHECKSUM BINDIR

.PHONY: all mostly_all configure info ruckusdir install install-info dist
.PHONY: install-dist-srp uninstall clean
.PHONY: distclean docs man
.PHONY: ${SUBDIRS} ${SUBDIRS:=-clean} ${SUBDIRS:=-distclean}

all: dist mostly_all

include Makefile.common

mostly_all: bin libs man info #${SUBDIRS}

bin: configure ${BUILDDIR}/${BIN}

configure:
	@echo "PYTHON_INTERPRETER: ${PYTHON_INTERPRETER}"
	@if [ -z "${PYTHON_INTERPRETER}" ]; then \
	  echo "Couldn't find a suitable version of Python!"; \
	  echo "${DISTNAME} requires Python >= ${MIN_PYTHON}!"; \
	  exit 1; \
	fi

libs: ${LIBS:%=${BUILDDIR}/%}
	${PYTHON_INTERPRETER} -c "import compileall; compileall.compile_dir('${BUILDDIR}')"

man: ${BUILDDIR}/${MAN} ${BUILDDIR}/${MAN}.gz 

info: ${BUILDDIR}/${TEXINFO} ${BUILDDIR}/${INFO} ${BUILDDIR}/${INFO}.gz

docs: mostly_all docs-pdf docs-html examples

docs-pdf: ${BUILDDIR}/${PDF}

docs-html: ${BUILDDIR}/${TEXINFO}
	makeinfo --html -o ${BUILDDIR}/html $<

ruckusdir:
	mkdir -p ${RUCKUS_for_makefile}/build
	mkdir -p ${RUCKUS_for_makefile}/package
	mkdir -p ${RUCKUS_for_makefile}/tmp
	mkdir -p ${RUCKUS_for_makefile}/installed
	mkdir -p ${RUCKUS_for_makefile}/brp

install: install-bin install-libs install-man install-info ruckusdir

install-docs: install-pdf install-html install-examples

install-bin: bin
	install -vD ${BUILDDIR}/${BIN} ${BINDIR}/${BIN}

install-libs: libs
	install -vd ${LIBDIR}
	install -vD --mode=644 ${LIBS:%=${BUILDDIR}/%} ${LIBDIR}
	install -vD --mode=644 ${BUILDDIR}/*.pyc ${LIBDIR}

install-man: man
	install -vD --mode=644 ${BUILDDIR}/${MAN}.gz ${MANDIR}/${MAN}.gz


install-info: info
	install -vD --mode=644 ${BUILDDIR}/${INFO}.gz ${INFODIR}/${INFO}.gz
	install-info ${INFODIR}/${INFO}.gz ${INFODIR}/dir

install-pdf: docs-pdf
	install -vD --mode=644 ${BUILDDIR}/${PDF} ${DOCDIR}/${PDF}

install-html: docs-html
	cd ${BUILDDIR}/html && find . -type d -exec install -vd ${DOCDIR}/html/{} \;
	cd ${BUILDDIR}/html && find . ! -type d -exec install -v --mode=644 {} ${DOCDIR}/html/{} \;

install-examples: mostly_all
	cd examples && find . -type d -a ! -wholename \*/CVS\* -a ! -wholename \*/${BUILDDIR}\* -exec install -vd ${DOCDIR}/examples/{} \;
	cd examples && find . ! -type d -a ! -wholename \*/CVS\* -a ! -wholename \*/${BUILDDIR}\* -exec install -v --mode=644 {} ${DOCDIR}/examples/{} \;

dist: dist-srp

install-dist-srp: ruckusdir dist-srp mostly_all
	./${BUILDDIR}/srp -i ${DIST_SRP}

uninstall: uninstall-bin uninstall-libs uninstall-man uninstall-info
	rmdir --ignore-fail-on-non-empty ${RUCKUS_for_makefile}/build
	rmdir --ignore-fail-on-non-empty ${RUCKUS_for_makefile}/package
	rmdir --ignore-fail-on-non-empty ${RUCKUS_for_makefile}/tmp
	rmdir --ignore-fail-on-non-empty ${RUCKUS_for_makefile}/installed
	rmdir --ignore-fail-on-non-empty ${RUCKUS_for_makefile}/brp
	rmdir --ignore-fail-on-non-empty ${RUCKUS_for_makefile}

uninstall-docs: uninstall-info uninstall-pdf uninstall-html uninstall-examples

uninstall-bin:
	rm -f ${BINDIR}/${BIN}

uninstall-libs:
	rm -f ${LIBS:%=${LIBDIR}/%}
	rmdir --ignore-fail-on-non-empty ${LIBDIR}

uninstall-man:
	rm -f ${MANDIR}/${MAN}.gz

uninstall-info:
	rm -f ${INFODIR}/${INFO}.gz
	install-info --delete ${INFODIR}/${INFO}.gz ${INFODIR}/dir

uninstall-pdf:
	rm -f ${DOCDIR}/${PDF}
	rmdir --ignore-fail-on-non-empty ${DOCDIR}

uninstall-html:
	rm -rf ${DOCDIR}/html
	rmdir --ignore-fail-on-non-empty ${DOCDIR}

uninstall-examples:
	rm -rf ${DOCDIR}/examples
	rmdir --ignore-fail-on-non-empty ${DOCDIR}

clean: ${SUBDIRS:=-clean}
	find . \( -name \*~ -o -name .\#\* -o -name \*.pyc \) -exec rm -v {} \;
	rm -rf ${BUILDDIR} ${DISTNAME}

distclean: clean ${SUBDIRS:=-distclean}
	rm -f ${PRODUCT}-${VERSION}*.tar.bz2
	rm -f ${PRODUCT}-${VERSION}*.srp
	rm -f ${PRODUCT}-*${VERSION}*.brp

${SUBDIRS}:
	${MAKE} -C $@

${SUBDIRS:=-clean}:
	${MAKE} -C ${@:-clean=} clean

${SUBDIRS:=-distclean}:
	${MAKE} -C ${@:-distclean=} distclean
