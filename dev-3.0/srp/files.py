"""srp.files -
This module defines classes representing the FILES file in a BRP.  The FILES
file acts as cached archive metadata, allowing us to querry files at the end
of the tarfile archive without having to sequentially parse through all the
preceding files.
"""

import os
import os.path
import sha
import tarfile

import config
import utils


class v3(utils.base_obj, dict):
    # this will be a dict of fileinfo objects
    def __init__(self, blob_p, notes_p):
        dict.__init__(self)
        
        for x in blob_p:
            # calculate checksum, if configured
            if "SRP_CHECKSUM" in notes_p.flags:
                # use files still in RUCKUS/tmp
                #x.checksum = utils.checksum(os.path.join(config.RUCKUS,
                #                                         "tmp",
                #                                         x.name))
                print x.name
                print x.type
                print os.listdir(os.path.join(config.RUCKUS, "tmp"))
                print x.isfile()
                print x.isreg()
                print x.isdir()
                print x.issym()
                print x.islnk()
                f = blob_p.extractfile(x.name)
                print f
                if f:
                    x.checksum = sha.new(f.read()).hexdigest()
                    print x.checksum

            # create owneroverride, if configureed
            if "SRP_OWNEROVERRIDE" in notes_p.flags:
                x.owneroverride = ""
                # if an override was specified, store it here
                
            # now add x to our dict
            self[x.name] = x
