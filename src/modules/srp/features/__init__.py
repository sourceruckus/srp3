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

  create(work) -- Creating a source package from a NOTES file, source
  tarball, and possibly other files (e.g., patches, extra sources).

  build(work) -- Build the binary package by executing the embedded build
  script in the NOTES file, create TarInfo list of resulting payload.

  build_iter(work, fname) -- If you want to tweak each file before it gets
  added to the archive, this is the stage you want.

  install(work) -- Install the package on a system.

  install_iter(work, fname) -- If you have something special to do that
  involves iterating over all the installed files, this is the stage to use.

  uninstall(work) -- Uninstall the package from a system.

  uninstall_iter(work, fname) -- If you have something to do per file during
  uninstall, this is the stage to do it in.

  action -- This stage is special.  It's really a meta-stage of sorts,
  allowing Features to create their own special pseudo-stages.  These
  special action stages can be triggered by explicitly requesting them via
  the --action command line flag.


So for example, when a package is being built, all the SRP main program
has to do is fetch a list of create functions from all the registered
Features (sorted via their pre/post rules), and execute them one by one.

"""

# These lists/maps are populated via calls to register_feature
default_features = []
registered_features = {}
action_map = {}

# The standard list of stages
stage_list = ['create',
              'build', 'build_iter',
              'install', 'install_iter',
              'uninstall', 'uninstall_iter']


class feature_struct:
    """The primary object used for feature registration.  The name and doc
    items are the feature's name and short description.  The default item
    specifies whether this feature should be turned on by default.  The
    action item is a list of name, stage_struct pairs.  The remaining
    items are stage_struct objects for each relevant stage.

    """
    def __init__(self, name=None, doc=None, default=False,
                 create=None,
                 build=None, build_iter=None,
                 install=None, install_iter=None,
                 uninstall=None, uninstall_iter=None,
                 action=[]):
        self.name=name
        self.doc=doc
        self.default=default
        self.create=create
        self.build=build
        self.build_iter=build_iter
        self.install=install
        self.install_iter=install_iter
        self.uninstall=uninstall
        self.uninstall_iter=uninstall_iter
        self.action=action


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
        if not (self.create or self.build or self.build_iter or self.install
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
    """The registration method for the Feature API."""
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



# NOTE: We want importing this package to automatically import all .py files in
#       this directory, because that triggers each individual feature's
#       registration code.  So, we do some globbing, manipulation, and then use
#       the __import__ statement here.
#
# NOTE: We do not define __all__, so doing 'from features import *' will ONLY
#       import the API structure and functions (which happens to avoid the
#       circular deps problem when a feature module tries to import * from
#       srp.features)
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
