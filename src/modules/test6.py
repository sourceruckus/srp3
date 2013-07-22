#!/usr/bin/env python3

import multiprocessing
import os
import sys
import tarfile
import tempfile
import time
import io
import pickle
import gzip
import stat
import pwd
import grp

import srp

# testing brp layout options
#
# Option 1:
#     compressed tar:
#         NOTES (plain txt ini)
#         FILES (pickled manifest)
#         BLOB (uncompressed tar)
#
# Option 2:
#     compressed tar:
#         NOTES (plain txt ini)
#         BLOB (pickled manifest, data for regular files...)
#
# The hopeful benefit of my new BLOB format is that all the metadata will be
# at the beginning, so we won't have to iterate through all the archive's
# data to get to the metadata for the last file.  I'm hoping this will allow
# for faster extraction compared to Python's TarFile implementation,
# hopefully also better via multiprocessing.


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
            arcname = os.path.join(root, x).split(payload_dir)[-1]
            # NOTE: Sockets don't go in tarballs.  GNU Tar issues a warning, so
            #       we will too.  I don't know if there are other unsupported
            #       file types, but it looks like gettarinfo returns None if
            #       the file cannot be represented in a tarfile.
            x = tar.gettarinfo(realname, arcname)
            x.uname = "root"
            x.gname = "root"
            del(x.tarfile)
            if x:
                retval[arcname] = {"tinfo": x}
            else:
                print("WARNING: ignoring unsupported file type:", arcname)

    return retval


def blob_create(manifest, pkgdir, fname):
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
        with open(pkgdir+"/"+tinfo.name, 'rb') as f:
            tmp.write(f.read())
        manifest[x]['offset'] = offset
        offset += tinfo.size
    tmp.seek(0)
    tmp.flush()
    
    # now pickle an manifest
    hdr = pickle.dumps(manifest)
    print("sizeof hdr:", len(hdr))
    
    with open(fname, "wb") as f:
        f.write(hdr)
        f.write(tmp.read())

    # NOTE: i think that's enough.  looks like pickle doesn't read beyond
    #       pickled data in a fobj.  in other words, it's safe to append
    #       more data to a file after the pickled byte stream.
    #
    #       f.tell() after reading for pickle.load() will tell us the hdr
    #       offset! yay!


class blob:
    def __init__(self, fname, fobj=None):
        if fobj:
            self.fobj = fobj
        else:
            self.fobj = open(fname, "rb")
        self.manifest = pickle.load(self.fobj)
        self.hdr_offset = self.fobj.tell()

    
    def extract(self, fname, path=None):
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

        # create target file
        #
        # FIXME: we need a block for each possible file type.  regular files
        #        are the only ones with real data, everything else is just
        #        file creation w/ metadata
        if x.isreg():
            offset = self.hdr_offset + self.manifest[fname]["offset"]
            self.fobj.seek(offset)
            with open(target, "wb") as t_fobj:
                t_fobj.write(self.fobj.read(x.size))

        elif x.isdir():
            os.mkdir(target)

        elif x.issym():
            os.symlink(x.linkname, target)

        elif x.islnk():
            # NOTE: This will fail if the archived link is being extracted
            #       prior to the file it links to.  I'm not worried about
            #       this, because we'll be iterating over the files in order
            #       via extractall()
            os.link(x.linkname, target)

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



# NOTE: iterating over tinfo calling extract isn't slower than
#       extractall... but i would have expected it to be... makes me think
#       that extractall must not be very optimized
def extractor_file(tinfo, filename):
    pkg = tarfile.open(filename)
    for x in tinfo:
        #print(multiprocessing.current_process().name, x)
        pkg.extract(x)



if __name__ == "__main__":
    print("hello")

    pkgfile = sys.argv[1]
    pkgdir = sys.argv[2]

    create = 0
    try:
        create=os.environ["CREATE"]
    except:
        pass
    if create:
        print("creating manifest for", pkgdir)
        m = manifest_create(pkgdir)
        print("writing", pkgfile)
        blob_create(m, pkgdir, pkgfile)
        sys.exit(0)

    print("loading blob from", pkgfile)
    b = blob(pkgfile)

    print("extracting into", pkgdir)
    b.extractall(pkgdir)

    sys.exit(1)




    # this doesn't seem to make a difference.  did 2 runs of test5 and 2 of
    # test4 and they all took the same ammount of time +/- 2 seconds.
    print("creating decompressed tmp file")
    with open("tmp", "wb") as tmp:
        with gzip.open(pkgfile, "rb") as f:
            tmp.write(f.read())
    print("done")

    print("loading pickled FILES")
    biglist = pickle.load(open("FILES", "rb"))
    print("done")
    print("partitioning list")
    sublists = srp.features.core.partition_list(biglist, 4)
    print("made", len(sublists), "sublists")
    
    print("extracting...")
    plist=[]
    for sublist in sublists:
        plist.append(
            multiprocessing.Process(target=extractor_file,
                                    args=(sublist, "tmp")))
        plist[-1].start()
    for p in plist:
        print("joining:", p)
        p.join()
