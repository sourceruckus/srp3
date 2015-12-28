"""Core classes and functions.

This module makes up the guts of the srp module (i.e., it contains all the
functions that actually DO STUFF using the other components of srp).

This module gets merged into the toplevel srp module
"""

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

      build - Parameters for building a package via srp.build()

      install - Parameters for installing a package via srp.install()

      uninstall - Parameters for uninstalling a package via
          srp.uninstall()

      query - Parameters for querying either the installed package
          database or a package on disk via srp.query()

      action - Parameters for srp.action()

    Global Parameters:

      verbosity - Integer representing verbosity level.  0 is off, 1 is a
          little debug, 2 is more, etc...

      dry_run - Don't actually do anything, just print out what WOULD have
          been done.  Since we cannot guarantee that all Feature
          implementers will have appropriately checked this parameter, the
          Feature funcs are not executed when dry_run is set.

      force - Forcefully do something that should otherwise not be done
          (e.g., install even though dependencies aren't met, upgrade to
          same version of a package).

      options - Comma-delimeted list of Features to be enabled (or
          disabled if prefiex with "no_").  This list is used to modify
          the default list of enabled Features at run-time.

    """
    # FIXME: should force be global? or specific to install, perhaps with
    #        a more detailed name?
    #
    def __init__(self):
        # global params
        self.verbosity = 0
        self.dry_run = False
        self.options = []

        # mode param instances
        self.build = None
        self.install = None
        self.uninstall = None
        self.query = None
        self.action = None


class BuildParameters(SrpObject):
    def __init__(self, notes, src, extradir=None, copysrc=False):
        """`notes' is the path to a notes file.  `src' is either the path to a
        source tarball or a directory full of source code.  Paths can use
        fnmatch patterns (e.g., src/foo/foo*.tar.*) but MUST only result
        in a single match.  `extradir', if provided, specifies a path to a
        dir to be used to locate extra files (defaults to directory
        containing the notes file).  If `copysrc' is specified as True,
        the build will create a copy of the source tree (i.e., so we don't
        modify an external source tree).

        """
        # FIXME: we can probably get rid of extradir at this point... it
        #        just doesn't seem to make any sense now that we've nixed
        #        the idea of source packages.
        #
        #        actually, there is a use case still: notes file +
        #        external source dir + dir of "extra files" (e.g., config
        #        files, patches) where notes file isn't in same dir as
        #        extra files.
        #
        #        also, files declared as extra_content in the notes file
        #        are copied into the extra_content dir in the per-package
        #        build tree.  w/out that, build_scripts won't be able to
        #        find their extra config files in the case mentioned
        #        above...
        #
        # FIXME: Is the description of copysrc really needed here?  Isn't
        #        this almost verbatim from the usage message in cli.py?
        #

        # NOTE: We store all paths as absolute here, so that they'll all
        #       still be valid after changing directory.
        #
        self.notes = os.path.abspath(notes)
        self.src = os.path.abspath(src)

        # if not set, default to directory containing notes file
        try:
            self.extradir = os.path.abspath(extradir)
        except:
            self.extradir = os.path.dirname(self.notes)

        self.copysrc = copysrc


class InstallParameters(SrpObject):
    def __init__(self, pkg, allow_upgrade=True):
        """`pkg' is the path to a brp to be installed.  Setting `allow_upgrade' to
        False will disable upgrade logic and raise an error if the
        specified package is already installed.

        """
        self.pkg = pkg
        self.allow_upgrade = allow_upgrade


class QueryParameters(SrpObject):
    def __init__(self, types, criteria):
        """`types` is a comma-delimited list of results the user is asking for
        (e.g., info, files).  `criteria' is a comma-delimited list of
        search things that would make a package match (e.g., package name,
        installed file).

        NOTE: Once successfully instantiated, the `types' and `criteria'
              member variables are both propper Python lists.

        """
        self.types = types
        self.criteria = criteria


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
    build_funcs = srp.work.build.stages["build"]
    build_iter_funcs = srp.work.build.stages["build_iter"]

    # add brp section to NOTES instance
    n.brp = srp.notes.NotesBrp()

    # update notes fields with optional command line flags
    n.update_features(srp.params.options)

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
    print("build funcs:", build_funcs)
    for f in build_funcs:
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
    print("build_iter funcs:", build_iter_funcs)
    flist = list(srp.work.build.manifest.keys())
    flist.sort()
    for x in flist:
        for f in build_iter_funcs:
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
