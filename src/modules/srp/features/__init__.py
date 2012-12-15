"""
Library for implementing the SRP Feature API
"""

registered_features = {}


# NOTE: each of the target stages is a tuple of (func, [dep_list])
def register_feature(name,
                     doc,
                     preinst = (None, []),
                     inst = (None, []),
                     postinst = (None, []),
                     preuninst = (None, []),
                     uninst = (None, []),
                     postuninst = (None, [])):
    
    registered_features[name] = {"doc": doc,
                                 "preinst": preinst,
                                 "inst": inst,
                                 "postinst": postinst,
                                 "preuninst": preuninst,
                                 "uninst": uninst,
                                 "postuninst": postuninst}


# NOTE: we can override registered_features by passing in a feature_list
def get_function_list(stage, feature_list=registered_features):
    retval = []
    for f in feature_list:
        # get the list of feature funcs required for f
        f_funcs = get_feature_stage_func_deps_list(f, stage)
        # add only new entries from f_funcs
        for x in f_funcs:
            if x not in retval:
                retval.append(x)
    return retval


def get_feature_stage_func_deps_list(f, stage, retval=[]):
    # if requested feature is unsupported, the following call will raise an
    # exception.
    func, deps = registered_features[f][stage]

    # if f's func has already been added, we're done
    if func in retval:
        return retval

    # add all f's dep funcs
    for d in deps:
        get_feature_stage_func_deps_list(d, stage, retval)

    # add f's func
    retval.append(func)

    return retval
