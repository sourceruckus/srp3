"""The SRP BLOB file.
"""

import collections
import grp
import os
import pickle
import pprint
import pwd
import stat
import subprocess
import tarfile
import tempfile

import srp
import srp._blob

# On Disk Layout:
#
#   pickled manifest (map[filename]{tinfo, checksum, offset, ...})
#   DATA1
#   DATA2
#   ...
#
# The hopeful benefit of my new BLOB format is that all the metadata will be
# at the beginning, so we won't have to iterate through all the archive's
# data to get to the metadata for the last file.  I'm hoping this will allow
# for faster extraction compared to Python's TarFile implementation,
# hopefully also better via multiprocessing.
#
# UPDATE: This looks good!  Testing indicates that blob is faster (for our
#         usage) than tarfile, especially on older hardware.  We'll be
#         making it even faster by implementing bits of it in C down the
#         line...


# NOTE: We derive from SrpObject here even though all we get from it is
#       __str__, which we override.  This way, if we ever go back and add
#       more methods or data to SrpObject, this class will get it.
#
class Manifest(srp.SrpObject, collections.UserDict):
    """Class representing the contents of a BlobFile.  It can be iterated in
    sorted order, and has a special classmethod for populating itself with
    TarInfo objects of an entire filesystem tree.

    Although there's nothing to enforce it's contents, a propperly created
    Manifest object will be a dict of filenames, each of which is
    associated with a dict describing some aspect of the file.

    NOTE: This inherits from collections.UserDict instead of builtins.dict
          because deriving from dict and then adding a __dict__ resulted
          in an un-pickle-able mess.

    """
    def __init__(self):
        collections.UserDict.__init__(self)
        srp.SrpObject.__init__(self)
        self.sortedkeys = []
        self.payload_dir = None

    def __iter__(self):
        return iter(self.sortedkeys)

    # FIXME: this could possibly be faster if we iterate over ourself
    #        until the next item > the item to be inserted, then insert.
    #        i'm unsure of the benefit, though, because if we use
    #        list.sort() that's implemented in C, and if we try to insert
    #        alphabetically we'll be iterating in Python... i think...
    #
    def __setitem__(self, k, v):
        self.data[k] = v
        if k not in self.sortedkeys:
            self.sortedkeys.append(k)
            self.sortedkeys.sort()

    def __delitem__(self, k):
        del self.data[k]
        self.sortedkeys.remove(k)

    def __repr__(self):
        return "<{}.{} object>".format(self.__module__, self.__class__.__name__)

    def keys(self):
        return self.sortedkeys

    def __str__(self):
        """This __str__ method is special in that it scales its verbosity
        according to srp.params.verbosity.  A value of 0 or 1 results in
        output identical to __repr__(), 2 results in additionally
        including a few extra details, and 3 result in a dump of the
        entire dictionary.
        
        NOTE: The verbosity scaling is assuming that at 0, you're not
              printing anything, and at 1 you want basic info.  2 and up
              adds more and more until you drown in information.  ;-)

        """
        ret = repr(self)
        if srp.params.verbosity <= 1:
            return ret

        # slice off the trailing '>'
        ret = ret[:-1]
        ret += ", payload_dir={}".format(self.payload_dir)
        ret += ", size={}".format(len(self.sortedkeys))
        ret += ", sortedkeys={}".format(self.sortedkeys)
        ret += '>'

        if srp.params.verbosity <= 2:
            return ret

        ret += "\nManifest Contents:\n"
        ret += pprint.pformat(self.data)

        return ret

    @classmethod
    def fromdir(cls, payload_dir):
        """Returns a new Manifest object populated with entries for each file in
        the specified `payload_dir'.

        """
        obj = cls()
        obj.payload_dir = os.path.abspath(payload_dir)

        # NOTE: This tar object is just so we can use the gettarinfo
        #       member function
        tar = tarfile.open("tar", fileobj=tempfile.TemporaryFile(), mode="w")
        for root, dirs, files in os.walk(payload_dir):
            tmp = dirs[:]
            tmp.extend(files)
            # NOTE: sorting here adds a little processing overhead, but if
            #       we're going to keep these TarInfo objects around in a
            #       map and then try to actually add them to the BLOB
            #       later, we have to make sure that the order they get
            #       added matches the order in which the TarInfo's were
            #       created, otherwise we might add a hardlink before we
            #       add the file it's linked to, which will cause the
            #       extraction to fail during install
            #
            # FIXME: there's no point in sorting here... dict doesn't
            #        retain order.  We could use collections.OrderedDict,
            #        which retains insertion order, but that won't help if
            #        we want to insert alphabetically...
            #
            tmp.sort()
            for x in tmp:
                realname = os.path.join(root, x)
                arcname = os.path.join(root, x).split(payload_dir, 1)[-1]

                # NOTE: Sockets don't go in tarballs.  GNU Tar issues a
                #       warning, so we will too.  I don't know if there
                #       are other unsupported file types, but it looks
                #       like gettarinfo returns None if the file cannot be
                #       represented in a tarfile.
                x = tar.gettarinfo(realname, arcname)
                if not x:
                    print("WARNING: ignoring unsupported file type:", arcname)
                    continue

                # set ownership to root:root
                x.uid = 0
                x.gid = 0

                # remove problematic tarfile instance from TarInfo object
                #
                # NOTE: The tarfile instance inside the TarInfo instance
                #       cannot be pickled, so we have to remove it.  It
                #       doesn't seem to hurt anything.  TarInfo objects
                #       returned from TarFile.getmember() don't have this,
                #       but ones returned from TarFile.gettarinfo() do.
                del(x.tarfile)

                obj[arcname] = {"tinfo": x}

        return obj


