"""Core classes and functions.

This module makes up the guts of the srp module (i.e., it contains all the
functions that actually DO STUFF using the other components of srp).

This module gets merged into the toplevel srp module.
"""

import glob
import hashlib
import os
import pickle
import platform
import tarfile
import tempfile
import time
import types

import srp


class SrpObject:
    """Base object for all srp objects.  Basically just adds some debugging
    routines.

    """
    def __str__(self):
        """This __str__ method is special in that it scales its verbosity
        according to srp.params.verbosity.  A value of 0 results in output
        identical to __repr__(), 1 results in additionally including a
        __str__() of each data member.

        """
        ret = repr(self)
        if srp.params.verbosity <= 1:
            return ret

        # slice off the trailing '>'
        ret = ret[:-1]
        for k in dir(self):
            v = getattr(self, k)
            if k.startswith("_") or type(v) == types.MethodType:
                continue
            ret+=", {}={}".format(k, v)
        ret += '>'
        return ret


class RunTimeParameters(SrpObject):
    """Class representing the work to be done for this invocation of srp.

    Each high-level operational mode (e.g., build) of srp has its own
    class to handle it's parameters:

      build - instance of BuildParameters

      install - instance of InstallParameters

      uninstall - instance of UninstallParameters

      query - instance of QueryParameters

      action - instance of ActionParameters

    Global Parameters:

      verbosity - Integer representing verbosity level.  0 is off, 1 is a
          little debug, 2 is more, etc...

      dry_run - Don't actually do anything, just print out what WOULD have
          been done.  Since we cannot guarantee that all Feature
          implementers will have appropriately checked this parameter, the
          Feature funcs are not executed when dry_run is set.

      root - Alternate root dir (like DESTDIR or SRP_ROOT_PREFIX).  Will
          get set to "/" by default.

      force - Forcefully do something that should otherwise not be done
          (e.g., install even though dependencies aren't met, upgrade to
          same version of a package).

      options - List of of Features to be enabled (or disabled if prefixed
          with "no_").  This list is used to modify the default list of
          enabled Features at run-time.


    FIXME: should force be global? or specific to install, perhaps with a
           more detailed name?

    """
    def __init__(self):
        # global params
        self.verbosity = 0
        self.dry_run = False
        self.root = "/"
        self.options = []

        # mode param instances
        self.build = None
        self.install = None
        self.uninstall = None
        self.query = None
        self.action = None

    def __setattr__(self, name, value):
        """This __setattr__ method is special only in that it automatically
        re-invokes srp.db.load() if `root' is being set.

        """
        # set it
        object.__setattr__(self, name, value)

        # reload the database if we just modified 'root' and db module has
        # already been loaded
        if name == "root" and hasattr(srp, "db"):
            srp.db.load()


# FIXME: where should this go?
def expand_path(path):
    """Returns a single, expanded, absolute path.  `path' arg can be shell
    glob, but must result in only a single match.  An exception is raised
    on any globbing errors (e.g., not found, multiple matches) or if the
    resulting path doesn't exist.

    """
    rv = glob.glob(path)
    if not rv:
        raise Exception("no such file - {}".format(path))

    if len(rv) != 1:
        raise Exception("glob had multiple matches - {}".format(path))

    rv = os.path.abspath(rv[0])
    return rv


class BuildParameters(SrpObject):
    """Class representing the parameters for srp.build().

    Data:

      notes - Absolute path to the notes file on disk.

      src - Either the absolute path to a source tarball or a directory
          full of source code.

      extradir - Specifies an absolute path to a dir to be used to locate
          extra files.  Defaults to directory containing the notes file.

      copysrc - If True, the build will create a copy of the source tree
          (i.e., so we don't modify an external source tree).  Defaults to
          False.


    FIXME: we can probably get rid of extradir at this point... it just
           doesn't seem to make any sense now that we've nixed the idea of
           source packages.
    
           actually, there is a use case still: notes file + external
           source dir + dir of "extra files" (e.g., config files, patches)
           where notes file isn't in same dir as extra files.
    
           also, files declared as extra_content in the notes file are
           copied into the extra_content dir in the per-package build
           tree.  w/out that, build_scripts won't be able to find their
           extra config files in the case mentioned above...
    
    FIXME: Is the description of copysrc really needed here?  Isn't this
           almost verbatim from the usage message in cli.py?
    
    """
    def __init__(self, notes, src, extradir=None, copysrc=False):
        """The paths `notes', `src', and `extradir' can be specified as relative
        paths, but will get stored away as absolute paths.

        Paths can use shell globbing (e.g., src/foo/foo*.tar.*) but MUST
        only result in a single match.

        """
        self.notes = expand_path(notes)
        self.src = expand_path(src)

        # if not set, default to directory containing notes file
        try:
            self.extradir = expand_path(extradir)
        except:
            self.extradir = os.path.dirname(self.notes)

        self.copysrc = copysrc


