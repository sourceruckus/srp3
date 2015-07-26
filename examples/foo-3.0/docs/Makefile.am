if !DIST_ONLY

dist_doc_DATA =
dist_doc_DATA += docs1
dist_doc_DATA += docs2
dist_doc_DATA += docs3

install-data-hook:
	$(RM) -f $(DESTDIR)$(docdir)/foo
	(cd $(DESTDIR)$(docdir) && $(LN_S) .. foo)

else

# Automake notices that we have registered documentation to install (even
# though it's in a conditional), and ensures the creation of docdir
# regardless.  We really don't want to create a docdir when we've
# configured for just making dist.
install-data-hook:
	rmdir $(DESTDIR)$(docdir)
endif
