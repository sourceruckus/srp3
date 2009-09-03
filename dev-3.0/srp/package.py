"""\
This module defines classes for representing the different types of
packages.
"""


import cPickle
import os.path
import shutil
import tarfile
import tempfile

import config
import deprecated
import notes
import owneroverride
import prepostlib
import utils


# exported objects
__all__ = ["srp", "brp"]


class srp(utils.base_obj):
    """Version 3 package object
    """
    
    def __init__(self, filename=None, dirname=None):
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
        self.__dirname = dirname
        self.__sourcefilename = None
        self.__old_filename = None

        if self.__dirname:
            # we're populating using directory of files
            self.extractfile = self.extractfile_dir
            self.addfile = self.addfile_dir
        else:
            # we're populating using committed package
            self.extractfile = self.extractfile_file
            self.addfile = self.addfile_file

        # create initial notes instance.  we do this by having
        # notes_p be empty with its chain set to the toplevel NOTES
        # file.  then we just loop until notes_p.chain is empty.
        self.__notes_p = notes.empty()
        self.__notes_p.chain = config.NOTES

        # NOTE: in order for this to be backwards compatible with srp2
        #       pacakges, we'll have to check for both config.NOTES
        #       and deprecated.sr.NOTES2
        try:
            self.extractfile(config.NOTES)
            
        except:
            # if config.NOTES isn't in the archive, then this must be
            # a v2 package.  time to do some translation...
            # package revision?
            try:
                if filename:
                    rev = filename.split('-')[-1].rstrip(".srp")
                elif os.path.exists(os.path.join(dirname, "REV")):
                    # REV file?
                    f = self.extractfile("REV")
                    rev = f.read().split('\n')[0].strip()
                    f.close()
                else:
                    rev = "1"
            except:
                rev = "999"

            # initialize the v2 notes file
            f = self.extractfile(deprecated.sr.NOTES2)
            x = notes.v2_wrapper(f, rev)
            f.close()
            to_add = x.create_v3_files()

            # get translated notes file and install script added to
            # archive.  pkg.addfile does NOT modify the original package
            # archive on disk
            for name, f in to_add:
                print "adding '%s' to archive..." % name
                self.addfile(name=name, fobj=f)
                print "added"

        n = self.__notes_p
        not_done = True
        while not_done:
            #n.info()
            try:
                if n.chain:
                    n.next_p = notes.v3(self.extractfile(n.chain))
                else:
                    not_done = False
                
                # no need to bother with extra object instantiation if
                # chain is our default toplevel NOTES file...
                if n.chain in [config.NOTES, deprecated.sr.NOTES2]:
                    n = n.next_p
                    continue

                # prepostlib
                if n.prepostlib:
                    n.prepostlib_p = prepostlib.init(
                        self.extractfile(n.prepostlib))
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

                # before we move on, let's verify that the sourcefile
                # is available.  the search path for sourcefile is .:..
                f = None
                searchpath=[".", ".."]
                for d in searchpath:
                    try:
                        fname = os.path.join(d, n.sourcefilename)
                        f = self.extractfile(fname)
                        if not self.__sourcefilename:
                            self.__sourcefilename = fname
                        break
                    except:
                        pass
                if f:
                    f.close()
                else:
                    msg = "Failed to locate sourcefile '%s'" % n.sourcefilename
                    raise Exception(msg)

                n = n.next_p

            except Exception, e:
                msg = "Failed to instantiate notes object: %s" % e
                raise Exception("ERROR: %s" % msg)
                
        # for convenience, let's remove the empty head node
        self.__notes_p = self.__notes_p.next_p


    def __del__(self):
        # delete our temporary archive
        if self.__old_filename:
            os.remove(self.__filename)


    def commit(self):
        """writes package to disk.  if package already exists, it is only
        replaced if the new package would be different.
        """
        # make sure this isn't silly
        if not self.__dirname:
            raise Exception("can't commit package that wasn't created by us")

        # what should my name be?
        self.__filename = "%s-%s-%s.srp" % (self.__notes_p.name,
                                            self.__notes_p.version,
                                            self.__notes_p.revision)
        needs_update = False

        # let's try to open existing file so we can check for content
        # differences as we go along.  to be clear, we care about the
        # actual data, not the order it appears in the archive.
        # (files, perms, timestamps, etc)
        try:
            old_one = tarfile.open(self.__filename, "r")
        except:
            #print "needs_update: no old one"
            needs_update = True

        # now let's create a temporary file to store our new archive
        # in.  if differences are noticed while creating it, it will
        # be renamed to replace the old package file.  this also means
        # that source package creation/update is fully atomic.
        tmpfile = tempfile.NamedTemporaryFile(mode="w")
        new_one = tarfile.open(name=tmpfile.name, fileobj=tmpfile, mode="w")
        
        # populate new_one, checking to see if any of the files we're
        # adding are different or missing from old_one
        #print "adding files to new_one..."
        to_add = os.listdir(self.__dirname)
        to_add.append(self.__sourcefilename)
        for fname in to_add:
            # add the file
            #print "adding:", fname
            new_one.add(name=os.path.join(self.__dirname, fname),
                        arcname=os.path.basename(fname))

            # now check for presence/differences in old_one (no need
            # to do the check if we already know we need to update the
            # file...)
            if needs_update:
                continue

            try:
                x = old_one.getmember(os.path.basename(fname)).tobuf()
                y = new_one.getmember(os.path.basename(fname)).tobuf()
                if x != y:
                    #print "needs_update: updated file: %s" % fname
                    #print x
                    #print y
                    needs_update = True
            except:
                #print "needs_update: new file: %s" % fname
                needs_update = True
                old_one.close()

        # we're still not sure if the archives are the same.  iterate
        # over old_one to see if it contains any files that new_one
        # doesn't.
        if not needs_update:
            for x in old_one.getmembers():
                try:
                    new_one.getmember(x.name)
                except:
                    #print "needs_update: removed file: %s" % fname
                    needs_update = True
                    old_one.close()
                    break
        
        new_one.close()

        print "package needs update: %s" % needs_update
        if needs_update:
            f = open(self.__filename, "w")
            tmpfile.seek(0)
            f.write(tmpfile.read())
            f.close()

        tmpfile.close()


    # ---------- API stuff ----------
    def extractfile_dir(self, name):
        """
        extact a file from an "archive" when we're creating an archive
        from a directory of files.
        """
        olddir = os.getcwd()
        try:
            os.chdir(self.__dirname)
            retval = open(name)
        finally:
            os.chdir(olddir)
        return retval


    def extractfile_file(self, name):
        """
        extract a file from a previously created archive
        """
        retval = None
        
        # create TarFile instance of filename
        try:
            tar_p = tarfile.open(self.__filename, 'r')
        except Exception, e:
            err = "Failed to create TarFile instance: %s" % e
            raise Exception(err)
        
        # try to extract "name"
        try:
            retval = tar_p.extractfile(name)
        except:
            # try to extract "./name"
            try:
                retval = tar_p.extractfile(os.path.join('.', name))
            except:
                msg = "Failed to extract file '%s'" % name
                msg += " from %s" % self.__filename
                raise Exception(msg)

        # NOTE: hmm... if i extract a file, then close the tar
        # instance, the file obj gets closed... which isn't what i
        # want.  but if i leave the tar instance open indefinately, is
        # that a bad thing?
        #finally:
        #    tar_p.close()
        
        return retval


    def addfile_dir(self, name=None, fobj=None):
        """
        adds a file to the archive, when the archive is actually a
        directory of files.
        """
        # NOTE: do we really want this?  when would a file ever added
        # to the "archive" when we're running using a directory of
        # files not yet wrapped up and commited as an srp file...?
        raise Excepion("AHA!  We *do* need a package.addfile_dir method!")


    def addfile_file(self, name=None, fobj=None):
        """
        adds a file to the archive.  actually, this creates a new
        archive in /tmp and changes our __filename reference to point
        there.  parsing a package file shouldn't cause the package on
        disk to change (unless we very explicitly tell it to)
        """
        # first off, if we're running with self.__dirname, we don't
        # have an archive...
        if self.__dirname:
            f = open(os.path.join(self.__dirname, name), "w")
            f.write(fobj.read())
            f.close()
            fobj.seek(0)
            return

        if not self.__old_filename:
            # create a temporary file
            fd, tmpfile = tempfile.mkstemp()
            os.close(fd)

            # make it a copy of __filename
            shutil.copy(self.__filename, tmpfile)

            # repoint __filename at the new temporary archive
            self.__old_filename = self.__filename
            self.__filename = tmpfile

        # create TarFile instance of filename
        try:
            tar_p = tarfile.open(self.__filename, 'a')
        except Exception, e:
            err = "Failed to create TarFile instance: %s" % e
            raise Exception(err)
        
        # try to get tarinfo of file
        try:
            tinfo = tar_p.gettarinfo(name=name, fileobj=fobj)
            tinfo.name = name
            tar_p.addfile(tinfo, fobj)
        except Exception, e:
            err = "Failed to add file: %s" % e
            raise Exception(e)
        finally:
            tar_p.close()


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
    def __init__(self, filename=None, srp=None):
        self.__filename = filename
        self.__srp = srp

#    def __init__(self, notes_p, files_p, tar_p=None):
#        self.__notes_p = notes_p
#        self.__files_p = files_p
#        if tar_p:
#            self.__tar_p = tar_p
#        else:
#            self.openblob()

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
