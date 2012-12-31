"""Module implementing the SRP Feature API.

The SRP Feature API is used to make the package manager as flexible and
extensible as possible.  This API provides programmers with an easy way to add
new features without having to rewrite massive blocks of nasty code and
introduce unseemly regressions (see SRP v2, regrettably).

The basic idea here is so simple it almost sounds funny: a Feature does
something at a certain time.

Each Feature provides a set of functions to be executed at pre-defined times, or
stages.  Each Feature's stage function can have pre/post requirements to help
coordinate what order all the functions get executed in.

The pre-defined stages are:

  create -- Creating a source package from a NOTES file, source tarball, and
  possibly other files (e.g., patches, extra sources)

  build -- Build the binary package by executing the embedded build script in
  the NOTES file, tar up the resulting payload.

  install -- Install the package on a system.

  uninstall -- Uninstall the package from a system.

  action -- This stage is special.  It's really a meta-stage of sorts, allowing
  Features to create their own special pseudo-stages.  These special action
  stages can be triggered by explicitly requesting them via the --action command
  line flag.


So for example, when a package is being built, all the SRP main program has to
do is fetch a list of create functions from all the registered Features (sorted
via their pre/post rules), and execute them one by one.
"""

registered_features = {}


class feature_struct:
    """The primary object used for feature registration.  The name and doc items
    are the feature's name and short description.  The action item is a list of
    name, stage_struct pairs.  The remaining items are stage_struct objects for
    each relevant stage."""
    def __init__(self, name=None, doc=None, create=None, build=None,
                 install=None, uninstall=None, action=[]):
        self.name=name
        self.doc=doc
        self.create=create
        self.build=build
        self.install=install
        self.uninstall=uninstall
        self.action=action


    def __repr__(self):
        s = "feature_struct({name!r}, {doc!r}"
        for x in ["create", "build", "install", "uninstall", "action"]:
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
        if not (self.create or self.build or self.install or self.uninstall
                or self.action):
            return False
        return True


class stage_struct:
    """This object is used for feature registration by using an instance to
    populate one of the stage fields of feature_struct.  name is the name of the
    feature as referenced by other features.  func is the function to be called
    during this stage.  pre_reqs is a list of feature names that are required to
    happen prior to this feature's func being called.  post_reqs is a list of
    feature names that are required to happen after this feature's func (i.e.,
    this feature's func has to happen first)."""
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
        instances propperly using our pre_reqs and post_reqs feature lists."""
        # does self need to come before other
        if self.name in other.pre_reqs:
            # either true or error
            if other.name in self.pre_reqs or self.name in other.post_reqs:
                raise Exception("circular pre_req dependencies")
            return True
        
        # does other need to come before self
        if other.name in self.pre_reqs:
            # false or error
            if self.name in other.pre_reqs or other.name in self.post_reqs:
                raise Exception("circular other pre_req dependencies")
            return False
        
        # does self need to come after other
        if self.name in other.post_reqs:
            # either false or error
            if other.name in self.post_reqs or self.name in other.pre_reqs:
                raise Exception("circular other post_req dependencies")
            return False
        
        # does other need to come after self
        if other.name in self.post_reqs:
            # either true or error
            if self.name in other.post_reqs or other.name in self.pre_reqs:
                raise Exception("circular post_req dependencies")
            return True


def register_feature(feature_obj):
    """The registration method for the Feature API."""
    if not feature_obj.valid():
        raise Exception("invalid feature_obj")

    registered_features[feature_obj.name] = feature_obj


# FIXME: haven't decided yet how we're really specifying features (i.e., is
#        registered featuers all the ones supported while feature_list arg is
#        all the ones specified in the NOTES file?), for now we can override
#        registered_features by passing in a feature_list
def get_function_list(stage, feature_list=None):
    """Utility function that returns a sorted list of feature stage_struct
    objects for the specified stage.  Each feature's stage_struct object is
    quereied for pre/post requirements and all are added, then the resulting
    list of objects is sorted based on all the pre/post requirements."""
    if feature_list == None:
        feature_list = registered_features.keys()
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


def get_function_list_deps(f, stage, retval=[]):
    """Utility function that recursively generates a list of stage_struct object
    for the specified feature and stage."""
    # if requested feature is unsupported, the following call will raise an
    # exception.
    x = getattr(registered_features[f], stage)

    # if f has already been added, we're done
    if x in retval:
        return retval

    # add all f's pre funcs
    for d in x.pre_reqs:
        get_function_list_deps(d, stage, retval)

    # add all f's post funcs
    for d in x.post_reqs:
        get_function_list_deps(d, stage, retval)

    # add f
    retval.append(x)

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