class InstallParameters(SrpObject):
    """Class representing the parameters for srp.install().

    Data:

      pkg - Absolute path to a brp to be installed.

      allow_upgrade - Setting to False will disable upgrade logic and
          raise an error if the specified package is already installed.
          Defaults to True.

    """
    def __init__(self, pkg, allow_upgrade=True):
        """The path `pkg' can be specified as a relative path and can use shell
        globbing.

        """
        self.pkg = expand_path(pkg)
        self.allow_upgrade = allow_upgrade


class QueryParameters(SrpObject):
    """Class representing the parameters for srp.query().

    Data:

      types - a list of results the user is asking for (e.g., [info,
          files]).

      criteria - a list of search things that would make a package match
          (e.g., package name, installed file).

    """
    def __init__(self, types, criteria):
        """Both `types` and `criteria' are comma-delimited lists, which get
        split on ',' and stored away as lists.  Validity of both arguments is
        handled by the srp.query() method.

        """
        self.types = types.split(',')
        self.criteria = criteria.split(',')


def build():
    """Builds a package according to the RunTimeParameters instance
    `srp.params'.  The features.WorkBag instance `srp.work' is created
    using a NotesFile instance created from the notes file specified in
    `srp.params'.

    """
    # create our work instance
    srp.work.build = srp.features.BuildWork()

    # get some local refs with shorter names
    n = srp.work.build.notes
    funcs = srp.work.build.funcs
    iter_funcs = srp.work.build.iter_funcs

    # FIXME: should the core feature func untar the srp in a tmp dir? or
    #        should we do that here and pass tmpdir in via our work
    #        map...?  i think that's the only reason any of the build
    #        funcs would need the tarfile instance...  might just boil
    #        down to how determined i am to make the feature funcs do as
    #        much of the work as possible...
    #
    #        it might also come down to duplicating code all over the
    #        place... chances are, there's a bunch of places where we'll
    #        need to create the tmpdir and extract a package's
    #        files... in which case we'll rip that out of the core
    #        feature's build_func and put it somewhere else.

    print(srp.work)

    # run through all queued up stage funcs for build
    print("features:", n.header.features)
    print("build funcs:", funcs)
    for f in funcs:
        # check for notes section class and create if needed
        section = getattr(getattr(srp.features, f.name),
                          "Notes"+f.name.capitalize(), False)
        if section and not getattr(n, f.name, False):
            print("creating notes section:", f.name)
            setattr(n, f.name, section())

        print("executing:", f)
        if not srp.params.dry_run:
            try:
                f.func()
            except:
                print("ERROR: failed feature stage function:", f)
                raise

    # now run through all queued up stage funcs for build_iter
    #
    # FIXME: multiprocessing
    print("build_iter funcs:", iter_funcs)
    flist = list(srp.work.build.manifest.keys())
    flist.sort()
    for x in flist:
        for f in iter_funcs:
            # check for notes section class and create if needed
            section = getattr(getattr(srp.features, f.name),
                              "Notes"+f.name.capitalize(), False)
            if section and not getattr(n, f.name, False):
                print("creating notes section:", f.name)
                setattr(n, f.name, section())

            print("executing:", f, x)
            if not srp.params.dry_run:
                try:
                    f.func(x)
                except:
                    print("ERROR: failed feature stage function:", f)
                    raise

    # create the toplevel brp archive
    #
    # FIXME: we should remove this file if we fail...
    mach = platform.machine()
    if not mach:
        mach = "unknown"
    pname = "{}.{}.brp".format(n.header.fullname, mach)
    print("finalizing", pname)

    if srp.params.dry_run:
        # nothing more to do, since we didn't actually build anything to
        # finalize into a brp...
        return

    # FIXME: compression should be configurable globally and also via
    #        the command line when building.
    #
    if srp.config.default_compressor == "lzma":
        import lzma
        __brp = lzma.LZMAFile(pname, mode="w",
                              preset=srp.config.compressors["lzma"])
    elif srp.config.default_compressor == "bzip2":
        import bz2
        __brp = bz2.BZ2File(pname, mode="w",
                            compresslevel=srp.config.compressors["bz2"])
    elif srp.config.default_compressor == "gzip":
        import gzip
        __brp = gzip.GzipFile(pname, mode="w",
                              compresslevel=srp.config.compressors["gzip"])
    else:
        # shouldn't really ever happen
        raise Exception("invalid default compressor: {}".format(
            srp.config.default_compressor))

    brp = tarfile.open(fileobj=__brp, mode="w|")
    sha = hashlib.new("sha1")

    # populate the BLOB archive
    #
    # NOTE: This is where we actually add TarInfo objs and their associated
    #       fobjs to the BLOB, then add the BLOB to the brp archive.
    #
    # NOTE: This is implemented using a temporary file as the fileobj for a
    #       tarfile.  When the fobj is closed it's contents are lost, but
    #       that's fine because we will have already added it to the toplevel
    #       brp archive.
    n.brp.time_blob_creation = time.time()
    blob_fobj = tempfile.TemporaryFile()
    srp.blob.blob_create(srp.work.build.manifest,
                         srp.work.topdir+'/payload', fobj=blob_fobj)
    n.brp.time_blob_creation = time.time() - n.brp.time_blob_creation
    # add BLOB file to toplevel pkg archive
    blob_fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="BLOB", fileobj=blob_fobj),
                fileobj=blob_fobj)
    # rewind and generate a SHA entry
    blob_fobj.seek(0)
    sha.update(blob_fobj.read())
    blob_fobj.close()

    # add NOTES (pickled instance) to toplevel pkg archive (the brp)
    n_fobj = tempfile.TemporaryFile()
    # last chance toupdate time_total
    n.brp.time_total = time.time() - n.brp.time_total
    pickle.dump(n, n_fobj)
    n_fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="NOTES", fileobj=n_fobj),
                fileobj=n_fobj)
    # rewind and generate a SHA entry
    n_fobj.seek(0)
    sha.update(n_fobj.read())
    n_fobj.close()

    # create the SHA file and add it to the pkg
    with tempfile.TemporaryFile() as f:
        f.write(sha.hexdigest().encode())
        f.seek(0)
        brp.addfile(brp.gettarinfo(arcname="SHA", fileobj=f),
                    fileobj=f)

    # FIXME: all the files are still left in /tmp/srp-asdf...

    # close the toplevel brp archive
    brp.close()
    __brp.close()


