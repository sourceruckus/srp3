"""Module implementing the SRP Feature API.

The SRP Feature API is used to make the package manager as flexible and
extensible as possible.  This API provides programmers with an easy way to
add new features without having to rewrite massive blocks of nasty code
and introduce unseemly regressions (see SRP v2, regrettably).

The basic idea here is so simple it almost sounds funny: a Feature does
something at a certain time.

Each Feature provides a set of functions to be executed at pre-defined
times, or stages.  Each Feature's stage function can have pre/post
requirements to help coordinate what order all the functions get executed
in.

The pre-defined stages are:

  build() -- Build the binary package by executing the embedded build
  script in the NOTES file, populate MANIFEST with TarInfo objects of
  resulting payload.

  build_iter(fname) -- If you want to tweak each file before it gets added
  to the archive, this is the stage you want.

  install() -- Install the package on a system.

  install_iter(fname) -- If you have something special to do that involves
  iterating over all the installed files, this is the stage to use.

  uninstall() -- Uninstall the package from a system.

  uninstall_iter(fname) -- If you have something to do per file during
  uninstall, this is the stage to do it in.

  action -- This stage is special.  It's really a meta-stage of sorts,
  allowing Features to create their own special pseudo-stages.  These
  special action stages can be triggered by explicitly requesting them via
  the --action command line flag.


So for example, when a package is being built, all the SRP main program
has to do is fetch a list of build functions from all the registered
Features (sorted via their pre/post rules), and execute them one by one.

"""
import hashlib
import os
import pickle
import tarfile
import tempfile

import srp

# These lists/maps are populated via calls to register_feature
default_features = []
registered_features = {}
action_map = {}

# The standard list of stages
stage_list = ['build', 'build_iter',
              'install', 'install_iter',
              'uninstall', 'uninstall_iter']


# FIXME: could use collections.namedtuple, derive from tuple myself, or
#        use __slots__ to make this more efficient.  more importantly,
#        this would add enforcement to the data members (i.e., .naem="foo"
#        would be an error instead of creating a new member named naem).
#
class feature_struct:
    """The primary object used for feature registration.  The name and doc
    items are the feature's name and short description.  The default item
    specifies whether this feature should be turned on by default.  The
    info item is a function that returns a string to be included in the
    results of queries of type "info".  The action item is a list of name,
    stage_struct pairs.  The remaining items are stage_struct objects for
    each relevant stage.

    """
    def __init__(self, name=None, doc=None, default=False,
                 build=None, build_iter=None,
                 install=None, install_iter=None,
                 uninstall=None, uninstall_iter=None,
                 action=[], info=None):
        self.name=name
        self.doc=doc
        self.default=default
        self.build=build
        self.build_iter=build_iter
        self.install=install
        self.install_iter=install_iter
        self.uninstall=uninstall
        self.uninstall_iter=uninstall_iter
        self.action=action
        self.info=info


    def __repr__(self):
        s = "feature_struct({name!r}, {doc!r}, {default}"
        tmp = stage_list[:]
        tmp.extend(["action"])
        for x in tmp:
            if getattr(self, x, None) != None:
                # NOTE: We use string += here instead of substitution because
                #       we're trying to embed format strings to be formatted
                #       later...
                s+=", " + x + "={" + x + "}"
        s+=")"
        return s.format(**self.__dict__)


    # FIXME: Do I really need this?  It enforces having a name and doc and at
    #        least one stage_struct...
    def valid(self):
        """Method used to do validity checking on instances"""
        if not (self.name and self.doc):
            return False
        if not (self.build or self.build_iter or self.install
                or self.install_iter or self.uninstall or self.uninstall_iter
                or self.action):
            return False
        return True


