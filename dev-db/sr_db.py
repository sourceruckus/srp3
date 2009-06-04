"""sr_db -
srp plaintext filesystem database
"""

import os
import os.path

import sr
import utils


class db:
    """db
    this class is essentially a hash table of applications.
    """
    
    def __init__(self):
        self.path = "%s/installed" % sr.RUCKUS
        self.apps = []
        nodes = os.listdir(self.path)
        nodes.sort()
        for x in nodes:
            if os.path.isdir(x):
                self.apps.append(application("%s/%s" % (self.path, x)))
            else:
                self.apps.append(compat_log(x))

    def __str__(self):
        retval = ""
        for x in self.apps:
            if retval != "":
                retval += "\n"
            retval += str(x)
        return retval


class application:
    """application
    this class defines the toplevel view of an installed application.  each
    application consists of one or more installed versions.
    """
    
    def __init__(self, path):
        self.path = path
        self.versions = []
        nodes = os.listdir(self.path)
        nodes.sort()
        for x in nodes:
            self.versions.append(version("%s/%s" % (self.path, x)))

    def __str__(self):
        retval = ""
        for x in self.versions:
            if retval != "":
                retval += "\n"
            retval += str(x)
        return retval


class version:
    """version
    this class defines one version of an installed application.  it contains
    all the necesary data for maintaining the application.
      - REV
      - NOTES
      - PREPOSTLIB
      - DEPS_LIB
      - DEPS_PROG
      - DEPS_SRP
      - FILES
    """

    def __init__(self, path):
        self.path = path
        self.REV = rev(path)
        self.NOTES = notes(path)
        self.PREPOSTLIB = prepostlib(path)
        self.DEPS_LIB = deps_lib(path)
        self.DEPS_PROG = deps_prog(path)
        self.DEPS_SRP = deps_srp(path)
        self.FILES = files(path)

    def __str__(self):
        retval = os.path.basename(os.path.dirname(self.path)).ljust(20)
        retval += ("src: %s" % os.path.basename(self.path)).ljust(40)
        retval += "rev: %s" % self.REV
        return retval


class sr_file:
    """sr_file
    this class is responsible for file read/write ops
    """

    def __init__(self, name):
        self.name = name
        self.lines = []
        if os.path.isfile(name):
            x = file(self.name)
            #self.lines = x.readlines()
            line = "foo"
            while line != "":
                line = x.readline()
                self.lines.append(line.rstrip())
            x.close()
            del self.lines[-1]


class rev(sr_file):
    """rev
    this file contains the package's rev number
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, "REV-2"))

    def __str__(self):
        return self.lines[0]


class notes(sr_file):
    """notes
    this file contains all the data needed to compile/install a package
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, sr.NOTES2))


class prepostlib(sr_file):
    """prepostlib
    this file contains pre/post-install routines
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, sr.PREPOSTLIB2))


class deps_lib(sr_file):
    """deps_lib
    this file contains library dependencies
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, sr.DEPS_LIB2))


class deps_prog(sr_file):
    """deps_prog
    this file contains program dependencies
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, sr.DEPS_PROG2))


class deps_srp(sr_file):
    """deps_srp
    this file contains srp dependencies
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, sr.DEPS_SRP2))


class files(sr_file):
    """files
    this file contains a list of installed files
    """
    
    def __init__(self, path):
        sr_file.__init__(self, "%s/%s" % (path, sr.FILES2))




class compat_log:
    """compat_log
    this class is for backwards compatability with the old logfile format
    """

    def __init__(self, path):
        
