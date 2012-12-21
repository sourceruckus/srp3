"""
Library for implementing the SRP Feature API
"""

registered_features = {}


class stage_struct:
    def __init__(self, name=None, func=None, pre_reqs=[], post_reqs=[]):
        self.name = name
        self.func = func
        self.pre_reqs = pre_reqs
        self.post_reqs = post_reqs
    
    def __eq__(self, other):
        return NotImplemented
    
    def __ne__(self, other):
        return NotImplemented
    
    def __ge__(self, other):
        return NotImplemented
    
    def __le__(self, other):
        return NotImplemented
    
    def __lt__(self, other):
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
    
    def __gt__(self, other):
        retval = self.__lt__(other)
        if retval == True:
            return False
        elif retval == False:
            return True
        else:
            # retval must be None?
            return retval



#x = stage_struct("tf")
#y = stage_struct("stat", None, ["tf"])
#z = stage_struct("foo", None, ["tf"], ["stat"])


#def cmp(a, b):
    # does a need b to come first (i.e., is b a pre_req of a)
    #   ret 1
    # does b need a to come first
    #   ret -1
    #
    # so neither one require the other to come first
    #
    # does a need b to come later (i.e., is b a post_req of a)
    #   ret -1
    # does b need a to come later
    #   ret 1
    #
    # ret 0
    #
    # we should make sure that the pre/post rules don't conlfict and throw an
    # error if they do...
    
    

def register_feature(name,
                     doc,
                     build = None,
                     inst = None,
                     uninst = None,
                     action = None):
    
    registered_features[name] = {"doc": doc,
                                 "build": build,
                                 "inst": inst,
                                 "uninst": uninst,
                                 "action": action}


# NOTE: we can override registered_features by passing in a feature_list
def get_function_list(stage, feature_list=None):
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
