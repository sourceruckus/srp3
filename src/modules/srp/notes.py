"""The SRP NOTES file.
"""

import srp

import collections
import configparser
import re
import base64

def encodescript(m):
    return "encoded = True\nbuf = {}".format(base64.b64encode(m.group(1).encode()).decode())

def bufferfixer(buf):
    return re.sub("^%%BUFFER_BEGIN%%\n(.*?)\n%%BUFFER_END%%\n", encodescript, buf, flags=re.DOTALL|re.MULTILINE)


class notes:
    """Class representing a NOTES file.  This class is designed very
    intentionally to do as much as possible dynamically based on what's actually
    in the NOTES file being parsed.
    """
    def __init__(self, fobj):
        # NOTE: We pass the actual buffer read from file through bufferfixer,
        #       which encodes specified sections and allows the configparser to
        #       parse things w/out having heartburn about embedded scripts,
        #       multi-line options, etc
        buf = bufferfixer(fobj.read())
        c = configparser.ConfigParser(comment_prefixes=('#'),
                                      inline_comment_prefixes=('#'))
        c.read_string(buf)
        
        # now dynamically assign attributes based on what configparser sees
        #
        # NOTE: This means we can access things as notes.info.version as apposed
        #       to keeping the config parser around and getting at things via
        #       notes.config['info']['version']
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
        # NOTE: This will automatically enable any feature that has a special
        #       section defined for it in the NOTES file (e.g., perms).
        #       However, it means that every unclaimed section is assumed to be
        #       a valid feature name.
        for s in self.sections:
            if s not in ['prereqs', 'info', 'options', 'script']:
                f.append(s)
        
        # overwrite the raw value with the parsed list
        self.options.features = f


    def __str__(self):
        ret = ""
        for s in self.sections:
            for k in self.sections[s]:
                if getattr(getattr(self, s), "encoded", False) and k == "buf":
                    ret += "-- <buffer> --------\n{}\n-- </buffer> -------\n".format(getattr(getattr(self, s), k))
                else:
                    ret += "[{}] {} = {}\n".format(s, k, getattr(getattr(self, s), k))
        return ret.strip()
