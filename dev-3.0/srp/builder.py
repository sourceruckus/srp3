"""srp.builder -
This module defines classes responsible for building packages.
"""

import os
import os.path
import shutil
import subprocess
import tarfile
import tempfile

import config
#import files
import package
import utils


class v3(utils.base_obj):
    def __init__(self):
        self.__p = None
        self.__n = None
        self.__b_list = []
    

    def build(self, package_p, commit=True):
        self.__p = package_p
        # first, extract archive into RUCKUS/build
        try:
            self.__p.extractall()
            self.__n = self.__p.notes_p
            while self.__n:
                # build it
                lib = self.__n.prepostlib_p
                lib.prebuild()
                self.__build_package()
                lib.postbuild()
                self.__create_brp_members()
                if commit:
                    self.__commit()
                
                # set us up to build the next one
                self.__n = self.__n.next_p

            return self.__b_list
        
        except Exception, e:
            err = "build failed: %s" % e
            raise Exception(err)
        finally:
            self.__p = None
            self.__n = None
            self.__b_list = []
            


    def __build_package(self):
        utils.vprint("building package: %s" % self.__p.filename)

        # things to export:
        #  SRP_ROOT=$RUCKUS/tmp
        #  SRP_PACKAGE_DIR=$RUCKUS/package
        #  SRP_BUILD_DIR=$RUCKUS/build/$DIRNAME
        #  SRP_INSTALL_SCRIPT=$SRP_PACKAGE_DIR/scriptname
        
        dirname = os.listdir(os.path.join(config.RUCKUS, "build"))
        utils.vprint("dirname: %s" % dirname)
        dirname = dirname[0]
        
        root = os.path.join(config.RUCKUS, "tmp")
        pdir = os.path.join(config.RUCKUS, "package")
        bdir = os.path.join(config.RUCKUS, "build", dirname)
        iscript = os.path.join(pdir, self.__n.script)
        
        # using the subprocess module (new in Python 2.4) takes care of
        # spawning subprocesses in a nice cross-platform manner.  the install
        # script in the package is probably system-dependant, though, unless
        # the package maintainer is _REALLY_ careful.
        env = os.environ.copy()
        env["SRP_ROOT"] = root
        env["SRP_PACKAGE_DIR"] = pdir
        env["SRP_BUILD_DIR"] = bdir
        env["SRP_INSTALL_SCRIPT"] = iscript

        utils.vprint("iscript: %s" % iscript)
        utils.vprint("env: %s" % env)
        
        sub = subprocess.Popen(iscript,
                               cwd = bdir,
                               env = env)

        status = sub.wait()
        if status != 0:
            raise Exception("ERROR: '%s' failed with retval: '%d'" % (iscript,
                                                                      status))
        


    def __create_brp_members(self):
        """NOTE: this addes the following members to the package instance:
                   - blob_p
                   - files_p
        """
        brp_id = tempfile.mkdtemp(prefix='brp-',
                                  dir=os.path.join(config.RUCKUS, "brp"))
        
        blob_p, files_p = self.__create_blob_p(brp_id)
        notes_p = self.__n

        self.__b_list.append(package.brp(None,
                                         notes_p,
                                         files_p,
                                         blob_p))


    def __create_blob_p(self, brp_id):
        utils.vprint("creating blob_p...")
        # create BLOB
        blob_name = os.path.join(brp_id, config.BLOB)
        blob_p = tarfile.open(blob_name, "w:%s" % config.BLOB_COMPRESSION)

        # use gnu extensions
        blob_p.posix = False

        # don't dereference symlinks
        blob_p.dereference = False

        # add all the files
        olddir = os.getcwd()
        os.chdir(os.path.join(config.RUCKUS, "tmp"))
        
        files_p = {}
        deps_p = {}
        
        for node, dirs, files in os.walk("."):
            files.extend(dirs)
            print files
            for f in files:
                n = os.path.join(node, f)
                i = blob_p.gettarinfo(n)
                print i

                # owneroverride_p and files_p are indexes by absolute pathname
                # of the file (w/out SRP_ROOT_PREFIX)
                abs_n = n[1:]
                
                # forge target user/group ownership per OWNEROVERRIDE
                if abs_n in self.__n.owneroverride_p:
                    uname, gname = self.__n.owneroverride_p[abs_n].split(":")
                    print "OWNEROVERRIDE: uname=%s, gname=%s" % (uname, gname)
                    i.uname = uname
                    i.gname = gname
                    # at install time, uname and gname will be resolved to uid
                    # and gid, respectively.  if either is unresolvable, the
                    # installing user's info will be used.
                
                # add file to archive
                if i.isreg():
                    f_obj = open(n, 'rb')
                else:
                    f_obj = None
                blob_p.addfile(i, f_obj)

                if i.isreg():
                    # create checksums, if configured
                    if utils.any_of_in(["SRP_MD5SUM",
                                        "SRP_SHA1SUM",
                                        "SRP_CHECKSUM"],
                                       self.__n.flags):
                        i.checksum = utils.checksum(n, f_obj)

                    # lookup shared library deps
                    i.deps_lib = utils.lookup_deps(n)
                        
                        
                # add tarinfo to files_p dict
                files_p[abs_n] = i
        
        
        # finalize the archive
        blob_p.close()

        # reopen in read-mode
        blob_p = tarfile.open(blob_name, "r:%s" % config.BLOB_COMPRESSION)

        # remove all the archived files
        for x in os.listdir("."):
            shutil.rmtree(x)

        # restore CWD
        os.chdir(olddir)

        return blob_p, files_p



