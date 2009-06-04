SUBDIRS=foo-1.0 foo-2.0


.PHONY: all clean distclean
.PHONY: ${SUBDIRS} ${SUBDIRS:=-clean} ${SUBDIRS:=-distclean}

all: ${SUBDIRS}

clean: ${SUBDIRS:=-clean}

distclean: ${SUBDIRS:=-distclean}

${SUBDIRS}:
	${MAKE} -C $@

${SUBDIRS:=-clean}:
	${MAKE} -C ${@:-clean=} clean

${SUBDIRS:=-distclean}:
	${MAKE} -C ${@:-distclean=} distclean
