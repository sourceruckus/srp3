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
import shutil
import stat
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
        according to srp.params.verbosity.  A value of 0 or 1 results in
        output identical to __repr__(), 2 results in additionally
        including a __str__() of each data member.
        
        NOTE: The verbosity scaling is assuming that at 0, you're not
              printing anything, and at 1 you want basic info.  2 and up
              adds more and more until you drown in information.  ;-)

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
        """This special __setattr__ method does some extra work if `root' is
        being set.  Namely, it 1) ensures that the new rootdir exists, creating
        it if needed, and 2) automatically re-invokes srp.db.load() if
        it's already been loaded.

        """
        # set it
        object.__setattr__(self, name, value)

        # reload the database if we just modified 'root' and db module has
        # already been loaded
        if name == "root":
            os.makedirs(value, exist_ok=True)
            if hasattr(srp, "db"):
                srp.db.load()


class BuildParameters(SrpObject):
    """Class representing the parameters for srp.build().

    Data:

      notes - Absolute path that has already been validated (i.e., it
          exists, glob only matched a single item).

      src - Absolute path, already validated.

      extradir - Absolute, validated path.

      copysrc - Same as param to __init__.

      gitsrc - Same as param to __init__.

      update - Internally, we still go through some of the motions even if
          the package is not being built.  This allows for enough of the
          BuildWork to get populated for subsequent InstallParams to be
          created (e.g., we can look at srp.work.build.notes to figure out
          package name).

    NOTE: This describes how the data members DIFFER from the args passed
          into the constructor.  See __init__ for the full story.

    """
    __slots__ = ["notes", "src", "extradir", "copysrc", "gitsrc", "update"]
    def __init__(self, notes, src=None, extradir=None, copysrc=False,
                 gitsrc=None, update=False):
        """Args:
        
          notes - Path to the NOTES file used for building the package.

          src - Path to either a source tarball or a directory full of
              source code.  Defaults to the directory containing the NOTES
              file.

          extradir - Path to a dir to be used to locate extra files
              required by the build_script.  Defaults to directory
              containing the NOTES file.

          copysrc - If set to True, the build will create a copy of the
              source tree (i.e., so we don't modify an external source
              tree).  Defaults to False.

          gitsrc - If specified, the build will create a copy of the
              source tree by cloning via git and checking out the
              specified branch ("HEAD" results in no additional checkout).
              Defaults to None.

          update - If set to True, only build the package if the NOTES
              file is newer than the built package (or the package hasn't
              ever been built).  Defaults to False.

        NOTE: All paths can be specified as relative paths, but will get
              stored away as absolute paths after validation.

        NOTE: All paths can use shell globbing (e.g., src/foo/foo*.tar.*)
              but MUST only result in a single match.

        """
        self.notes = srp.utils.expand_path(notes)

        # if not set, default to directory containing notes file
        try:
            self.src = srp.utils.expand_path(src)
        except:
            self.src = os.path.dirname(self.notes)

        # if not set, default to directory containing notes file
        try:
            self.extradir = srp.utils.expand_path(extradir)
        except:
            self.extradir = os.path.dirname(self.notes)

        self.copysrc = copysrc
        self.gitsrc = gitsrc
        self.update = update

        # error checking
        if copysrc and gitsrc:
            raise Exception("cannot specify both `copysrc` and `gitsrc`")


class InstallParameters(SrpObject):
    """Class representing the parameters for srp.install().

    Data:

      pkg - Absolute, validated path.

      upgrade - Same as param to __init__.

    NOTE: This describes how the data members DIFFER from the args passed
          into the constructor.  See __init__ for the full story.

    """
    __slots__ = ["pkg", "upgrade"]
    def __init__(self, pkg, upgrade=True):
        """Args:
        
          pkg - Path to the package to be installed.

          upgrade - Setting to False will disable upgrade logic and raise
              an error if the specified package is already installed.
              Defaults to True.

        NOTE: All paths can be specified as relative paths, but will get
              stored away as absolute paths after validation.

        NOTE: All paths can use shell globbing (e.g., src/foo/foo*.tar.*)
              but MUST only result in a single match.

        """
        self.pkg = srp.utils.expand_path(pkg)
        self.upgrade = upgrade


