MAKEFILE      =	Makefile

PRODUCT	      =	foo
VERSION	      =	1.0
PACKAGEREV    =	1
DEVTAG	      =	

OFFICIALDIR   =	.
TEMPLATE_KEYS =	VERSIONSTRING

PREFIX	      =	/usr
BINDIR	      =	${PREFIX}/bin
DOCDIR	      =	${PREFIX}/share/doc

BIN	      =	foo

all: dist ${SRP}
	@echo "done"

Makefile.common: $(wildcard ../../Makefile.common)
	cp -dpR $< .

-include Makefile.common

SRP:=$(shell pwd)/../../${BUILDDIR}/srp

${BUILDDIR}/${BIN}: ${BUILDDIR}/${BIN}.cpp
	${CXX} -o $@ $<

install: ${BUILDDIR}/${BIN} ${MAKEFILE}
	install -vD $< ${DESTDIR}${BINDIR}/${BIN}

install-docs: ${BUILDDIR}/README ${MAKEFILE}
	mkdir -p ${DESTDIR}${DOCDIR}/${DISTNAME}
	cp -vdpR $< ${DESTDIR}${DOCDIR}/${DISTNAME}
	cp -vdpR docs ${DESTDIR}${DOCDIR}/${DISTNAME}
	ln -fs ${DESTDIR}${DOCDIR}/${DISTNAME} ${DESTDIR}${DOCDIR}/${PRODUCT}

clean:
	find . -name \*~ -exec rm -v {} \;
	rm -rf ${BUILDDIR} ${DISTNAME}

distclean: clean
	rm -f ${BIN}
	rm -f ${DIST_BZ2} ${DIST_SRP} ${PRODUCT}-*${VERSIONSTRING}-${PACKAGEREV}*.brp

dist: dist-srp
