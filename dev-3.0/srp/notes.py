"""srp.notes -
This module defines classes representing the NOTES file in a package.
"""

import ConfigParser
import os
import os.path
import random
import shutil
import string
import sys
import tempfile

import config
import utils
import owneroverride
import prepostlib

import deprecated.sr
import deprecated.sr_package2


class VersionMismatchError(Exception):
    pass



class v2_wrapper(utils.base_obj):
    def __init__(self, file_p, rev="99"):
        """this wrapper class shouldn't be used, except to initalize a basic
        v2 notes file to translate into a v3 instance
        """
        self.file_p = file_p
        self.name = ""
        self.dirname = ""
        self.package_rev = rev
        self.logfile = ""
        self.srp_flags = []

        self.filename = ""
        self.description = ""
        self.flags = ""
        self.prefix = ""
        self.eprefix = ""
        self.bindir = ""
        self.sbindir = ""
        self.libexecdir = ""
        self.datadir = ""
        self.sysconfdir = ""
        self.sharedstatedir = ""
        self.localstatedir = ""
        self.libdir = ""
        self.includedir = ""
        self.oldincludedir = ""
        self.infodir = ""
        self.mandir = ""
        self.srcdir = ""
        self.otheropts = ""
        self.i_script = ""
        self.inplace = ""
        self.ldpath = []
        self.ownerinfo = {}
    
        self.name = file_p.readline().rstrip()
        self.filename = file_p.readline().rstrip()
        self.dirname = file_p.readline().rstrip()
        self.description = file_p.readline().rstrip()
        
        self.srp_flags = file_p.readline().rstrip().split('srp_flags = ')[-1].split()
        self.flags = file_p.readline().rstrip()
        self.prefix = file_p.readline().rstrip()
        self.eprefix = file_p.readline().rstrip()
        self.bindir = file_p.readline().rstrip()
        self.sbindir = file_p.readline().rstrip()
        self.libexecdir = file_p.readline().rstrip()
        self.datadir = file_p.readline().rstrip()
        self.sysconfdir = file_p.readline().rstrip()
        self.sharedstatedir = file_p.readline().rstrip()
        self.localstatedir = file_p.readline().rstrip()
        self.libdir = file_p.readline().rstrip()
        self.includedir = file_p.readline().rstrip()
        self.oldincludedir = file_p.readline().rstrip()
        self.infodir = file_p.readline().rstrip()
        self.mandir = file_p.readline().rstrip()
        self.srcdir = file_p.readline().rstrip()
        self.otheropts = file_p.readline().rstrip()

        self.prepostlib = None
        self.owneroverride = None

        # don't insert any extra code into i_script.  srp2 was doing
        # this at NOTES read-time, but srp3 will set up the
        # environment externally, then run the i_script.
        #self.i_script = "export SRP_ROOT='" + config.RUCKUS + "/tmp' && \n"
        #if self.flags != "SRP_NONE":
        #    self.i_script += "export CFLAGS=" + self.flags + " && \nexport CXXFLAGS=" + self.flags + " && \n"

        # have to tweak srp_flags a bit in here.  any v2 flags that
        # had default arguments should have the old default value
        # explicitly added.  can't assume the defaults are the same in
        # v3...
        for f in self.srp_flags[:]:
            # PREPOSTLIB
            if f.startswith("SRP_PREPOSTLIB"):
                if "=" not in f:
                    self.srp_flags.remove(f)
                    self.srp_flags.append("%s=%s" % (f, deprecated.sr.PREPOSTLIB2))
                    self.prepostlib = deprecated.sr.PREPOSTLIB2
                else:
                    self.prepostlib = f.split("=")[-1]
            # OWNEROVERRIDE
            if f.startswith("SRP_OWNEROVERRIDE"):
                if "=" not in f:
                    self.srp_flags.remove(f)
                    self.srp_flags.append("%s=%s" %
                                          (f, deprecated.sr.OWNEROVERRIDE2))
                    self.owneroverride = deprecated.sr.OWNEROVERRIDE2
                else:
                    self.owneroverride = f.split("=")[-1]

        # the rest of the file is i_script
        buf = "".join(file_p.readlines()).rstrip()
        self.i_script += utils.compat_unescaper(buf)
        

    def create_v3_files(self):
        """returns a list of name, fobj pairs
        """
        retval = []
        c = ConfigParser.RawConfigParser()

        #c.readfp(file_p)
        c.add_section("header")
        c.set("header", "version", "3")
        c.add_section("info")
        c.set("info", "name", self.name)
        c.set("info", "version", self.dirname.split("%s-" % self.name)[-1])
        c.set("info", "revision", self.package_rev)
        c.set("info", "sourcefilename", self.filename)
        c.set("info", "description", self.description)
        c.add_section("options")
        c.set("options", "flags", " ".join(self.srp_flags))
        chars = "%s%s" % (string.letters, string.digits)
        script = "go-%s" % "".join(random.sample(chars, 5))
        c.set("options", "script", script)

        x = tempfile.NamedTemporaryFile(mode="w+")
        c.write(x)
        x.seek(0)
        name = os.path.basename(self.file_p.name)
        if name == deprecated.sr.NOTES2:
            name = config.NOTES
        retval.append([name, x])

        # we have to create the 'go' script and get it added to the archive...
        x = tempfile.NamedTemporaryFile(mode="w+")
        x.write("%s\n" % self.i_script)
        x.seek(0)
        retval.append([script, x])

        # prepostlib?

        # owneroverride?

        # prepostlib and owneroverride will have to be handled by
        # package calling a v2_wrapper instance of each.  we can't do
        # it here because we don't have any means of accessing the
        # archive...

        return retval



