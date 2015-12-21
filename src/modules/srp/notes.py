"""The SRP NOTES file.
"""

import srp

import collections
import configparser
import re
import base64
import tarfile
import tempfile
import types
import os
import pwd
import socket
import time

# FIXME: we should implement a v2->v3 translator here.  it should translate
#        the following variables in the build script:
#
#        $SRP_ROOT/../package -> $EXTRA_DIR
#
#        $SRP_ROOT -> PAYLOAD_DIR
#
#        it should also issue warnings about removed features in v3 (e.g.,
#        PREPOSTLIB, CHAIN).
#

# NOTE: This is a bit hairy because bufferfixer expects a str and returns a
#       str, but the base64 methods operates on bytes...

def encodescript(m):
    return "encoded = True\nbuffer = {}".format(base64.b64encode(m.group(1).encode()).decode())

def bufferencode(buf):
    return re.sub("^%%BUFFER_BEGIN%%\n(.*?)\n%%BUFFER_END%%\n", encodescript, buf, flags=re.DOTALL|re.MULTILINE)

def cmp_version(a, b):
    if a[0] > b[0]:
        return 1
    if a[0] < b[0]:
        return -1
    if a[1] > b[1]:
        return 1
    if a[1] < b[1]:
        return -1
    if a[2] > b[2]:
        return 1
    if a[2] < b[2]:
        return -1
    return 0


class NotesHeader:
    def __init__(self, config, path=""):
        self.name = config["name"]
        self.version = config["version"]
        self.pkg_rev = config["pkg_rev"]

        # add formatted fullname
        self.fullname = "{}-{}-{}".format(self.name, self.version, self.pkg_rev)

        # strip carriage returns out of this potentially multi-line item
        self.description = config["description"].replace("\n", " ")

        # prepend path segments to each element in this list
        self.extra_content = []
        try:
            for x in config["extra_content"].split():
                self.extra_content.append(os.path.join(path, x))
        except:
            pass

        # if any segments of srp_min_version aren't defined, fallback to the
        # version being used to create the package.
        try:
            self.srp_min_version_major = int(config["srp_min_version_major"])
            self.srp_min_version_minor = int(config["srp_min_version_minor"])
            self.srp_min_version_micro = int(config["srp_min_version_micro"])

        except:
            self.srp_min_version_major = srp.config.version_major
            self.srp_min_version_minor = srp.config.version_minor
            self.srp_min_version_micro = srp.config.version_micro

        self.srp_min_version = "{}.{}.{}".format(
            self.srp_min_version_major,
            self.srp_min_version_minor,
            self.srp_min_version_micro)

        try:
            self.features = config["features"].split()
        except:
            self.features = []

        # populate features with our defaults
        f = srp.features.default_features[:]

        # parse features from NOTES file
        #
        # NOTE: We ONLY want to tweak features if this NOTES file hasn't
        #       already been run through srp (i.e., it's not coming from a
        #       brp archive)
        #
        # NOTE: That's ok, we won't ever be constructing NOTES again after
        #       package creation because we're going to store a pickled
        #       instance from there on out.
        for x in self.features:
            if x.startswith("no_"):
                # handle feature disabling
                try:
                    f.remove(x[3:])
                except:
                    pass

            # NOTE: We add the "no_*" entries along with the enabler flags
            #       so we can keep track of what's been explicitly disabled
            #       as apposed to simply not enambed somewhere along the
            #       line.
            f.append(x)

        # overwrite the raw value with the parsed list
        self.features = f


class NotesBuffer:
    def __init__(self, config, path=""):
        try:
            self.encoded = config["encoded"]
            # FIXME: why not leave this as bytes?  i really need to get a
            #        better handle on the rationale for bytes vs string...
            self.buffer = base64.b64decode(config["buffer"].encode()).decode()
        except:
            self.encoded = False
            self.buffer = config["buffer"]


class NotesScript(NotesBuffer):
    pass


class NotesBrp:
    def __init__(self):
        # FIXME: should have a .srprc file to specify a full name (e.g.,
        #        'Joe Bloe <bloe@mail.com>'), and fallback to user id if
        #        it's not set
        self.build_user = pwd.getpwuid(os.getuid()).pw_gecos

        # FIXME: this should probably be a bit more complicated...
        self.build_host = socket.gethostname()

        # FIXME: should i store seconds since epoch, struct_time, or a human
        #        readable string here...?
        self.build_date = time.asctime()

        # Number of seconds it took to build the whole package
        #
        # NOTE: Set to current time here, and is subtracted from current
        #       time when we're done at the very end of package creation.
        #
        self.time_total = time.time()


