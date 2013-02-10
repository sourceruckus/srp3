"""Feature module for specifying permissions.

This feature allows package maintainers to override file permissions resulting
from the build script via the NOTES file (as apposed to putting chmod/chown
statements in the script).

NOTE: This is the only appropriate way to set file ownership.  Using chown in
      the NOTES file's build script will not work if a package is built as
      non-root.
"""

from srp.features import *

# NOTE: We want this to be done at build time... At build time, we could
#       update the TarInfo object prior to adding the file to the archive.
#       If we do it at install time, we'll have to extract and then change
#       perms afterwards.
#
# FIXME: Hmmm... If we do this at build time, it has to come after
#        core... otherwise we haven't run the build script yet... but core
#        will have already added all the files to the archive... then what?
#
#        We could have core create a SpooledTempFile as the BLOB, then have
#        the perms build method readd each member to a new SpooledTempFile
#        w/ forged TarInfos, then only write the final one to disk?
#
# FIXME: Well, there's really no need to have core's build func actually create
#        the tar.  We could have core's build func just run the script and
#        populate the payload dir, but have some other final step create the
#        tarball.  We could even create a TarFile object and iterate over all
#        the files creating TarInfo objects, but not actually add any files to
#        the archive until the very very end...
#
# NOTE: There's no interdependency with user feature here because we can
#       forge the TarInfo with whatever we like.  The system doesn't
#       actually try to use the ownership info until install time.
#
# FIXME: I think the above is true, but TarInfo has a uid and uname
#        field.... what if they don't match up?  are they both required?
def build_func(work):
    """update tarinfo via perms section of NOTES file"""
    print(work)


def verify_func():
    """check perms, issue warning"""
    pass

register_feature(feature_struct("perms",
                                __doc__,
                                build = stage_struct("perms", build_func, ["core"], []),
                                action = [("verify", stage_struct("perms", verify_func, [], []))]))
