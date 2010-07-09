"""
This module defines classes responsible for doing work (ie, building,
installing etc).
"""

import os
import os.path
import shutil
import subprocess
import tarfile
import tempfile

import config
import package
import utils


class builder(utils.base_obj):
    """builder object
    """

    def __init__(self):
        """
        Create a builder object.  This object can be used to build
        binary packages from source packages.
        """
        self.__p = None
        self.__n = None
        self.__b_list = []


    def build(self, package_p, commit=True):
        """
        Build all the binary packages detailed in the specified source
        package.  Returns a list of binary packages.
        """
        self.__p = package_p
        # first, extract archive into RUCKUS/build
        try:
            self.__p.extractall()
            self.__n = self.__p.notes_p
            while self.__n:
                # build it
                lib = self.__n.prepostlib_p
                print "prebuild"
                print lib
                print lib.prebuild
                print dir(lib)
                lib.prebuild()
                print "build"
                self.__build_package()
                print "postbuild"
                lib.postbuild()
                print "wrap it up"
                self.__create_brp_members()
#                if commit:
#                    self.__commit()
                
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
        """
        run the contained build script to build the files to be
        installed by the binary package.  files to be packaged up end
        up installed in RUCKUS/tmp
        """
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
        """
        creates the necesary objects needed to instantiate a binary
        package, instantiates the package, and adds it to
        self.__b_list.
        """
        brp_id = tempfile.mkdtemp(prefix='brp-',
                                  dir=os.path.join(config.RUCKUS, "brp"))
        
        blob_p, files_p = self.__create_blob_and_files(brp_id)
        notes_p = self.__n

        self.__b_list.append(package.binary(None,
                                            notes_p,
                                            files_p,
                                            blob_p))


    def __create_blob_and_files(self, brp_id):
        """
        creates blob and files objects for a binary package.  this
        archives all the files in RUCKUS/tmp, records extra file
        metadata (checksums, owner overrides, etc), removes the files
        in RUCKUS/tmp, and returns blob and files objects.
        """
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
            files.sort()
            print files
            for f in files:
                n = os.path.join(node, f)
                i = blob_p.gettarinfo(n)
                print i

                # owneroverride_p and files_p are indexes by absolute pathname
                # of the file (w/out SRP_ROOT_PREFIX)
                abs_n = n[1:]
                
                # forge target user/group ownership per OWNEROVERRIDE
                for rule in self.__n.owneroverride_p[abs_n]:
                    # apply the rule

                    # uh, how exactly?  am i guaranteed that each
                    # supported rule will have a key?  or do i have to
                    # put a bunch of try blocks in here...?

                    # look for a __override_KEY method for each key value?
                    for key, value in rule['options'].items():
                        try:
                            f = eval("__override_%s" % key)
                        except:
                            print "WARNING: invalid override option specified: %s" % key
                        try:
                            f(value, i)
                        except Exception, e:
                            print "WARNING: override method '%s' failed: %s: %s" % (key, value, e)

                    # uh, this will only work for files.  we have to
                    # also be able to override metadata for
                    # directories.  we can specify a non-recursive
                    # rule for a dir in the override file, but we'll
                    # never check to see if a dir matches it because
                    # we only iterate over files here... directory
                    # creation/storage in tarfiles is transparent,
                    # right?
                    #
                    # actually, it looks like dirs _can_ have an entry
                    # in a tarfile... but they don't _need_ to?
                    # either way, they show up with a full set of
                    # metadata (although size is 0), so maybe this
                    # method should be looping over files _and_ dirs?
                    #
                    # it already is... we extend files list with dirs.
                    # never mind.  this will work just fine.  ;-)

                        
                #if abs_n in self.__n.owneroverride_p:
                #    uname, gname = self.__n.owneroverride_p[abs_n].split(":")
                #    print "OWNEROVERRIDE: uname=%s, gname=%s" % (uname, gname)
                #    i.uname = uname
                #    i.gname = gname
                #    # at install time, uname and gname will be resolved to uid
                #    # and gid, respectively.  if either is unresolvable, the
                #    # installing user's info will be used.
                
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



class installer(utils.base_obj):
    """installer object
    """

    def __init__(self):
        """
        Create an installer object.  This object can be used to
        install, upgrade, or uninstall a package.
        """
        self.__p = None


    def install(self, package_p):
        """
        install the provided binary package object
        """
        self.__p = package_p
        try:
            self.__p.prepost.preinstall()
            self.__check_deps()
            self.__install_files()
            self.__p.prepost.postinstall()
            self.__commit()
        finally:
            self.__p = None


    def upgrade(self, package_p):
        """
        upgrade the provided binary package object
        """
        self.__p = package_p


    def uninstall(self, package_p):
        """
        uninstall the provided installed package object
        """
        self.__p = package_p