class QueryParameters(SrpObject):
    """Class representing the parameters for srp.query().

    Data:

      types - Stored as a list.

      criteria - Stored as a dict.

    NOTE: This describes how the data members DIFFER from the args passed
          into the constructor.  See __init__ for the full story.

    """
    __slots__ = ["types", "criteria"]
    def __init__(self, types, criteria):
        """Args:
        
          types - Comma-delimited list of types of results the user is
              asking for (e.g., 'info,files')

          criteria - Comma-delimited list of key=val pairs describing the
              search criteria that would make a package match (e.g.,
              'pkg=*').

        """
        self.types = types
        self.criteria = criteria


# FIXME: decorator to purge topdir when we're done?

def build():
    """Builds a package according to the RunTimeParameters instance
    `srp.params'.  All work is stored in the features.WorkBag instance
    `srp.work'.

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
    for x in srp.work.build.manifest:
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
    n.brp.pname = pname
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
    blob = srp.blob.BlobFile()
    blob.manifest = srp.work.build.manifest
    blob.fobj = tempfile.TemporaryFile()
    blob.tofile()
    n.brp.time_blob_creation = time.time() - n.brp.time_blob_creation
    # add BLOB file to toplevel pkg archive
    blob.fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="BLOB", fileobj=blob.fobj),
                fileobj=blob.fobj)
    # rewind and generate a SHA entry
    blob.fobj.seek(0)
    sha.update(blob.fobj.read())
    blob.fobj.close()

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

    # close the toplevel brp archive
    brp.close()
    __brp.close()

    # clean out topdir
    for g in glob.glob("{}/*".format(srp.work.topdir)):
        if os.path.isdir(g):
            shutil.rmtree(g)
        else:
            os.remove(g)

    # FIXME: should i clear srp.work.build at this point?  it shouldn't
    #        really hurt anything if i leave it... and maybe it will be
    #        helpful during a --build-and-install?


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
    for x in m:
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

    # clean out topdir
    for g in glob.glob("{}/*".format(srp.work.topdir)):
        if os.path.isdir(g):
            shutil.rmtree(g)
        else:
            os.remove(g)


# FIXME: Need to document these query type and criteria ramblings
#        somewhere user-visible...
#
# -q type[,type,...],criteria[,criteria]
#
# valid types:
#   - name (package name w/ version)
#   - info (summary)
#   - files (filenames)
#   - stats (stats for each file)
#   - size (total size of installed package)
#   - raw (super debug all)
#
# valid criteria:
#   - pkg (glob pkgname or path to brp)
#   - file (glob name of installed file)
#   - date_installed (-/+ for before/after)
#   - date_built (-/+ for before/after)
#   - size (-/+ for smaller/larger)
#   - grep (find string in info)
#   - built_by (glob builder name)
#   - built_on (glob built on host)
#
#
# What package installed the specified file:
#   srp -q name,file=/usr/lib/libcrust.so
#
# Show description of installed package:
#   srp -q info,pkg=srp-example
#
# List all files installed by package
#   srp -q files,pkg=srp-example
#
# List info,files for package on disk
#   srp -q info,files,pkg=./foo.brp
#
# List packages installed after specified date:
#   srp -q name,date_installed=2015-11-01+
#
#   srp -q name,date_built=2015-11-01+
#
#   srp -q name,size=1M+
#
#   srp -q name,built_by=mike
#
# Search through descriptions for any packages that match a pattern:
#   srp -q name,grep="tools for flabbergasting"
#
# Everything, and I mean everything, about a package:
#   srp -q raw,pkg=srp-example
#
def query():
    """Performs a query according to the RunTimeParamters instance
    `srp.params'.

    FIXME: This mode is really different from the others... it doesn't
           actually correlate with any stages defined by the Features API
           and it doesn't really need a QueryWork object...

    FIXME: I wonder if we should add a way for Features to define new
           query types or criteria?  I've already got things plubmed into
           feature_struct to add output to `info' queries... but I do have
           size listed as a potention criteria in my ramblings
           above... and size is defined via the Features API...

    """
    matches = []
    for k in srp.params.query.criteria:
        v = srp.params.query.criteria[k]
        print("k={}, v={}".format(k, v))
        if k == "pkg":
            # glob pkgname or path to brp
            matches.extend(query_pkg(v))
        elif k == "file":
            # glob name of installed file
            matches.extend(query_file(v))
        else:
            raise Exception("Unsupported criteria '{}'".format(k))

    print("fetching for all matches: {}".format(srp.params.query.types))
    for m in matches:
        for t in srp.params.query.types:
            if t == "name":
                print(format_results_name(m))
            elif t == "info":
                print(format_results_info(m))
            elif t == "files":
                print(format_results_files(m))
            elif t == "stats":
                print(format_results_stats(m))
            elif t == "raw":
                print(format_results_raw(m))
            else:
                raise Exception("Unsupported query type '{}'".format(t))

    # clean out topdir
    for g in glob.glob("{}/*".format(srp.work.topdir)):
        if os.path.isdir(g):
            shutil.rmtree(g)
        else:
            os.remove(g)


# FIXME: we should put all the pre-defined query_type and format_results
#        funcs somewhere else and dynamically extend them via the Features
#        API.
#
def query_pkg(name):
    if os.path.exists(name):
        # query package file on disk
        #
        # FIXME: shouldn't there be a helper func for basic brp-on-disk
        #        access?
        #
        with tarfile.open(name) as p:
            n_fobj = p.extractfile("NOTES")
            n = pickle.load(n_fobj)
            blob_fobj = p.extractfile("BLOB")
            blob = srp.blob.BlobFile.fromfile(fobj=blob_fobj)
            m = blob.manifest

        return [srp.db.InstalledPackage(n, m)]

    else:
        # query installed package via db
        return srp.db.lookup_by_name(name)


def format_results_name(p):
    return "-".join((p.notes.header.name,
                     p.notes.header.version,
                     p.notes.header.pkg_rev))


def format_results_info(p):
    # FIXME: make this a nice multi-collumn summary of the NOTES file,
    #        excluding build_script, perms, etc
    #
    # FIXME: wrap text according to terminal size for description
    #
    info = []
    info.append("Package: {}".format(format_results_name(p)))
    info.append("Description: {}".format(p.notes.header.description))
    
    for f in srp.features.registered_features:
        info_func = srp.features.registered_features[f].info
        if info_func:
            info.append(info_func(p))

    return "\n".join(info)


def format_results_files(p):
    return "\n".join(p.manifest.sortedkeys)


def format_tinfo(t):
    fmt = "{mode} {uid:8} {gid:8} {size:>8} {date} {name}{link}"
    mode = stat.filemode(t.mode)
    uid = t.uname or t.uid
    gid = t.gname or t.gid
    if t.ischr() or t.isblk():
        size = "{},{}".format(t.devmajor, t.devminor)
    else:
        size = t.size
    date = "{}-{:02}-{:02} {:02}:{:02}:{:02}".format(
        *time.localtime(t.mtime)[:6])
    name = t.name + ("/" if t.isdir() else "")
    if t.issym():
        link = " -> " + t.linkname
    elif t.islnk():
        link = " link to " + t.linkname
    else:
        link = ""
    return fmt.format(**locals())


def format_results_stats(p):
    retval = []
    for f in p.manifest:
        tinfo = p.manifest[f]["tinfo"]
        retval.append(format_tinfo(tinfo))
    return "\n".join(retval)


def format_results_raw(p):
    return "{}\n{}".format(
        p.notes,
        p.manifest)
