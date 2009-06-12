"""\
This module defines classes for representing the different types of
packages.
"""


import cPickle
import os.path
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
        self.__tar_p = None
        self.__sourcefilename = None

        olddir = os.getcwd()
        
        if self.__dirname:
            # we're populating using directory of files
            extract = open
        else:
            # we're populating using committed package
            extract = self.extractfile

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
        print self.__notes_p
        self.__notes_p.chain = config.NOTES
        # NOTE: in order for this to be backwards compatible with srp2
        #       pacakges, we'll have to check for both config.NOTES
        #       and deprecated.sr.NOTES2
        try:
            os.chdir(dirname)
            extract(config.NOTES)
            
        except:
            # just checking to see if config.NOTES can be extracted
            # without throwing an exception...
            self.__notes_p.chain = deprecated.sr.NOTES2
            # translation of v2 NOTES files is going to require a few
            # extra args... unfortunately
            extra_notes_args = {}
            # package revision?
            try:
                if filename
                    rev = filename.split('-')[-1].rstrip(".srp")
                elif os.path.exists(os.path.join(dirname, "REV")):
                    # REV file?
                    f = open(os.path.join(dirname, "REV"))
                    rev = f.read().split('\n')[0].strip()
                else:
                    rev = "1"
            except:
                rev = "999"
            extra_notes_args["rev"] = rev

        finally:
            os.chdir(olddir)

        n = self.__notes_p
        not_done = True
        while not_done:
            try:
                if dirname:
                    os.chdir(dirname)
                
                if n.chain:
                    n.next_p = notes.init(extract(n.chain), *extra_notes_args)
                else:
                    not_done = False
                
                # no need to bother with extra object instantiation if
                # chain is our default toplevel NOTES file...
                if n.chain == config.NOTES:
                    n = n.next_p
                    continue

                # prepostlib
                if n.prepostlib:
                    n.prepostlib_p = prepostlib.init(extract(n.prepostlib))
                else:
                    # create a prepostlib instance full of empty (or
                    # default) functions if a library wasn't provided
                    # by the package.
                    n.prepostlib_p = prepostlib.init(None)
                    
                # owneroverride
                if n.owneroverride:
                    n.owneroverride_p = extract(n.owneroverride)
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
                        f = extract(fname)
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
                
            finally:
                os.chdir(olddir)

        # for convenience, let's remove the empty head node
        self.__notes_p = self.__notes_p.next_p

        
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
            print "needs_update: no old one"
            needs_update = True

        # now let's create a temporary file to store our new archive
        # in.  if differences are noticed while creating it, it will
        # be renamed to replace the old package file.  this also means
        # that source package creation/update is fully atomic.
        tmpfile = tempfile.NamedTemporaryFile(mode="w")
        new_one = tarfile.open(name=tmpfile.name, fileobj=tmpfile, mode="w")
        
        # populate new_one, checking to see if any of the files we're
        # adding are different or missing from old_one
        print "adding files to new_one..."
        to_add = os.listdir(self.__dirname)
        to_add.append(self.__sourcefilename)
        for fname in to_add:
            # add the file
            print "adding:", fname
            new_one.add(name=os.path.join(self.__dirname, fname),
                        arcname=os.path.basename(fname))

            # now check for presence/differences in old_one (no need
            # to do the check if we already know we need to update the
            # file...)
            if needs_update:
                continue

            try:
                #print old_one
                #print old_one.list(verbose=True)
                #x = os.path.basename(fname)
                #print x
                #x = old_one.getmember(x)
                #print x
                x = old_one.getmember(os.path.basename(fname)).tobuf()
                #print x
                y = new_one.getmember(os.path.basename(fname)).tobuf()
                #print y
                if x != y:
                    print "needs_update: updated file: %s" % fname
                    print x
                    print y
                    needs_update = True
            except:
                print "needs_update: new file: %s" % fname
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
                    print "needs_update: removed file: %s" % fname
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
                msg += " from %s" % self.__filename
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
