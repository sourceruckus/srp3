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
import utils


# exported objects
__all__ = ["srp", "brp"]


class srp(utils.base_obj):
    """Version 3 package object
    """
    
    def __init__(self, filename):
        """Create a Version 3 package instance
        """
        self.filename = filename
        
        # create TarFile instance of filename
        try:
            self.__tar_p = tarfile.open(filename, 'r')
        except Exception, e:
            err = "Failed to create TarFile instance: %s" % e
            raise Exception(err)

        self.__notes_p = notes.init(self)
        
        # DEBUG: display all notes objects in chain
        n = self.__notes_p
        while n:
            n.info()
            n = n.next_p
    

    # ---------- API stuff ----------
    def extractfile(self, member):
        retval = None
        try:
            retval = self.__tar_p.extractfile(member)
        except:
            # try ./ version
            retval = self.__tar_p.extractfile(os.path.join('.', member))
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
