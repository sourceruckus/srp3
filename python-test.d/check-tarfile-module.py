#!/usr/local/bin/python

# NOTE: this was taken mostly verbatim from the attachment to bug #1609958 on
#       Python's SourceForge Bug Tracker page.


import tarfile

import sys
import os
import tempfile

print "Python Version:", sys.version
print "Executable:", sys.executable
print "Tarfile Version: ", tarfile.version

myscript = sys.argv[0]

dummyfile = myscript

def run_pathlength_test(posix=True, maxlen=256):
    loops = (maxlen - len("fooo")) / len("tmp/") ## defauls to 63
    
    for i in range(int(loops)): 
        dir = "tmp/" * i
        arcname =  dir + "fooo" 
        try:
            tar_fd, tar_name = tempfile.mkstemp(prefix="check-tarfile-module-")
            tar = tarfile.open(tar_name, "w:gz", os.fdopen(tar_fd, "wb"))
            tar.posix = posix
            tar.debug = 0 # set 3 for debug output
            tar.add(myscript, arcname)
            tar.close()
            
            ## reopen the tarfile, this way the tarfile-member list
            ## will be reinitialized, restoring the file-name from
            ## tarinfo.prefix and tarinfo.name, otherwise tarfile.getnames()
            ## returns invalid filename-list
            
            tar = tarfile.open(tar_name, "r")
            if arcname not in tar.getnames():
                raise Exception("arcname not in tar.getnames()")

            ## check getmember() operation, might throw exception
            tar.getmember (arcname)
            tar.close()

        except Exception,e:
            msg = "TarFile pathlength check failed"
            msg += ": (arcname=%s, length=%d, posix=%s)" % (arcname,
                                                            len(arcname),
                                                            str(posix))
            msg += ": %s" %  str(e)
            raise Exception(msg)

        finally:
            # remove the file
            os.remove(tar_name)

    print "Tarfile module (posix=%s) is Ok" % posix        

try:
    run_pathlength_test(posix=True, maxlen=256)
    run_pathlength_test(posix=False, maxlen=1024)
except Exception, e:
    print "ERROR: %s" % e
    sys.exit(-1)
sys.exit(0)