class stage_struct:
    """This object is used for feature registration by using an instance to
    populate one of the stage fields of feature_struct.  name is the name
    of the feature as referenced by other features.  func is the function
    to be called during this stage.  pre_reqs is a list of feature names
    that are required to happen prior to this feature's func being called.
    post_reqs is a list of feature names that are required to happen after
    this feature's func (i.e., this feature's func has to happen
    first).

    """
    def __init__(self, name=None, func=None, pre_reqs=[], post_reqs=[]):
        self.name = name
        self.func = func
        self.pre_reqs = pre_reqs
        self.post_reqs = post_reqs
    

    def __repr__(self):
        s = "stage_struct({name!r}, {func!r}"
        for x in ["pre_reqs", "post_reqs"]:
            if getattr(self, x, []) != []:
                # NOTE: We use string += here instead of substitution because
                #       we're trying to embed format strings to be formatted
                #       later...
                s+=", " + x + "={" + x + "}"
        s+=")"
        return s.format(**self.__dict__)


    def __lt__(self, other):
        """The less than method is implemented so we can sort a list of
        instances propperly using our pre_reqs and post_reqs feature
        lists.
        """

        # update pre_reqs and post_reqs for both self and other
        #
        # NOTE: This is done to remove special characters from feature names
        #       for sorting purposes.  For example, a leading ? (e.g.,
        #       ?checksum) indicates that the named features is a required
        #       sort rule IF THE FEATURE HAS EXPLICITLY BEEN ENABLED BY
        #       SOMETHING ELSE (i.e., it's there for sorting, but doesn't
        #       recursively get enabled as a feature).
        pre_reqs = []
        for x in self.pre_reqs:
            if x[0] == "?":
                pre_reqs.append(x[1:])
            else:
                pre_reqs.append(x)

        post_reqs = []
        for x in self.post_reqs:
            if x[0] == "?":
                post_reqs.append(x[1:])
            else:
                post_reqs.append(x)

        for x in other.pre_reqs[:]:
            if x[0] == "?":
                other.pre_reqs.remove(x)
                other.pre_reqs.append(x[1:])

        for x in other.post_reqs[:]:
            if x[0] == "?":
                other.post_reqs.remove(x)
                other.post_reqs.append(x[1:])

        # does self need to come before other
        if self.name in other.pre_reqs:
            # either true or error
            if other.name in pre_reqs or self.name in other.post_reqs:
                raise Exception("circular pre_req dependencies")
            return True
        
        # does other need to come before self
        if other.name in pre_reqs:
            # false or error
            if self.name in other.pre_reqs or other.name in post_reqs:
                raise Exception("circular other pre_req dependencies")
            return False
        
        # does self need to come after other
        if self.name in other.post_reqs:
            # either false or error
            if other.name in post_reqs or self.name in other.pre_reqs:
                raise Exception("circular other post_req dependencies")
            return False
        
        # does other need to come after self
        if other.name in post_reqs:
            # either true or error
            if self.name in other.post_reqs or other.name in pre_reqs:
                raise Exception("circular post_req dependencies")
            return True

        # NOTE: We need to support at least 1 level of indirect deps
        #       (i.e., deps and checksum may not directly relate to each
        #       other, but checksum has to happen after core while deps
        #       has to happen before core).

        # does other have a pre_req that's in our post_reqs
        for x in other.pre_reqs:
            if x in post_reqs:
                return True

        # does other have a post_req that's in our pre_reqs
        for x in other.post_reqs:
            if x in pre_reqs:
                return False

        # NOTE: If we've failed to determine if we're less than, we've
        #       missed something... and this is a lot easier to detect in
        #       the interpreter if we don't return anything...


def register_feature(feature_obj):
    """The registration method for the Feature API.  See documentation for
    features.feature_struct.

    """
    if not feature_obj.valid():
        raise Exception("invalid feature_obj")

    # add the feature to our registered_features dict
    registered_features[feature_obj.name] = feature_obj

    # add any feature-specific actions to our actions_map
    for a in feature_obj.action:
        try:
            action_map[a[0]].append(a[1])
        except:
            action_map[a[0]] = [a[1]]

    # add the feature's name to our default list if specified
    if feature_obj.default:
        default_features.append(feature_obj.name)


