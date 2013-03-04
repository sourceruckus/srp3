"""The SRP NOTES file.
"""

import srp

import collections
import configparser
import re
import base64
import tempfile

# FIXME: we should implement a v2->v3 translator here.  it should translate
#        the following variables in the build script:
#
#        SRP_ROOT/../package -> PACKAGE_DIR
#
#        SRP_ROOT -> PAYLOAD_DIR
#
#        it should also issue warnings about SRP_ROOT being deprecated.
#

# NOTE: This is a bit hairy because bufferfixer expects a str and returns a
#       str, but the base64 methods operates on bytes...

def encodescript(m):
    return "encoded = True\nbuf = {}".format(base64.b64encode(m.group(1).encode()).decode())

def bufferencode(buf):
    return re.sub("^%%BUFFER_BEGIN%%\n(.*?)\n%%BUFFER_END%%\n", encodescript, buf, flags=re.DOTALL|re.MULTILINE)


class notes:
    """Class representing a NOTES file.  This class is designed very
    intentionally to do as much as possible dynamically based on what's actually
    in the NOTES file being parsed.

    NOTE: fobj must be opened in binary mode
    """
    def __init__(self, fobj):
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

        self.filename = fobj.name
        # NOTE: We pass the actual buffer read from file through buffencode,
        #       which encodes specified sections and allows the configparser to
        #       parse things w/out having heartburn about embedded scripts,
        #       multi-line options, etc
        buf = bufferencode(fobj.read().decode())
        c = configparser.ConfigParser(comment_prefixes=('#'),
                                      inline_comment_prefixes=('#'))
        c.read_string(buf)
        
        # now dynamically assign attributes based on what configparser sees
        #
        # NOTE: This means we can access things as notes.info.version as apposed
        #       to keeping the config parser around and getting at things via
        #       notes.config['info']['version']
        #
        # NOTE: This isn't just for aesthetics.  It should be faster and
        #       less memory intensive to use this struct-ish data model than
        #       keeping the config parser around and accessing things
        #       through it directly all the time.  And we can type the
        #       values (e.g., notes.prereqs.version_major is an int, but
        #       notes.config['prereqs']['version_major'] is a string
        self.sections = {}
        for s in c.keys():
            if s == "DEFAULT":
                continue
            self.sections[s] = []
            setattr(self, s, collections.namedtuple(s, c[s].keys()))
            for k in c[s].keys():
                setattr(getattr(self, s), k, c[s][k])
                self.sections[s].append(k)
            if getattr(getattr(self, s), "encoded", False):
                getattr(self, s).buf = base64.b64decode(getattr(self, s).buf.encode()).decode()

        # and now do some re-typing (for standard items)
        self.prereqs.version = ".".join([self.prereqs.version_major,
                                         self.prereqs.version_minor,
                                         self.prereqs.version_bugfix])
        self.prereqs.version_major = int(self.prereqs.version_major)
        self.prereqs.version_minor = int(self.prereqs.version_minor)
        self.prereqs.version_bugfix = int(self.prereqs.version_bugfix)

        # prepopulate features with our defaults
        f = srp.features.default_features[:]

        # parse features from NOTES file
        #
        # NOTE: We ONLY want to tweak features if this NOTES file hasn't
        #       already been run through srp (i.e., it's not coming from a
        #       brp archive)
        if 'brp' not in self.sections:
            for x in self.options.features.split():
                if x.startswith("no_"):
                    # handle feature disabling
                    try:
                        f.remove(x[3:])
                    except:
                        pass
                else:
                    # handle enables
                    f.append(x)

            # add features for unclaimed sections
            #
            # NOTE: This will automatically enable any feature that has a
            #       special section defined for it in the NOTES file (e.g.,
            #       perms).  However, it means that every unclaimed section
            #       is assumed to be a valid feature name.
            for s in self.sections:
                if s not in ['prereqs', 'info', 'options', 'script', 'brp']:
                    f.append(s)

            # overwrite the raw value with the parsed list
            #
            # NOTE: We flatten this back out into a string to make life
            #       easier later on when we write via ConfigParser
            self.options.features = " ".join(f)

        self.additions = {}

        # check package requirements
        self.check()


    def __str__(self):
        ret = ""
        for s in self.sections:
            for k in self.sections[s]:
                if getattr(getattr(self, s), "encoded", False) and k == "buf":
                    ret += "-- <buffer> --------\n{}\n-- </buffer> -------\n".format(getattr(getattr(self, s), k))
                else:
                    ret += "[{}] {} = {}\n".format(s, k, getattr(getattr(self, s), k))
        for s in self.additions:
            for k in self.additions[s]:
                ret += "[{}] {} = {}\n".format(s, k, self.additions[s][k])
        return ret.strip()


    def write(self, fobj):
        # we accomplish this by re-populating a new configparser instance
        # with all our data (namedtuples and items from self.additions),
        # then have the configparser write to a file object
        c = configparser.ConfigParser()

        # our namedtuple data originally read from the NOTES file
        for s in self.sections:
            c[s] = {}
            for k in self.sections[s]:
                if getattr(getattr(self, s), "encoded", False) and k == "buf":
                    c[s][k] = base64.b64encode(getattr(getattr(self, s), k).encode()).decode()
                else:
                    c[s][k] = str(getattr(getattr(self, s), k))

        # now add items from self.additions
        for s in self.additions:
            c[s] = {}
            for k in self.additions[s]:
                c[s][k] = self.additions[s][k]

        # fix fobj mode
        #
        # NOTE: ConfigParser.write requires a fobj that was opened in txt
        #       mode, but everywhere else we (or other python objects) are
        #       forcing binary mode.  I'm working around this by writing
        #       config to a temp txt file, then read/writing into the passed
        #       in binary mode fobj.
        #
        # FIXME: max_size should be common w/ all our other
        #        SpooledTemporaryFile instances.
        with tempfile.SpooledTemporaryFile(mode="w+") as wtf:
            c.write(wtf)
            wtf.seek(0)
            fobj.write(wtf.read().encode())


    def check(self):
        # check for required version
        if srp.config.version_major < self.prereqs.version_major:
            raise Exception("package requires srp >= {}".format(self.prereqs.version))
        elif srp.config.version_minor < self.prereqs.version_minor:
            raise Exception("package requires srp >= {}".format(self.prereqs.version))
        elif srp.config.version_bugfix < self.prereqs.version_bugfix:
            raise Exception("package requires srp >= {}".format(self.prereqs.version))

        # check for required features
        missing = self.options.features.split()
        #print(missing)
        #print(srp.features.registered_features)
        for x in srp.features.registered_features:
            try:
                missing.remove(x)
            except:
                pass
        if missing:
            raise Exception("package requires missing features: {}".format(missing))
