PRODUCT	      =	srpdev
DEVDATE	      =	`date +"%Y%m%d%H%M%S"`

DISTNAME      =	${PRODUCT}-${DEVDATE}


all: dist

dist: dist-bzip2

dist-bzip2:
	@echo "DISTNAME: ${DISTNAME}"
	tar jcf ../${DISTNAME}.tar.bz2 .

