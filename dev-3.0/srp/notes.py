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



@utils.tracedmethod("srp.notes")
def init(file_p, rev=None):
    """create notes instance(s). we will attempt to use the latest and
    greatest, but fall back to the older deprecated class as a last resort
    """
    # try v3
    try:
        retval_p = v3(file_p)
        return retval_p
    except Exception, e:
        tried.append("v3 (%s)" % e)

    # try v2 translated to v3
    try:
        x = v2_wrapper(file_p, rev)
        to_add = x.create_v3_files()
        retval_p = v3(to_add[config.NOTES])
        # get translated notes file and install script added to archive?
        for name, f in to_add.items():
            tinfo = tar_p.gettarinfo(fileobj=f)
            tinfo.name = name
            tar_p.addfile(tinfo(f), f)

    except Exception, e:
        tried.append("v2 (%s)" % e)

    if retval_p == None:
        err = "Failed to create NOTES instace(s): %s" % ", ".join(tried)
        raise Exception(err)
    return retval_p


def foo():
    retval_p = None
    tried = []
    to_try = [v3, v2]
    for x in to_try:
        try:
            retval_p = x(file_p)
            break
        except Exception, e:
            tried.append("%s (%s)" % (x, e))
    if retval_p == None:
        err = "Failed to create NOTES instace(s): %s" % ", ".join(tried)
        raise Exception(err)
    return retval_p


class v2_wrapper(utils.base_obj):
    def __init__(self, file_p, rev="99"):
        """this wrapper class shouldn't be used, except to initalize a basic
        v2 notes file to translate into a v3 instance
        """
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
        
        self.i_script = "export SRP_ROOT='" + config.RUCKUS + "/tmp' && \n"

        if self.flags != "SRP_NONE":
            self.i_script += "export CFLAGS=" + self.flags + " && \nexport CXXFLAGS=" + self.flags + " && \n"

        # the rest of the file is i_script
        buf = "".join(file_p.readlines()).rstrip()
        self.i_script += utils.compat_unescaper(buf)
        

    def create_v3_files(self):
        """returns a map of fobjs? (notes_p, script_p, etc)
        """
        retval = {}
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
        retval[config.NOTES] = x

        # we have to create the 'go' script and get it added to the archive...
        x = tempfile.NamedTemporaryFile(mode="w+")
        x.write("%s\n" % self.i_script)
        x.seek(0)
        retval[script] = x

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


class v2(empty):
    def __init__(self, file_p):
        super(self.__class__, self).__init__()
        
        # maybe we should say we're backwards compatible with the
        # following caveats:
        #  1. NOTES-2 file must have not been using all the prefix munging
        #     options.
        #  2. PREPOSTLIB methods must not have been using their arguments
        #  3. version is dirname.split(name-)[-1].
        #  4. revision is going to be set to 99
        
        
        # use old v2 method(s) to create a v2-ish notes instance

        # translate it into a v3 notes instance


    def __icky(self):

        # unfortunately, to do this with the smallest headache (which is what
        # we want, since this is all backwards compatibility stuff), we have to
        # extract a few files to the disk...  to maintain the illusion of not
        # writing to disk, we'll only write the files we really need and we'll
        # write them in /tmp by setting SRP_ROOT_PREFIX to /tmp/something

        # first, create our /tmp/something directory
        tmpdir = tempfile.mkdtemp(prefix="srp-")
        # now that we created that tmpdir, we have to make sure we delete it
        # before exiting
        try:
            # fudge deprecated.sr variables
            try:
                old_prefix = os.environ["SRP_ROOT_PREFIX"]
            except:
                old_prefix = ""
            os.environ["SRP_ROOT_PREFIX"] = tmpdir
            reload(deprecated.sr)
            print("fudged deprecated.sr.SRP_ROOT_PREFIX: %s" %
                  deprecated.sr.SRP_ROOT_PREFIX)

            # make sure the necessary ruckus directories exist.
            for x in deprecated.sr.ruckus_dirs:
                dir = os.path.join(deprecated.sr.RUCKUS, x)
                print("making: %s" % dir)
                os.makedirs(dir)

            target_dir = os.path.join(deprecated.sr.RUCKUS, "package")
            
            to_extract = [deprecated.sr.NOTES2,
                          deprecated.sr.PREPOSTLIB2,
                          deprecated.sr.OWNEROVERRIDE2]
            
            # extract any files that are available.  the only critical failure
            # is the NOTES file.
            for x in to_extract:
                try:
                    file_p = package_p.extractfile(x)
                    target_file = os.path.join(target_dir, x)
                    target_file_p = open(target_file, 'w')
                    print("extracting: %s --> %s" % (x, target_file))
                    shutil.copyfileobj(file_p, target_file_p)
                except Exception, e:
                    if x == deprecated.sr.NOTES2:
                        err = "Failed to extract NOTES file '%s': %s" % (x, e)
                        raise Exception(err)
                    else:
                        # anything else is optional
                        pass

            # now use deprecated.sr_package2 
            p = deprecated.sr_package2.package()
            p._read_notes()
            
        finally:
            # clean up tmpdir
            shutil.rmtree(tmpdir)
            # revert the fudged variables in deprecated.sr
            os.environ["SRP_ROOT_PREFIX"] = old_prefix
            reload(deprecated.sr)

        # now map everything into a compatible object
        self.__notes_version = "2"
        self.__name = p.name
        self.__sourcefilename = p.filename
        self.__description = p.description
        self.__flags = p.srp_flags
        self.__script = p.i_script #<--- needs to be a filename only
        self.__prepostlib = p.prepost #<--- needs to be a filename only
        self.__owneroverride = p.ownerinfo #<--- needs to be a filename only
        self.__ldpath = p.ldpath

        # keep the old package instance around for now...
        self.p = p


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

            # create an prepostlib instance full of empty (or default)
            # functions if a library wasn't provided by the package.
            #if not self.__prepostlib_p:
            #    self.__prepostlib_p = prepostlib.v3(package_p)
        except Exception, e:
            err = "Failed to parse NOTES file '%s': %s" % (file_p.name, e)
            raise Exception(err)

        # double check the notes_version
        if self.notes_version != "3":
            raise VersionMismatchError

        # create next instance, if using SRP_CHAIN
        #print "before:", dir(self)
        #if self.__chain:
        #    print "right here:", self.__chain
        #    try:
        #        self.__next_p = v3(package_p, self.__chain)
        #    except Exception, e:
        #        err = "Failed to instantiate next NOTES object in chain"
        #        err += ": %s" % e
        #        raise Exception(err)


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
