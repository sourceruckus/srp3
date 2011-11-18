""" Library for implementing the SRP Feature API """

registered_features = {}

def register_feature(name,
                     doc,
                     preinst = None,
                     inst = None,
                     postinst = None,
                     preuninst = None,
                     uninst = None,
                     postuninst = None):
    
    registered_features[name] = {"name": name,
                                 "doc": doc,
                                 "preinst": preinst,
                                 "inst": inst,
                                 "postinst": postinst,
                                 "preuninst": preuninst,
                                 "uninst": uninst,
                                 "postuninst": postuninst}


def get_function_list(stage, feature_list):
    retval = []
    for x in feature_list:
        retval.extend(get_feature_stage_func_deps_list(x, stage))
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
