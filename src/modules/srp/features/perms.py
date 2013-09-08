"""Feature module for specifying permissions.

This feature allows package maintainers to override file permissions resulting
from the build script via the NOTES file (as apposed to putting chmod/chown
statements in the script).

NOTE: This is the only appropriate way to set file ownership.  Using chown in
      the NOTES file's build script will not work if a package is built as
      non-root.
"""

import srp.notes
from srp.features import *

import os
import re
import tarfile


class notes_perms(srp.notes.notes_buffer):
    pass

# NOTE: We need to stick our notes section definition class in the notes
#       module's namespace so that it can be located dynamically in the
#       notes_file constructor.
#
# FIXME: Need to document this requirement somewhere more obvious...  By the
#        way, this is ONLY needed because we expect stuff for this feature
#        to be parsed from the initial notes file (i.e., if we only add
#        things during build it's not needed).
srp.notes.notes_perms = notes_perms


class perms(list):
    """ This class defines a special list that initializes itself from a
    decoded perms buffer.  It provides a [] method that returns a list of
    rules that match the specified file (via regexp).

    file_regex:user=,group=,mode=,mode_set=,mode_unset=,...recursive=true

    If file_regex is a directory and 'recursive' option is specified,
    recursively apply all settings.

    Instead of just setting mode, mode_set and mode_unset are availibe as
    well.  So

    /var/named:user=named,group=named,mode_set=384,mode_unset=63,recursive=true

    will set all files under /var/named (including /var/named) to
    named:named, set S_IRUSR|S_IWUSR, and unset S_IRWXG|S_IRWXO.

    NOTE: This is implemented as a list, not a map, so we can ensure that
          rules are applied in the order they're defined...  We won't ever
          be indexing into a specific key anway, since we allow regex for
          key.
    """
    def __init__(self, buf):
        list.__init__(self)

        lines = buf.split('\n')
        
        for line in lines:
            # remove comments
            line = line.split("#")[0].strip()
            if not line:
                continue

            # split on : but keep in mind that regex can have ':' in
            # it.
            line = line.split(":")
            options = line[-1]
            pattern = ":".join(line[:-1])

            # split options on ,
            options = options.split(",")

            # create options dict
            options_dict = {}
            for x in options:
                k, v = x.split("=")
                options_dict[k] = v

            # make sure our flag options exist with default values
            for flag, value in [('recursive', 'false')]:
                try:
                    # this will lowercase-ize the flag value if it was
                    # specified so we don't have to check multiple
                    # cases later on
                    options_dict[flag] = options_dict[flag].lower()
                except:
                    options_dict[flag] = value

            self.append({'regex': re.compile(pattern), 'options': options_dict})


    def __getitem__(self, fname):
        """
        unlike most __getitem__ methods, this one returns a list of
        items instead of a single item.  as such, it returns [] if
        there are no matching items istead of raising an exception.

        NOTE: if passed an int, the list.__getitem__ method is called
              to allow for simple indexing.
        """
        # if we're simply trying to index into the list, call the list
        # method to do so
        if isinstance(fname, int):
            return list.__getitem__(self, fname)

        retval = []
        for x in self:
            if x['options']['recursive'] != "false":
                # we have to try matching on fname and each of it's parent dirs
                sep = os.path.sep
                y = fname.split(sep)
                for i in range(len(y)):
                    subname = sep.join(y[:len(y)-i])
                    if not subname:
                        continue
                    if x['regex'].search(subname):
                        retval.append(x)
                        break

            elif x['regex'].search(fname):
                retval.append(x)

        return retval


# NOTE: We want this to be done at build time... At build time, we could
#       update the TarInfo object prior to adding the file to the archive.
#       If we do it at install time, we'll have to extract and then change
#       perms afterwards.
#
# NOTE: The core build_func does NOT actually add files to the brp, it just
#       runs the build script and make a first pass at the package manifest.
#       This gives us a chance to swoop in here and change perms in the
#       TarInfo objects in work['tinfo'] prior to the toplevel program
#       finalizing the brp (at which point, files are actually added to the
#       BLOB archive).
#
# NOTE: There's no interdependency with user feature here because we can
#       forge the TarInfo with whatever we like.  The system doesn't
#       actually try to use the ownership info until install time.
#
# FIXME: I think the above is true, but TarInfo has a uid and uname
#        field.... what if they don't match up?  are they both required?
def build_func(work, fname):
    """update tarinfo via perms section of NOTES file"""
    #print(work.keys())
    #print(work['notes'].perms.buf)
    n = work["notes"]
    p = perms(n.perms.buffer)
    #print(p)
    #print(p['/usr/local/bin/foo'])
    #print(p['/usr/share/asdf'])

    x = work["manifest"][fname]["tinfo"]
    #print(x)

    # skip links
    #
    # NOTE: I was going to also skip hard links here, but the behavior of GNU
    #       Tar is that the 1st file linked to an inode gets added as a regular
    #       file and all subsequent files get added as hard links... and the
    #       order the files are visited by tar's recursive algo isn't entirely
    #       clear.  For example, my example package creates a file foo, a
    #       symlink to it called bar, and a hard link to it called baz, but
    #       tarring that up with GNU Tar results in foo.islnk() == True and
    #       baz.islnk() == False.  Not what I expected...  anyhoo, we'll not
    #       skip hard links then so that package maintainers don't have to
    #       worry about this bit of arbitrariness.
    #
    # FIXME: Wait, do we need to support chowning symlinks here?
    if x.issym():
        return

    # special treatment for hard links
    #
    # NOTE: Ok, if the file we're acting on is a hard link, we're going to
    #       follow the link and act on the real file.  This is needed so that
    #       package maintainers don't need to worry about which file gets added
    #       first when writing perms rules.
    if x.islnk():
        x = work["manifest"]["/"+x.linkname]["tinfo"]
        #print(x)

    # return if there's no perms matching this file
    #
    # NOTE: We need to use fname here instead of x.name because leading slashes
    #       are pruned off of the TarInfo objects
    if not p[fname]:
        return

    for rule in p[fname]:
        #print("rule:", rule)

        if 'user' in rule['options']:
            try:
                x.uid = int(rule['options']['user'])
            except:
                x.uname = rule['options']['user']

        if 'group' in rule['options']:
            try:
                x.gid = int(rule['options']['group'])
            except:
                x.gname = rule['options']['group']

        if 'mode' in rule['options']:
            x.mode = int(rule['options']['mode'], 8)

        if 'mode_set' in rule['options']:
            x.mode = x.mode | int(rule['options']['mode_set'], 8)

        if 'mode_unset' in rule['options']:
            x.mode = x.mode & ~int(rule['options']['mode_unset'], 8)

    # update global data
    #
    # NOTE: We use x.name instead of fname here because we need to make sure we
    #       update the right TarInfo instance and we may have followed a link
    #       to a new file's TarInfo.
    work["manifest"]["/"+x.name]["tinfo"] = x



def verify_func():
    """check perms, issue warning"""
    # FIXME: MULTI:
    pass

register_feature(
    feature_struct("perms",
                   __doc__,
                   build_iter = stage_struct("perms", build_func, [], []),
                   action = [("verify",
                              stage_struct("perms", verify_func, [], []))]))