class empty(utils.base_obj):
    def __init__(self):
        # initialize strings
        self.notes_version = ''
        self.name = ''
        self.version = ''
        self.revision = ''
        self.sourcefilename = ''
        self.description = ''
        self.script = ''
        self.prepostlib = ''
        self.owneroverride = ''
        self.ldpath = ''
        self.chain = ''

        # initialize objects
        self.prepostlib_p = None
        self.next_p = None
        self.owneroverride_p = None

        # initialize lists
        self.flags = []



class v3(empty):
    def __init__(self, file_p):
        super(self.__class__, self).__init__()
        
        c = ConfigParser.RawConfigParser()

        try:
            c.readfp(file_p)
            self.notes_version = c.get("header", "version")
            self.name = c.get("info", "name")
            self.version = c.get("info", "version")
            self.revision = c.get("info", "revision")
            self.sourcefilename = c.get("info", "sourcefilename")
            self.description = c.get("info", "description")
            self.flags = c.get("options", "flags").split()
            self.script = c.get("options", "script")

            self.__parse_flags()

        except Exception, e:
            err = "Failed to parse NOTES file '%s': %s" % (file_p.name, e)
            raise Exception(err)

        # double check the notes_version
        if self.notes_version != "3":
            raise VersionMismatchError


    def info2(self):
        print "--- notes.v3.info() ---"
        for x in dir(self):
            if x in self.__dict__:
                print "%s = %s" % (x, self.__dict__[x])
        print "-----------------------"

    
    def __parse_flags(self):
        utils.vprint("flags pre-parsing: %s" % (self.flags))
        
        # go through the flags, splitting on '=' to parse flag args
        for i in self.flags[:]:
            if "=" in i:
                flagarg = i.split("=")
                x = flagarg[0]
                y = flagarg[1]
                self.flags.remove(i)
                self.flags.append(x)
            else:
                x = i
                y = ""
            if x not in config.SUPPORTED_FLAGS:
                # we don't want to save flags we didn't use during the
                # install...
                utils.vprint("dropping unsupported srp_flag: " + x)
                self.flags.remove(x)
            elif y != "":
                # do something with the flag arg
                if x == "SRP_PREPOSTLIB":
                    utils.vprint("initializing self.prepostlib")
                    self.prepostlib = y

                elif x == "SRP_OWNEROVERRIDE":
                    utils.vprint("initializing self.owneroverride")
                    self.owneroverride = y
                    
                elif x == "SRP_INPLACE":
                    utils.vprint("initializing self.inplace")
                    self.inplace = os.path.join("/", config.SRP_ROOT_PREFIX, y)
                
                elif x == "SRP_LDCONFIG":
                    utils.vprint("initializing self.ldpath")
                    self.ldpath = y.split(',')

                elif x == "SRP_CHAIN":
                    utils.vprint("initializing self.chain")
                    self.chain = y
                    
        self.__add_default_flags()
        self.__override_default_flags()
        
        utils.vprint("flags post-parsing: %s" % (self.flags))


    def __add_default_flags(self):
        # add default_flags, if necessary
        for x in config.DEFAULT_FLAGS:
            if x not in self.flags:
                # special case for CHECKSUM variants
                if x == "SRP_CHECKSUM":
                    if "SRP_MD5SUM" in self.flags:
                        config.CHECKSUM = "md5"
                    elif "SRP_SHA1SUM" in self.flags:
                        config.CHECKSUM = "sha1"
                    else:
                        # no checksum algorithm was specified, use the default
                        x = "SRP_%sSUM" % (config.CHECKSUM.upper())

                self.flags.append(x)


    def __override_default_flags(self):
        # check for default overrides
        if "SRP_NO_UPGRADE" in self.flags:
            self.flags.remove("SRP_UPGRADABLE")
            self.flags.remove("SRP_NO_UPGRADE")

        if "SRP_NO_CHECKSUM" in self.flags:
            self.flags.remove("SRP_CHECKSUM")
            self.flags.remove("SRP_NO_CHECKSUM")

        if "SRP_NO_PERMS" in self.flags:
            self.flags.remove("SRP_PERMS")
            self.flags.remove("SRP_NO_PERMS")

        if "SRP_NO_LINKTARGET" in self.flags:
            self.flags.remove("SRP_LINKTARGET")
            self.flags.remove("SRP_NO_LINKTARGET")

        if "SRP_NO_INSTALLINFO" in self.flags:
            self.flags.remove("SRP_INSTALLINFO")
            self.flags.remove("SRP_NO_INSTALLINFO")

        if "SRP_NO_LDCONFIG" in self.flags:
            self.flags.remove("SRP_LDCONFIG")
            self.flags.remove("SRP_NO_LDCONFIG")