# FIXME: if created via fobj, extract will not be functional... unless we
#        make it work later.  the c func takes a filename, so we would
#        have to make sure to know the path to the file on disk.
#
class BlobFile(srp.SrpObject):
    """Class representing a BLOB file.

    Data:

      fname - file name of the blob file on disk

      fobj - opened file object

      manifest - the Manifest object associated with the blob

      hdr_offset - size in bytes of the file's header (i.e., the pickled
          manifest).

    """
    def __init__(self):
        self.fname = None
        self.fobj = None
        self.manifest = None
        self.hdr_offset = None

    @classmethod
    def fromfile(cls, fname=None, fobj=None):
        """Creates a BlobFile object from either `fname' or `fobj'.
        """
        if not fname and not fobj:
            raise Exception("requires either fname or fobj")

        obj = BlobFile()
        obj.fname = fname

        if not fobj:
            obj.fobj = open(fname, "rb")
        else:
            obj.fobj = fobj

        obj.manifest = pickle.load(obj.fobj)
        obj.hdr_offset = obj.fobj.tell()

        # FIXME: Should I update each manifest offset entry to reflect
        #        hdr_offset?  Assuming that manifest gets pickled and
        #        restored prior to installation, this should make
        #        extraction a tad faster at the expense of a little extra
        #        work during build.  It would also allow us to pass a
        #        pre-created manifest into the constructor...

        return obj


    def tofile(self):
        """Creates a BLOB file on disk.  Either a `self.fname' for the resulting
        blob or a previously opened `self.fobj' must be supplied.

        """
        if not self.fname and not self.fobj:
            raise Exception("requires either fname or fobj")

        # create temporary file containing all the data from regular files
        # concatenated, while adding offset values to the manifest.
        tmp = tempfile.TemporaryFile()
        offset=0
        for x in self.manifest:
            tinfo = self.manifest[x]['tinfo']
            if not tinfo.isreg():
                continue
            with open(self.manifest.payload_dir+'/'+tinfo.name, 'rb') as f:
                tmp.write(f.read())
            self.manifest[x]['offset'] = offset
            offset += tinfo.size
        tmp.seek(0)
        tmp.flush()

        # now pickle the manifest
        #
        # FIXME: woah, i cannot pikcle.loads() the resulting string...
        #        what's going on?  I get the following traceback:
        #
        #   File "./srp/blob.py", line 65, in __setitem__
        #     self.sortedkeys.append(k)
        # AttributeError: 'Manifest' object has no attribute 'sortedkeys'
        #
        hdr = pickle.dumps(self.manifest)

        if self.fobj:
            f = self.fobj
        else:
            f = open(self.fname, "wb")

        f.write(hdr)
        f.write(tmp.read())

        # only close the file object if we opened it
        if not self.fobj:
            f.close()



    # FIXME: this needs to make backups of existing files.  i think we'll
    #        add the upgrade logic via an upgrade feature, but we need to
    #        at least make srpbak files here.
    def extract(self, fname, path=None, __c=True):
        """Extracts `fname' from the BLOB file to the current working directory.
        If `path' is specified, it is prepended to the resulting pathname.
        The C implementation is used if availalbe unless `__c' is set to
        False.

        """
        # get the TarInfo object
        x = self.manifest[fname]['tinfo']
        if srp.params.verbosity > 1:
            print("extracing", fname, "(tinfo:", x, ")")

        # decide on a full target pathname
        if path:
            target = os.path.join(path, x.name)
        else:
            target = x.name
        if srp.params.verbosity > 1:
            print("target:", target)

        # create leading path segments if needed
        #
        # NOTE: If we're being called via extractall, this won't be creating
        #       any directories stored in the blob because we iterate in
        #       sorted order.  However, if we're just randomly grabbing a
        #       single file, then we're going to be creating a bunch of
        #       directories here.
        try:
            os.makedirs(os.path.dirname(target))
        except:
            pass

        # delete file if already present
        #
        # FIXME: add srpbak support
        try:
            os.remove(target)
        except:
            pass

        # create target file
        #
        # NOTE: Regular files are the only ones with real data, everything
        #       else is just file creation w/ metadata
        if x.isreg():
            offset = self.hdr_offset + self.manifest[fname]["offset"]
            if srp.params.verbosity > 1:
                print("regular file: offset:", offset, "size:", x.size)
            if __c:
                srp._blob.extract(self.fname, target, offset, x.size)
            else:
                self.fobj.seek(offset)
                with open(target, "wb") as t_fobj:
                    t_fobj.write(self.fobj.read(x.size))

        elif x.isdir():
            if srp.params.verbosity > 1:
                print("directory")
            try:
                os.mkdir(target)
            except:
                # We'll get OSError if we've already created this dir
                # (e.g., as a leading path element to a file we've already
                # extracted)
                pass

        elif x.issym():
            if srp.params.verbosity > 1:
                print("symlink")
            os.symlink(x.linkname, target)

        elif x.islnk():
            if srp.params.verbosity > 1:
                print("hard link")
            # NOTE: This will fail if the archived link is being extracted
            #       prior to the file it links to.  I guess if we're
            #       extracting a link to a nonexistent file, we'd better
            #       follow the link in the archive and extract that file
            #       too.
            #
            # FIXME: What happens if the other file gets extracted in
            #        another thread?  I think it'll still be fine... but
            #        this might be a corner case we need to fix later.
            try:
                os.link(os.path.join(path, x.linkname), target)
            except:
                self.extract(os.path.sep + x.linkname, path)
                os.link(os.path.join(path, x.linkname), target)

        elif x.ischr():
            if srp.params.verbosity > 1:
                print("char device")
            os.mknod(target, x.mode | stat.S_IFCHR,
                     os.makedev(x.devmajor, x.devminor))

        elif x.isblk():
            if srp.params.verbosity > 1:
                print("block device")
            os.mknod(target, x.mode | stat.S_IFBLK,
                     os.makedev(x.devmajor, x.devminor))

        elif x.isfifo():
            if srp.params.verbosity > 1:
                print("fifo")
            os.makefifo(target)

        # set ownership
        #
        # NOTE: For now, I'm going to only chown with uid/gid if the string
        #       user/group isn't set.  In other words, the human readable
        #       ones take precedence.
        u = -1
        g = -1
        if x.uid:
            u = x.uid
        if x.uname:
            try:
                u = pwd.getpwnam(x.uname).pw_uid
            except:
                pass
        if x.gid:
            g = x.gid
        if x.gname:
            try:
                g = grp.getgrnam(x.gname).gr_gid
            except:
                pass
        if srp.params.verbosity > 1:
            print("chowing to user", u, ", group", g)
        try:
            os.lchown(target, u, g)
        except:
            print("WARNING: failed to set ownership of", target, "to",
                  "{}:{}".format(u, g))

        # symlinks don't support the rest of the meta-data, so return
        if x.issym():
            return

        # set mode
        if srp.params.verbosity > 1:
            print("chmoding to", x.mode)
        os.chmod(target, x.mode)

        # set time(s)
        #
        # FIXME: does tar really only track mtime?
        if srp.params.verbosity > 1:
            print("setting mtime", x.mtime)
        os.utime(target, (x.mtime, x.mtime))


    def extractall(self, path=None):
        """Extract the entire contents of the BLOB to the current working
        directory, or to `path' if specified.

        """
        for f in self.manifest:
            self.extract(f, path)