def install():
    """Installs a package according to the RunTimeParameters instance
    `srp.params'.

    """
    # create our work instance
    srp.work.install = srp.features.InstallWork()

    # get some local refs with shorter names
    n = srp.work.install.notes
    m = srp.work.install.manifest
    funcs = srp.work.install.funcs
    iter_funcs = srp.work.install.iter_funcs

    # run through install funcs
    print("features:", n.header.features)
    print("install funcs:", funcs)
    for f in funcs:
        # check for notes section class and create if needed
        section = getattr(getattr(srp.features, f.name),
                          "Notes"+f.name.capitalize(), False)
        if section and not getattr(n, f.name, False):
            print("creating notes section:", f.name)
            setattr(n, f.name, section())

        print("executing:", f)
        if not srp.params.dry_run:
            try:
                f.func()
            except:
                print("ERROR: failed feature stage function:", f)
                raise

    # now run through all queued up stage funcs for install_iter
    #
    # FIXME: multiprocessing
    print("install_iter funcs:", iter_funcs)
    flist = list(m.keys())
    flist.sort()
    for x in flist:
        for f in iter_funcs:
            # check for notes section class and create if needed
            section = getattr(getattr(srp.features, f.name),
                              "Notes"+f.name.capitalize(), False)
            if section and not getattr(n, f.name, False):
                print("creating notes section:", f.name)
                setattr(n, f.name, section())

            print("executing:", f, x)
            if not srp.params.dry_run:
                try:
                    f.func(x)
                except:
                    print("ERROR: failed feature stage function:", f)
                    raise

    # commit NOTES to disk in srp db
    #
    # NOTE: We need to refresh our copy of n because feature funcs may have
    #       modified the copy in work[].
    #
    n = srp.work.install.notes

    # commit MANIFEST to disk in srp db
    #
    # NOTE: We need to refresh our copy because feature funcs may have
    #       modified it
    #
    m = srp.work.install.manifest

    # register w/ srp db
    inst = srp.db.InstalledPackage(n, m)
    srp.db.register(inst)

    # commit db to disk
    #
    # FIXME: is there a better place for this?
    if not srp.params.dry_run:
        srp.db.commit()