def get_function_list(stage, feature_list):
    """Utility function that returns a sorted list of feature stage_struct
    objects for the specified stage.  Each feature's stage_struct object
    is quereied for pre/post requirements and all are added, then the
    resulting list of objects is sorted based on all the pre/post
    requirements.

    """
    retval = []
    for f in feature_list:
        # skip disablers
        if f.startswith("no_"):
            continue
        # get the list of feature funcs required for f
        f_funcs = get_function_list_deps(f, stage)
        # add only new entries from f_funcs
        for x in f_funcs:
            if x not in retval:
                retval.append(x)
    retval.sort()
    return retval


def get_function_list_deps(f, stage, retval=None):
    """Utility function that recursively generates a list of stage_struct
    objects for the specified feature and stage.

    """
    if retval == None:
        retval = []

    # if requested feature is unsupported, the following call will raise an
    # exception.
    try:
        x = getattr(registered_features[f], stage)
    except KeyError:
        print("ERROR: requested unsupported feature: {}".format(f))
        raise

    # feature might not implement a func for this stage
    if not x:
        return retval

    # if f has already been added, we're done
    if x in retval:
        return retval

    # add all f's pre funcs
    for d in x.pre_reqs:
        if not d.startswith("?"):
            get_function_list_deps(d, stage, retval)

    # add all f's post funcs
    for d in x.post_reqs:
        if not d.startswith("?"):
            get_function_list_deps(d, stage, retval)

    # add f
    retval.append(x)

    return retval


def get_stage_map(flags):
    """Utility function that returns a dict of sorted stage lists.  The flags
    argument is a list of features read from the NOTES file.

    """
    retval = {}
    for s in stage_list:
        retval[s] = get_function_list(s, flags)

    return retval


# FIXME: should this be in core.py or features/__init__.py?  could go
#        either way, really, as it's for coordinating the feature funcs to
#        do work per RunTimeParameters...  might move it into features
#        just so it's documentation is alongside the rest of the Features
#        API docs...
#
# FIXME: move get_stage_map, get_function_list, etc, into this class
#
class WorkBag(srp.SrpObject):
    """Toplevel container class for storing all the things being worked on by
    the Feature funcs during our run.  All Feature stage functions should
    refer to the common WorkBag instance at `srp.work'.

    Each high-level operational mode (e.g., build) of srp has its own
    class to handle it's work data:

      build - instance of BuildWork
      install - instance of InstallWork
      uninstall - instance of UninstallWork
      query - instance of QueryWork
      action - instance of ActionWork

    Global Items:

      topdir - The instance-unique temporary working directory that serves
          as the parent directory for all temporary files.  The directory
          itself is created when this class gets instantiated, and is up
          to the user to be deleted (upon successful completion)

    """
    def __init__(self):
        self.build = None
        self.install = None
        self.uninstall = None
        self.query = None
        self.action = None

        self.topdir = tempfile.mkdtemp(prefix="srp-")


class BuildWork(srp.SrpObject):
    """Class holding data for srp.build(), which runs through the build and
    build_iter stages.

    Data:

      notes - Instance of srp.notes.NotesFile.

      manifest - Instance of srp.blob.Manifest (basically a sorted dict)
          used to track files being installed and lots of metadata for
          each one (this is left intentionally vague).

      funcs - Sorted list of stage_struct instances for the build stage.

      iter_funcs - Sorted list of stage_struct instances for the
          build_iter stage.

    """
    def __init__(self):
        with open(srp.params.build.notes, 'rb') as fobj:
            self.notes = srp.notes.NotesFile(fobj)
        
        # FIXME: blob.Manifest with sorted iterator/view?  I seem to think
        #        i didn't do this originally because 1) i was lazy, and 2)
        #        i think it messes with shared memory in
        #        multiprocessing...
        #
        #        was that ever really true?
        #
        self.manifest = srp.blob.Manifest()

        stages = get_stage_map(self.notes.header.features)
        self.funcs = stages["build"]
        self.iter_funcs = stages["build_iter"]

        # add brp section to NOTES instance
        self.notes.brp = srp.notes.NotesBrp()

        # update notes fields with optional command line flags
        self.notes.update_features(srp.params.options)


