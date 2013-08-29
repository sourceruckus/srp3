"""The SRP db module - on-disk representation of installed pacakges and
lookup functions
"""

import srp
from pprint import pprint


# let's store the db as a pickled map
#
# db = {pkg1: [inst1, inst2, ...], ...}
#
# each installed version is referenced by sha of its db contents, which is
# NOTES and pickled FILES (and perhaps other files as well).
#
# inst = pickeld {"FILES": files_obj, "NOTES": notes_obj, ...}


# hmm, i'm falling into the trap of holding everything (even our files
# contents) in memory.  i don't want to do that.  i want to use the disk to
# hold all the big stuff, and just have pickled meta-data

# take 2:
#
# /var/lib/srp/db (this is the pickled meta-data)
#
# /var/lib/srp/objects/ (this is a directory of sha dirs, each containing a package's files)
# /var/lib/srp/objects/d976b5ba0496df79b7e9c63dd7b82372dd903a45/NOTES (txt)
# /var/lib/srp/objects/d976b5ba0496df79b7e9c63dd7b82372dd903a45/FILES (pickled)
#
# the db object is now a map like this:
#
# {"pkgname", ["shadirname", ...], ...}
#
# so db[foo] will return the list of installed shadirs for the package named
# foo.


# should we keep NOTES as a txt file or pickled NOTES instance?

# should the sha be of NOTES, NOTES+FILES, or everything in the dir?  if we
# do everything (which would make sense from a uniqueness standpoint), we
# might end up incurring some rather time consuming sha-ing if we have a
# repairable package (contains the actual BLOB) in the shadir.
#
# right now, sha is the one embedded in the brp (i.e., it's the shasum of
# the original brp's contents (BLOB, NOTES)).  this would mean that no matter what extra things we do
# at install time (or later on via actions), the sha for the installed
# pacakge would remain constant.
#
# perhaps we should put the installed-from brp's sha in NOTES, but use a
# freshly calculated sha for the db dir?  do we keep track of the built-from
# srp's sha anywhere?  do we care about this level of tracability?


def refresh():
    import os
    # FIXME: path to db in config?
    #
    # FIXME: DESTDIR?  --root?  both/either?
    try:
        dbpath = os.getenv("DESTDIR")
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
