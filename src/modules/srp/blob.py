"""The SRP BLOB file
"""

import os
import tarfile
import tempfile
import pickle
import stat
import pwd
import grp

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

def manifest_create(payload_dir):
    retval = {}
    # NOTE: This tar object is just so we can use the gettarinfo member
    #       function
    tar = tarfile.open("tar", fileobj=tempfile.TemporaryFile(), mode="w")
    for root, dirs, files in os.walk(payload_dir):
        tmp = dirs[:]
        tmp.extend(files)
        # NOTE: sorting here adds a little processing overhead, but if we're
        #       going to keep these TarInfo objects around in a map and then
        #       try to actually add them to the BLOB later, we have to make
        #       sure that the order they get added matches the order in
        #       which the TarInfo's were created, otherwise we might add a
        #       hardlink before we add the file it's linked to, which will
        #       cause the extraction to fail during install
        tmp.sort()
        for x in tmp:
            realname = os.path.join(root, x)
            arcname = os.path.join(root, x).split(payload_dir, 1)[-1]

            # NOTE: Sockets don't go in tarballs.  GNU Tar issues a warning, so
            #       we will too.  I don't know if there are other unsupported
            #       file types, but it looks like gettarinfo returns None if
            #       the file cannot be represented in a tarfile.
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
            #       returned from TarFile.getmember() don't have this, but
            #       ones returned from TarFile.gettarinfo() do.
            del(x.tarfile)

            retval[arcname] = {"tinfo": x}

    return retval


def blob_create(manifest, payload_dir, fname=None, fobj=None):
    if not fname and not fobj:
        raise Exception("requires either fname or fobj")

    # create temporary file containing all the data from regular files
    # concatenated, while adding offset values to the manifest.
    tmp = tempfile.TemporaryFile()
    offset=0
    flist = list(manifest.keys())
    flist.sort()
    for x in flist:
        tinfo = manifest[x]['tinfo']
        if not tinfo.isreg():
            continue
        with open(payload_dir+"/"+tinfo.name, 'rb') as f:
            tmp.write(f.read())
        manifest[x]['offset'] = offset
        offset += tinfo.size
    tmp.seek(0)
    tmp.flush()
    
    # now pickle the manifest
    hdr = pickle.dumps(manifest)
    
    if fobj:
        f = fobj
    else:
        f = open(fname, "wb")

    f.write(hdr)
    f.write(tmp.read())

    # only close the file object if we opened it
    if not fobj:
        f.close()

    # NOTE: i think that's enough.  looks like pickle doesn't read beyond
    #       pickled data in a fobj.  in other words, it's safe to append
    #       more data to a file after the pickled byte stream.
    #
    #       f.tell() after reading for pickle.load() will tell us the hdr
    #       offset! yay!


class blob:
    def __init__(self, fname):
        self.fname = fname
        self.fobj = open(fname, "rb")
        self.manifest = pickle.load(self.fobj)
        self.hdr_offset = self.fobj.tell()

        # FIXME: Should I update each manifest offset entry to reflect
        #        hdr_offset?  Assuming that manifest gets pickled and
        #        restored prior to installation, this should make
        #        extraction a tad faster at the expense of a little extra
        #        work during build.  It would also allow us to pass a
        #        pre-created manifest into the constructor...


    # FIXME: this needs to make backups of existing files.  i think we'll
    #        add the upgrade logic via an upgrade feature, but we need to
    #        at least make srpbak files here.
    def extract(self, fname, path=None, __c=True):
        # get the TarInfo object
        x = self.manifest[fname]['tinfo']

        # decide on a full target pathname
        if path:
            target = os.path.join(path, x.name)
        else:
            target = x.name

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
            if __c:
                srp._blob.extract(self.fname, target, offset, x.size)
            else:
                self.fobj.seek(offset)
                with open(target, "wb") as t_fobj:
                    t_fobj.write(self.fobj.read(x.size))

        elif x.isdir():
            try:
                os.mkdir(target)
            except:
                # We'll get OSError if we've already created this dir
                # (e.g., as a leading path element to a file we've already
                # extracted)
                pass

        elif x.issym():
            os.symlink(x.linkname, target)

        elif x.islnk():
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
            os.mknod(target, x.mode | stat.S_IFCHR,
                     os.makedev(x.devmajor, x.devminor))

        elif x.isblk():
            os.mknod(target, x.mode | stat.S_IFBLK,
                     os.makedev(x.devmajor, x.devminor))

        elif x.isfifo():
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
        try:
            os.lchown(target, u, g)
        except:
            print("WARNING: failed to set ownership of", target, "to",
                  "{}:{}".format(u, g))

        # symlinks don't support the rest of the meta-data, so return
        if x.issym():
            return

        # set mode
        os.chmod(target, x.mode)

        # set time(s)
        #
        # FIXME: does tar really only track mtime?
        os.utime(target, (x.mtime, x.mtime))


    def extractall(self, path=None):
        flist = list(self.manifest.keys())
        flist.sort()
        for f in flist:
            self.extract(f, path)