def verify_sha(tar):
    sha = hashlib.new("sha1")
    for f in tar:
        if f.name != "SHA":
            sha.update(tar.extractfile(f).read())
    x = sha.hexdigest().encode()
    y = tar.extractfile("SHA").read()
    if x != y:
        raise Exception("SHA doesn't match.  Corrupted archive?")
    return x


class InstallWork(srp.SrpObject):
    """Class holding data for srp.install(), which runs through the install and
    install_iter stages.

    Data:

      notes - Instance of srp.notes.NotesFile loaded out of the package.

      prevs - List of previously installed srp.db.InstalledPackage
          instances of the same name.

      blob - Instance of srp.blob.BlobFile loaded out of the package.

      manifest - Instance of srp.blob.Manifest extracted from the BlobFile
          object.

      funcs - Sorted list of stage_struct instances for the install stage.

      iter_funcs - Sorted list of stage_struct instances for the
          install_iter stage.

    """
    def __init__(self):
        # extract required files
        with tarfile.open(srp.params.install.pkg) as p:
            # verify SHA
            from_sha = verify_sha(p)

            # get NOTES
            n_fobj = p.extractfile("NOTES")
            n = pickle.load(n_fobj)
            self.notes = n

            # get BLOB
            #
            # NOTE: We need to actually extract this file as apposed to
            #       just using a file object here.  This is because our C
            #       _blob.extract method needs access to the file on disk
            #       somewhere.
            #
            p.extract("BLOB", srp.work.topdir + "/package")

        # check for previously installed version
        #
        # NOTE: The db lookup method(s) return a list of matches to 1) support
        #       fnmatch queries and 2) support having multiple versions of a
        #       package installed.  We don't need to wory about the 1st case
        #       here, because we're passing in an exact package name, but we
        #       do have to wory about the 2nd case.
        #
        #       Why?  We like to be able to have multiple kernel packages
        #       installed, as they generally don't overlap files (except
        #       firmware, possibly) and it's nice to have multiple kernels
        #       managed via the package manager.
        #
        #       This means we need to iterate over a list of possibly more
        #       than 1 installed version.
        #
        prevs = srp.db.lookup_by_name(n.header.name)
        # make sure upgrading is allowed if needed
        if prevs and not srp.params.install.allow_upgrade:
            raise Exception("Package {} already installed".format(
                n.header.name))

        # check for upgrading to identical version (requires --force)
        for prev in prevs:
            if (prev.notes.header.fullname == n.header.fullname
                and not srp.params.force):
                raise Exception("Package {} already installed, use --force to"
                                " forcefully reinstall or --uninstall and then"
                                " --install".format(n.header.fullname))

        if prevs:
            print("Upgrading to {}".format(n.header.fullname))
        self.prevs = prevs

        # add installed section to NOTES instance
        n.installed = srp.notes.NotesInstalled(from_sha)

        # update NotesFile with host defaults
        n.update_features(srp.features.default_features)

        # update notes fields with optional command line flags
        n.update_features(srp.params.options)

        self.blob = srp.blob.BlobFile.fromfile(srp.work.topdir+"/package/BLOB")

        self.manifest = self.blob.manifest

        stages = get_stage_map(self.notes.header.features)
        self.funcs = stages["install"]
        self.iter_funcs = stages["install_iter"]



# NOTE: We want importing this package to automatically import all .py files in
#       this directory, because that triggers each individual feature's
#       registration code.  So, we do some globbing, manipulation, and then use
#       the __import__ statement here.
#
# NOTE: We do not define __all__, so doing 'from features import *' will ONLY
#       import the API structure and functions (which happens to avoid the
#       circular deps problem when a feature module tries to import * from
#       srp.features)
#
# FIXME: is that still true?
#
from glob import glob
import os
for x in glob("{}/*.py".format(__path__[0])):
    if x == __file__:
        # skip __init__.py
        continue
    # remove leading path
    x = os.path.basename(x)
    # we globbed on *.py, so we know that x ends with ".py"... let's remove it
    x = x[:-3]
    __import__(".".join([__name__, x]))


# clean up our namespace
del glob
del os
del x

# FIXME: move huge ammount of stuff to api.py
