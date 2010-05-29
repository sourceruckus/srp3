"""prepostlib
"""

import os
import sys
import types
import tempfile
import random

import config
import utils

import deprecated.sr


class v2_wrapper(utils.base_obj):
    def __init__(self, file_p):
        """this wrapper class shouldn't be used, except to initalize a basic
        v2 prepostlib file to translate into a v3 instance
        """
        if file_p:
            file_p.seek(0)
            self.name = file_p.name
            self.lines = file_p.read().split('\n')
        else:
            self.name = "PREPOSTLIB_%s.py" % "".join(random.sample(chars, 5))
            self.lines = []


    def create_v3_files(self):
        """returns a list of name, fobj pairs
        """
        retval = []

        path_deprecated = [os.path.join(config.LIBDIR, "deprecated"),
                           os.path.join(config.LIBDIR_REL, "deprecated")]

        header = ["import sys",
                  "import os",
                  "import srp.config",
                  "path_deprecated = [os.path.join(srp.config.LIBDIR, \"deprecated\"),",
                  "                   os.path.join(srp.config.LIBDIR_REL, \"deprecated\")]",
                  "sys.path.extend(path_deprecated)",
                  ""]

        new_lines = header

        for line in self.lines:
            if line.startswith("def"):
                print "LINE: %s" % line
                fname = line.split('(')[0].split()[-1]
                print "FNAME: %s" % fname
                arg = line.split('(')[-1].split(')')[0]
                print "ARG: %s" % arg
                new_lines.extend(["def %s():" % fname,
                                  "    %s_v2(None)" % fname,
                                  "",
                                  "def %s_v2(%s):" % (fname, arg)])
            else:
                new_lines.append(line)
                
        print "--- new_lines ---"
        print "\n".join(new_lines)
        print "--- /new_lines ---"

        x = tempfile.NamedTemporaryFile(mode="w+")
        x.write("\n".join(new_lines))
        x.seek(0)
        name = os.path.basename(self.name)
        retval.append([name, x])

        return retval



class v3(utils.base_obj):

    standard_funcs = ["prebuild",
                      "postbuild",
                      "preinstall",
                      "postinstall",
                      "preuninstall",
                      "postuninstall"]

    def __init__(self, file_p=None):
        try:
            if file_p:
                # execute the provided code in the new module's __dict__
                exec file_p.read() in self.__dict__
                file_p.seek(0)
                print file_p.read()
            
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


# NOT QUITE DEAD YET.  but should probably be removed shortly...
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

        except Exception, e:
            temp = "Failed to import package's prepostlib module:"
            temp += " %s" % e
            raise Exception(temp)
                    
        finally:
            for x in path_deprecated:
                sys.path.remove(x)
