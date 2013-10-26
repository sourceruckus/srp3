if !DIST_ONLY

dist_doc_DATA =
dist_doc_DATA += docs1
dist_doc_DATA += docs2
dist_doc_DATA += docs3

install-data-hook:
	$(RM) -f $(DESTDIR)$(docdir)/foo
	(cd $(DESTDIR)$(docdir) && $(LN_S) .. foo)

endif
