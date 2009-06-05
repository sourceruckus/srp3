"""prepostlib
"""

import new
import os.path
import sys
import types

import config
import utils

import deprecated.sr


@utils.tracedmethod("srp.prepostlib")
def init(file_p):
    """create prepostlib instance(s). we will attempt to use the latest
    and greatest, but fall back to the older deprecated class as a
    last resort
    """
    retval_p = None
    tried = []
    to_try = [v3, v2]
    for x in to_try:
        try:
            retval_p = x(file_p)
            break
        except Exception, e:
            tried.append("%s (%s)" % (x, e))
    if retval_p == None:
        err = "Failed to create PREPOSTLIB instace(s): %s" % ", ".join(tried)
        raise Exception(err)
    return retval_p


class v3(utils.base_obj):

    standard_funcs = ["prebuild",
                      "postbuild",
                      "preinstall",
                      "postinstall",
                      "preuninstall",
                      "postuninstall"]

    def __init__(self, file_p=None):
        try:
            # create a new module
            #self.__prepost__ = new.module("prepost")

            if file_p:
                # execute the provided code in the new module's __dict__
                exec file_p.read() in self.__dict__
            
            # add missing standard functions
            print "adding undefined methods to prepostlib:"
            for x in self.standard_funcs:
                if not hasattr(self, x):
                    print "  %s" % x
                    setattr(self, x, lambda : None)
                    getattr(self, x).__name__ = x
            
            # apply decorators
            print "decorating prepostlib methods:"
            for x in self.__dict__.items():
                f_name, f_obj = x
                if type(f_obj) == types.FunctionType:
                    header = "__prepost__"
                    print "  utils.tracedmethod('%s')(%s)" % (header, f_name)
                    f_obj = utils.tracedmethod(header)(f_obj)
                    setattr(self, f_name, f_obj)
            
        except Exception, e:
            temp = "Failed to import package's prepostlib module:"
            temp += " %s" % e
            raise Exception(temp)


class v2(v3):
    
    def __init__(self, file_p=None):
        path_deprecated = [os.path.join(config.LIBDIR, "deprecated"),
                           os.path.join(config.LIBDIR_REL, "deprecated")]
        sys.path.extend(path_deprecated)
        try:
            # do v3 initialization
            v3.__init__(self, file_p)

            # wrap up v2 prepostlib methods so they can be called with no args
            # NOTE: this will break any v2 package with a prepostlib function
            #       that actually used the passed in package object. i never
            #       should have passed in an internal data structure... and it
            #       really shouldn't ever be necesary.
            print "removing arguments from v2 prepostlib methods:"
            for x in self.__dict__.items():
                f_name, f_obj = x
                if type(f_obj) == types.FunctionType:
                    #print "foo:", x
                    #print f_obj.func_code.co_argcount
                    #if f_obj.func_code.co_argcount:
                    print "  %s" % f_name
                    setattr(self, "%s_v2" % f_name, f_obj)
                    f_old = getattr(self, "%s_v2" % f_name)
                    print f_old
                    #f_new = lambda : f_old(None)
                    def f_new():
                        f_v2 = f_old
                        print dir()
                        return f_v2(None)
                    #f_new = lambda : __dict__['f_v2'](None)
                    print f_new
                    f_new.__name__ = f_name
                    f_new.f_v2 = f_old
                    print f_new
                    setattr(self, f_name, f_new)
                    
        finally:
            for x in path_deprecated:
                sys.path.remove(x)
