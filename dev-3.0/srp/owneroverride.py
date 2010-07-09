"""owneroverride
"""

import os
import random
import re
import tempfile
import types

import config
import utils

# old format was just a file of '/path/to/file:uid:gid' lines.
# uid/gid could be by name or actual id as long as the names exist
# prior to installing the package (which turne out to be almost
# never).
#
# assuming we have SRP_USERADD=name,id and SRP_GROUPADD=name,id flags,
# we should be able to use user/group names that we're going to
# install after the files are installed...
#
# file_regex:user=,group=,mode=,mode_set=,mode_unset,selinux_user=,selinux_role=,selinux_type=,...recursive=true
#
# if file_regex is a directory and 'recursive' option is specified,
# recursively apply all settings
#
# instead of just setting mode, we will now support mode, mode_or, and
# mode_and which will staticly set mode, or (set) mode bits, or
# (unset) in mode bits, respectively.
#
# /var/named:user=named,group=named,mode_set=384,mode_unset=63,recursive=true
#
# will set all files under /var/named (including /var/named) to
# named:named, set S_IRUSR|S_IWUSR, and unset S_IRWXG|S_IRWXO.
#
# this is accomplished internally like this:
# os.chmod(filename, os.stat(filename)[stat.ST_MODE] | mode_set)
# os.chmod(filename, os.stat(filename)[stat.ST_MODE] & ~mode_unset)
#
# NOTE: if we accept regexp in here, do we have to wait to the end to
#       apply the modes?  we currently check for a single key in
#       owneroverride during build, and forge metadata in the tarfile
#       if something is specified.
#
# NOTE: yeah, it'll work.  we'll just have to check each key in the
#       map for regexp that would match each given file...
#
# NOTE: should i actually do the file modifications in the builder?
#       or do them via owneroverride member functions?
#
# NOTE: i probably want this to be a list, not a map, so i can ensure
#       that rules are applied in the order they're defined...  we
#       won't ever be indexing into a specific key anway, since we
#       allow regex for key.


class v2_wrapper(utils.base_obj):
    def __init__(self, file_p):
        """this wrapper class shouldn't be used except to initialize a basic
        v2 owneroverride file to translate into a v3 instance
        """
        if file_p:
            file_p.seek(0)
            self.name = file_p.name
            self.lines = file_p.read().split('\n')
        else:
            self.name = "OWNEROVERRIDE-%s" % "".join(random.sample(chars, 5))
            self.lines = []

            
    def create_v3_files(self):
        """returns a list of name, fobj paris
        """
        retval = []

        # old file format was: /installed/file:uid:gid
        new_lines = []
        for line in self.lines:
            key, user, group = line.split(":")
            options = {"user": user,
                       "group": group}
            
            new_lines.append("%s:user=%s,goup=%s" % key, user, group)

        x = tempfile.NamedTemporaryFile(mode="w+")
        x.write("\n".join(new_lines))
        x.seek(0)
        name = os.path.basename(self.name)
        retval.append([name, x])

        return retval



class v3(utils.base_obj, list):
    def __init__(self, file_p):
        list.__init__(self)

        if not file_p:
            return

        file_p.seek(0)
        lines = file_p.read().split('\n')
        
        for line in lines:
            # remove comments
            line = line.split("#")[0].strip()
            if not line:
                continue
            #print "line: '%s'" % line
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
        if type(fname) == types.IntType:
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