class NotesInstalled():
    def __init__(self, from_sha):
        self.install_date = time.asctime()
        self.installed_from_sha = from_sha


class NotesFile:
    """Class representing a NOTES file.

    NOTE: fobj must be opened in binary mode

    NOTE: We implement sub-classes in here to handle each section of the file.
    """
    def __init__(self, fobj, src, extradir=None, copysrc=False):
        # check for open mode
        #
        # NOTE: We do this here so that we can assume the file has been
        #       opened in binary mode from here on out.  We chose to force
        #       binary (as apposed to text) mode simply because that's what
        #       you get when you extractfile from tarfile.
        #
        # NOTE: We can't just check fobj.mode, because file-like-objects
        #       returned from tarfile.extractfile have mode of 'r' (at least
        #       w/ v3.2.2), but read returns bytes (as apposed to str).
        if type(fobj.read(0)) != bytes:
            raise Exception("{}(fobj): fobj must be opened in binary mode".format(self.__class__.__name__))

        if not extradir:
            extradir = os.path.dirname(fobj.name)

        # NOTE: We pass the actual buffer read from file through buffencode,
        #       which encodes specified sections and allows the configparser to
        #       parse things w/out having heartburn about embedded scripts,
        #       multi-line options, etc
        buf = bufferencode(fobj.read().decode())
        c = configparser.ConfigParser(comment_prefixes=('#'),
                                      inline_comment_prefixes=('#'))
        c.read_string(buf)

        # populate sub-section instances
        self.header = NotesHeader(c["header"], extradir)
        self.script = NotesScript(c["script"], extradir)
        self.brp = None
        self.installed = None

        # add cli-specified header fields
        self.header.src = os.path.abspath(src)
        self.header.copysrc = copysrc

        # add features for unclaimed sections
        #
        # NOTE: This will automatically enable any feature that has a
        #       special section defined for it in the NOTES file (e.g.,
        #       perms).  However, it means that every unclaimed section
        #       is assumed to be a valid feature name.
        for s in c.keys():
            if s not in ["header", "script", "brp", "installed", "DEFAULT"]:
                self.header.features.append(s)
                # instantiate special feature subsections
                setattr(self, s,
                        globals()["Notes"+s.capitalize()](c[s], extradir))

        # check package requirements
        self.check()


    # FIXME: do i really want to do this?  look at __str__ vs __repr__
    def __str__(self):
        ret = ""
        ret += repr(self) + "\n"
        for x in dir(self):
            s = getattr(self, x)
            if x.startswith("_") or type(s) == types.MethodType:
                continue

            ret += x + ": " + repr(s) + "\n"
            if not s:
                continue
            keys = list(s.__dict__.keys())
            keys.sort()
            for k in keys:
                if k == "buffer" and getattr(s, "encoded", False):
                    ret += "-- <buffer> --------\n{}\n-- </buffer> -------\n".format(getattr(s, "buffer"))
                else:
                    ret += "{}.{}: ".format(s.__class__.__name__, k) + str(getattr(s, k)) + "\n"
        return ret.strip()


    def check(self):
        # check for required version
        #
        # NOTE: This check does not include devtag (i.e., 3.0.0-alpha1 ==
        #       3.0.0)
        if cmp_version([srp.config.version_major,
                        srp.config.version_minor,
                        srp.config.version_micro],
                       [self.header.srp_min_version_major,
                        self.header.srp_min_version_minor,
                        self.header.srp_min_version_micro]) < 0:
            raise Exception("package requires srp >= " +
                            self.header.srp_min_version)

        # check for required features
        missing = self.header.features[:]
        # prune all disablers
        for x in self.header.features:
            if x.startswith("no_"):
                missing.remove(x)
        # prune all registered features
        for x in srp.features.registered_features:
            try:
                missing.remove(x)
            except:
                pass
        if missing:
            err="package requires missing features: {}".format(missing)
            raise Exception(err)

        # check for needed files (source tree, patches, etc)
        flist = []
        # source dir/tarball
        flist.append(self.header.src)
        # extra content
        flist.extend(self.header.extra_content)

        print(os.getcwd())
        print(flist)
        for fname in flist:
            # fname may be a file or a dir, so we just check for existence
            if not os.path.exists(fname):
                raise Exception("missing required file/dir: " + fname)



    # used to update features on the command line
    def update_features(self, options):
        for o in options:
            if o in self.header.features:
                # already there
                continue

            if o.startswith("no_"):
                try:
                    self.header.features.remove(o[3:])
                except:
                    # wasn't enabled to begin with
                    pass

            self.header.features.append(o)
