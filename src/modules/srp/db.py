"""The SRP db module - on-disk representation of installed pacakges and
lookup functions
"""
import os
import pickle
import hashlib

import srp
from pprint import pprint


# let's store the db as a pickled map
#
# db = {pkg1: [inst1, inst2, ...], ...}
#
# each installed version is referenced by sha of its pickled db contents,
# which is NOTES and MANIFEST (and perhaps other files as well).


class installed_package:
    def __init__(self, notes, manifest):
        self.notes = notes
        self.manifest = manifest

        # gen sha of data stream consisting of pickled notes and manifest
        # objects
        #
        # NOTES: The sha will be used to store aditional files on disk (as
        #        apposed to pickled in the db).
        sha = hashlib.new("sha1")
        sha.update(pickle.dumps(notes))
        sha.update(pickle.dumps(manifest))
        self.sha = sha.hexdigest().encode()



    def addfile(self, name, fobj):
        """creates an additional file in the sha-specific object dir"""
        pass

    def removefile(self, name):
        """removes an additional file from the object dir"""
        pass



#
# /var/lib/srp/db (this is the pickled meta-data)
#
# /var/lib/srp/objects/ (this is a directory of sha dirs, each containing a package's extra files)
# /var/lib/srp/objects/d976b5ba0496df79b7e9c63dd7b82372dd903a45/something_extra


# should the sha be of NOTES, NOTES+MANIFEST, or everything in the dir?  if we
# do everything (which would make sense from a uniqueness standpoint), we
# might end up incurring some rather time consuming sha-ing if we have a
# repairable package (contains the actual BLOB) in the shadir.
#
# actually, there's probably no need to include the extra stuff in the sha.
# for example, modifying/adding/removing a file will generally cause
# MANIFEST to be modified (unless it's modify and checksum is disabled).
# adding/removing extra content should generaly cause NOTES to be updated.
# modifying extra content might not get noticed.
#
# right now, sha is the one embedded in the brp (i.e., it's the shasum of
# the original brp's contents (BLOB, NOTES)).  this would mean that no matter what extra things we do
# at install time (or later on via actions), the sha for the installed
# pacakge would remain constant.
#
# perhaps we should put the installed-from brp's sha in NOTES, but use a
# freshly calculated sha for the db dir?  do we keep track of the built-from
# srp's sha anywhere?  do we care about this level of tracability?


# probably can't just use the module's toplevel namespace as the db, as i'm
# gonna need to be able to easily unpickle/repickle the db contents all the
# time.
#__db = {}


def register(p):
    """register installed_package instance p in the db"""
    name = p["notes"].info.name
    try:
        __db[name].append(p)
    except:
        __db[name] = [p]


# FIXME: path to db in config?
#
# FIXME: DESTDIR?  --root?  both/either?
try:
    dbpath = os.environ["DESTDIR"]
except:
    dbpath = ""
dbpath+="/var/lib/srp/db"


def commit():
    """re-pickle __db to disk"""
    with open(dbpath, "wb") as f:
        pickle.dump(__db, f)


def load():
    """un-pickle __db from disk"""
    global __db
    try:
        with open(dbpath, "rb") as f:
            __db = pickle.load(f)
    except IOError:
        __db = {}
    except Exception as e:
        # NOTE: Anything other than IOError means the file was there but
        #       corrupt... user is gonna want to know about that.
        print("ERROR: failed to load __db:", e)
        raise


# FIXME: think this is OBE...
def refresh():
    import os
    # FIXME: path to db in config?
    #
    # FIXME: DESTDIR?  --root?  both/either?
    try:
        dbpath = os.environ["DESTDIR"]
    except:
        dbpath = ""
    dbpath+="/var/lib/srp/"

    objs = os.listdir(dbpath)
    print(objs)
    for x in objs:
        path = dbpath+"/"+x+"/"
        print(os.listdir(path))
        with open(path+"NOTES", "rb") as f:
            n = srp.notes.notes(f)
        print(n)
        #print(dir())
        #print(dir(srp.db))
        #print(locals())
        #print(globals())
        g = globals()
        try:
            g[n.info.name].append(n)
        except:
            g[n.info.name] = [n]


#srp.db.foo = [{"af4237": {

# foo = [{"n": <notes inst>, "shadir": "af43212"}, {"n": <notes inst>, "shadir": "ff2315"}]

# srp.db.foo[0]['n'].info.name


# these functions lookup and return installed package instances or None
#
# they should probably all return a list, just in case there's multiple
# matches.
#
# names should use fnmatch to support basic completion

def lookup_by_name(pkgname):
    pass

def lookup_by_file(filename):
    pass

def lookup_by_dep_lib(libname):
    pass

def lookup_by_builder():
    pass

#def lookup_by...description...install_date...build_date...

# should we just plumb something up to dynamically query on any field in
# NOTES?




load()