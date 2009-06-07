"""\
This module defines classes for representing the different types of
packages.  Each supported major version of srp (v1, v2, v3, etc) should have
an class defined here to wrap the old classes into the API needed by the
current implementation of builder/installer/etc.  Said API is as follows:

--- API stuff ---
extractfile()
notes_p (prepostlib_p, owneroverride_p, etc, are in here)
filename




builder needs:
  notes.description
  notes.flags
  notes.name
  notes.next_p
  notes.notes_version
  notes.owneroverride_p
  notes.prepostlib_p.__prepost__
  notes.script
  notes.sourcefilename

installer needs:
  blob_p
  files_p
  notes_p (w/ chain stripped)
  
"""


import cPickle
import new
import os.path
import tarfile

import config
import notes
import owneroverride
import prepostlib
import utils


# exported objects
__all__ = ["srp", "brp"]


class srp(utils.base_obj):
    """Version 3 package object
    """
    
    def __init__(self, filename, dirname=None):
        """Create a Version 3 package instance.  The filename argument refers
        to the name of a source package.  If dirname is not provided,
        it's assumed that filename refers to a previously committed
        source package.  If dirname is provided, it's assumed that the
        directory contains all the files necessary to create a source
        package (the source tarball search path is actually .:..).  A
        created source package is not written to disk until commit()
        is called.
        """
        self.__filename = filename
        
        if not dirname:
            self.__load_package_from_disc()
        else:
            self.__create_package(dirname)
        
        # create TarFile instance of filename
        try:
            self.__tar_p = tarfile.open(filename, 'r')
        except Exception, e:
            err = "Failed to create TarFile instance: %s" % e
            raise Exception(err)

        # create initial notes instance.  we do this by having
        # notes_p be empty with its chain set to the toplevel NOTES
        # file.  then we just loop until notes_p.chain is empty.
        self.__notes_p = notes.empty()
        self.__notes_p.chain = config.NOTES

        n = self.__notes_p
        not_done = True
        while not_done:
            try:
                if n.chain:
                    n.next_p = notes.init(self.extractfile(n.chain))
                else:
                    not_done = False
                
                # no need to bother with extra object instantiation if
                # chain is our default toplevel NOTES file...
                if n.chain == config.NOTES:
                    n = n.next_p
                    continue

                # prepostlib
                if n.prepostlib:
                    n.prepostlib_p = self.extractfile(n.prepostlib)
                    n.prepostlib_p = prepostlib.init(n.prepostlib_p)
                else:
                    # create a prepostlib instance full of empty (or
                    # default) functions if a library wasn't provided
                    # by the package.
                    n.prepostlib_p = prepostlib.init(None)
                    
                # owneroverride
                if n.owneroverride:
                    n.owneroverride_p = self.extractfile(n.owneroverride)
                    n.owneroverride_p = owneroverride.init(n.owneroverride_p)
                else:
                    # create an empty owneroverride so we can assume
                    # one is available later on
                    n.owneroverride_p = owneroverride.init(None)

                n = n.next_p

            except Exception, e:
                msg = "Failed to instantiate notes object: %s" % e
                raise Exception("ERROR: %s" % msg)
                
        
        # for convenience, let's remove the empty head node
        self.__notes_p = self.__notes_p.next_p

        # DEBUG: display all notes objects in chain
        #n = self.__notes_p
        #while n:
        #    n.info()
        #    n = n.next_p
    

    # ---------- API stuff ----------
    def extractfile(self, member):
        retval = None
        try:
            retval = self.__tar_p.extractfile(member)
        except:
            try:
                # try ./ version
                retval = self.__tar_p.extractfile(os.path.join('.', member))
            except:
                msg = "Failed to extract file '%s'" % member
                msg += " from %s" % self.filename
                raise Exception(msg)
        return retval


    @utils.ruckuswritemethod
    def extractall(self):
        # this will get us ready to build (extract srp, and sourcetarball)
        self.__tar_p.extractall(os.path.join(config.RUCKUS, "package"))
        temptar = os.path.join(config.RUCKUS, "package", self.__notes_p.sourcefilename)
        print "temptar:", temptar
        temptar = tarfile.open(temptar)
        temptar.extractall(os.path.join(config.RUCKUS, "build"))


#    def get_script_name(self):
#        return self.__notes_p.script
    
#    def get_prepostlib(self):
#        return self.__notes_p.prepostlib_p.__prepost__

#    def create_blob(self):
#        # __init__ should parse through the files ONCE, creating tar entries,
#        # files entries (forged according to owneroverrides), and deps in one
#        # fell swoop
#        self.__blob_p = blob.v3()

    def extract_blob(self):
        self.__blob_p.extract()

    def generate_deps(self):
        pass

    def get_deps(self):
        pass

    def version(self):
        return self.__notes_p.notes_version




class brp(utils.base_obj):
    def __init__(self, notes_p, files_p, tar_p=None):
        self.__notes_p = notes_p
        self.__files_p = files_p
        if tar_p:
            self.__tar_p = tar_p
        else:
            self.openblob()

    def openblob(self):
        self.__tar_p = tarfile.open(config.BLOB, config.BLOB_COMPRESSION)
        
    def pickle(self):
        #name = "%s-%s-%s.%s.brp" % (self.__notes_p.name,
        #                            self.__notes_p.version,
        #                            self.__notes_p.revision,
        #                            utils.platform_id())
        self.__tar_p = None
        retval = cPickle.dumps(self, -1)
        self.openblob()
        return retval
