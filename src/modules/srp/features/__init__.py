"""
Module implementing the SRP Feature API
"""

registered_features = {}


class stage_struct:
    """This object is used for feature registration.  An instance for each stage
    is passed to register_feature.  name is the name of the feature as
    referenced by other features.  func is the function to be called during this
    stage.  pre_reqs is a list of feature names that are required to happen
    prior to this feature's func being called.  post_reqs is a list of feature
    names that are required to happen after this feature's func (i.e., this
    feature's func has to happen first)."""
    def __init__(self, name=None, func=None, pre_reqs=[], post_reqs=[]):
        self.name = name
        self.func = func
        self.pre_reqs = pre_reqs
        self.post_reqs = post_reqs
    
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


def register_feature(name,
                     doc,
                     build = None,
                     install = None,
                     uninstall = None,
                     action = None):
    """The registration method for the Feature API.  name is the feature's name.
    doc is a short description of the feature.  build, install, uninstall, and
    action are optional stage_struct object that specify an action to be taken
    for their respective stages.  At least one stage is required."""
    
    if not (build or install or uninstall or action):
        raise Exception("at least one stage must be specified")

    registered_features[name] = {"doc": doc,
                                 "build": build,
                                 "install": install,
                                 "uninstall": uninstall,
                                 "action": action}


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
    x = registered_features[f][stage]

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
