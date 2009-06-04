"""utils -
contains some convenience routines for srp2."""

import commands
import inspect
import md5
import os
import os.path
import random
import sha
import socket
import stat
import tarfile
import time
import types
import sys
import subprocess

import config


def list_files(node):
    """list_files(dir) -> list of filenames
    returns a recursively generated list of the entire contents
    of the given filesystem node.  the list is sorted.
    """
    # iter function is only in this wrapper's scope
    def list_files_iter(node, retval):
        if not os.path.isdir(node) or os.path.islink(node):
            retval.append(node)
        else:
            # let's try keeping track of directories too
            if node not in retval:
                retval.append(node)
            for file in os.listdir(node):
                list_files_iter(node + "/" + file, retval)
        return retval
    
    # ok, go
    retval = list_files_iter(node, [])
    retval.sort()
    return retval


def vprint(list):
    """vprint(list)
    takes a list of args to be printed if VERBOSE == 1
    """
    if config.VERBOSE:
        print list


def yesno(string, default):
    """yesno(string, default) -> 1 or 0
    takes a string and a default, prompts the user for input, parses the
    input, returns 1 for yes, 0 for no
    """
    try:
        x = raw_input(string).lower()
    except:
        # don't ever accept if we fail to read from stdin
        return 0
    
    if x == "y" or x == "yes":
        return 1
    elif x == "":
        return default
    return 0


def md5sum(filename, fobj=None):
    """md5sum(filename) -> md5sum or -1
    takes a filename, returns the md5sum or -1 on error
    """
    vprint("generating md5sum of " + filename)
    try:
        if not fobj:
            fobj = open(filename, "rb")
        else:
            fobj.seek(0)
        retval = md5.new(fobj.read()).hexdigest()
    except:
        retval = -1
    return retval


def sha1sum(filename, fobj=None):
    """sha1sum(filename) -> sha1sum or -1
    takes a filename, returns the sha1sum or -1 on error
    """
    vprint("generating sha1sum of " + filename)
    try:
        if not fobj:
            fobj = open(filename, "rb")
        else:
            fobj.seek(0)
        retval = sha.new(fobj.read()).hexdigest()
    except:
        retval = -1
    return retval


def checksum(filename, fobj=None):
    """checksum(filename) -> checksum or -1
    uses the preferred algorithm to generate a checksum
    """
    retval = -1
    if "md5" == config.CHECKSUM:
        retval = md5sum(filename, fobj)
    elif "sha1" == config.CHECKSUM:
        retval = sha1sum(filename, fobj)
    return retval


def is_infofile(file):
    """is_infofile(file) -> 1 or 0
    returns 1 if 'file' is an infofile, 0 otherwise.
    a file is an infofile if it satisfies both of these:
      1) it is not a directory
      2) it's installed in a directory called 'info' (or a subdirectory of it)
    """
    if not os.path.isdir(file) and len(file.split('/info/')) >= 2:
        return 1
    return 0


def is_so(file):
    """is_so(file) -> 1 or 0
    returns 1 if 'file' is a shared object, 0 otherwise.
    also returns 0 if we're not configured for LDCONFIG or we don't have FILE
    returns 0 on other errors as well.
    """
    if config.FILE == "" or config.LDCONFIG == "":
        return 0
    
    if os.path.islink(file):
        file = os.path.realpath(file)
    
    go = config.FILE + " " + file
    vprint(go)
    status = commands.getstatusoutput(go)
    vprint(status)
    if status[0] != 0:
        return 0
    
    if status[1].find("shared object") != -1:
        return 1
    else:
        return 0


def read_ldpath():
    """read_ldpath() -> ldpath
    returns a list of directories for the ldpath
    """
    try:
        f = open(config.SRP_ROOT_PREFIX + config.LDSOCONF, "r")
    except:
        vprint("error opening ldpath config file (%s) for reading" % (config.SRP_ROOT_PREFIX + config.LDSOCONF))
        return []
    
    retval = f.readlines()
    f.close()
    
    # strip out the carriage returns
    for i in retval:
        retval[retval.index(i)] = i.rstrip()
    
    return retval


def write_ldpath(ldpath):
    """write_ldpath(ldpath) -> status
    writes the ldpath to the appropriate config file
    retval: 1 = success, 0 = failure
    """
    ldfile = config.SRP_ROOT_PREFIX + config.LDSOCONF
            
    try:
        if not os.path.exists(os.path.dirname(ldfile)):
            # path to ldfile doesn't exist
            os.makedirs(os.path.dirname(ldfile))
        
        f = open(ldfile, "w")
        for i in ldpath:
            f.write(i + '\n')
        
        f.close()
    except:
        return 0
    return 1


def lookup_deps_hp_ux10(filename):
    env = os.environ.copy()
    env["_HP_DLDOPTS"] = "-ldd"
    p = subprocess.Popen(filename,
                         env=env,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output = p.communicate()[0].split('\n')
    retval = []
    for x in output:
        x = x.strip()
        if not x:
            continue
        x = x.split()[0].strip()
        if x not in retval:
            retval.append(x)
    return retval


def lookup_deps_linux2(filename):
    p = subprocess.Popen(['ldd', filename],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output = p.communicate()[0].split('\n')
    retval = []
    for x in output:
        x = x.strip()
        if not x:
            continue
        x = x.split()[0].strip()
        if x not in retval:
            retval.append(x)
    return retval


def lookup_deps(filename):
    platform = sys.platform.replace('-', '_')
    func = "lookup_deps_%s" % platform
    try:
        func = eval(func)
    except:
        raise Exception("unsupported platform:", sys.platform)
    return func(filename)


def check_for_lib_using_dl(lib):
    """check_for_lib_using_dl(lib) -> True or False
    uses the dl module to check for a library.
    """
    # this only works if sizeof(int) == sizeof(long) == sizeof(char *).
    # SystemError gets thrown on failure.
    import dl
    
    try:
        dl.open(lib)
        return True
    except:
        return False


def check_for_lib_compat(lib):
    """check_for_lib_compat(lib) -> True or False
    fallback lib checker.  tries to search the filesystem for existence of lib
    """
    ldpath_orig = read_ldpath()
    ldpath = []
    
    # strip comments out of ldpath
    for i in ldpath_orig[:]:
        i = i.split('#')[0].strip()
        if i != "":
            ldpath.append(i)
    ldpath = config.LDPATH_DEFAULT + ldpath
    vprint("ldpath: %s" % ldpath)
    vprint("lib: %s" % lib)
    
    for i in ldpath:
        potential = os.path.join("/",
                                 config.SRP_ROOT_PREFIX,
                                 i[1:],
                                 lib)
        vprint("looking for %s" % (potential))
        if os.path.exists(potential):
            vprint("found it!")
            return True
    
    vprint("missing!")
    return False


def format_size(size):
    """format_size(size) -> formatted_size
    takes a size in bytes and returns a size in the most appropriate size range
    """
    scale = 0
    size2 = size
    
    while size2 >= 1024:
        size2 = size2/1024.0
        scale = scale + 1
    
    if scale == 0:
        scale_string = " bytes"
    elif scale == 1:
        scale_string = "k"
    elif scale == 2:
        scale_string = "M"
    elif scale == 3:
        scale_string = "G"
    else:
        scale_string = "G"
        size2 = size2 * pow(2, 10*(scale-3))
    
    return "%.1f%s" % (size2, scale_string)
    

def hosttype():
    """hosttype() -> type
    determines the host type
    """
    arch = commands.getoutput("uname -m").lower()
    #arch = string.join(arch.split('/'), '-')
    arch = '-'.join(arch.split('/'))
    
    os = commands.getoutput("uname -s").lower()
    #os = string.join(os.split('/'), '-')
    os = '-'.join(os.split('/'))
    
    return os + "." + arch


def contact():
    """contact() -> contact
    looks up contact email address
    """
    try:
        email = os.environ['REPLYTO']
    except:
        try:
            email = os.getlogin() + "@" + socket.gethostname()
        except:
            email = "(null)"
    return email


def timestamp_utc():
    """timestamp_utc() -> timestamp
    generates a timestamp string.  uses utc time.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def timestamp_local():
    """timestamp_local() -> timestamp
    generates a timestamp string.  uses local time.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def timer_start():
    """timer_start()
    starts our timer"""
    config.TIMER = time.time()


def timer_stop():
    """timer_stop() -> time
    stops our timer and returns elapsed time in seconds
    """
    retval = time.time() - config.TIMER
    config.TIMER = 0
    return retval


def random_dirname(path):
    """random_dirname(path) -> dirname
    returns a currently non-existing directory name inside path
    retval: dirname
    """
    if not os.path.isdir(path):
        return ""
    
    done = 0
    while not done:
        # generate random filename
        set = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
               'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
               'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
               'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
               'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7',
               '8', '9', '-', '_']
        foo = ""
        while len(foo) <= 25:
            foo = foo + random.choice(set)
        
        # test it out
        foo = path + "/" + foo
        if not os.path.exists(foo):
            done = 1
    return foo


def getsize(file):
    """getsize(file) -> size
    we use this function to calculate installed sizes because python's
    os.path.getsize() follows symbolic links and works recursively...
    retval: size in bytes
    """
    status = commands.getstatusoutput("du -bs " + file)
    if status[0] != 0:
        return 0
    
    if os.path.islink(file) or os.path.isfile(file):
        return int(status[1].split()[0])
    else:
        # it's a directory...
        # how big is an empty directory in this filesystem?
        #os.chdir(file)
        temp = random_dirname(file)
        if not temp:
            return 0
        
        os.mkdir(temp)
        
        status = commands.getstatusoutput("du -bs " + temp)
        if status[0] != 0:
            return 0
        retval = int(status[1].split()[0])
        os.rmdir(temp)
        
        return retval


def any_of_in(x, y):
    """any_of_in(x, y) -> 1 or 0
    iterates over x to determine if any of it's elements are members of y.
    retval: 1 = yes, 0 = no
    """
    retval = 0
    for i in x:
        if i in y:
            retval = 1
    return retval


def remove_duplicates(x):
    """remove_duplicates(x) -> []
    generates a copy of x that contains no duplicates
    retval: x without duplicates
    """
    retval = []
    for i in x:
        if i not in retval:
            retval.append(i)
    return retval


def file_perms(file):
    """file_perms(file) -> perms string
    generates the perms string used by SRP_PERMS option
    retval: mode:uid:gid
    """
    stats = os.lstat(file)
    mode = stats[stat.ST_MODE]
    uid = stats[stat.ST_UID]
    gid = stats[stat.ST_GID]
    retval = "%d:%d:%d" % (mode, uid, gid)
    return retval


def link_target(file):
    """link_target(file) -> linktarget string
    returns the linktarget string used by SRP_LINKTARGET option
    retval: filename of link's target or ""
    """
    retval = ""
    try:
        retval = os.readlink(file)
    except:
        pass
    return retval


def tarball_create_compressed(file, contents, compression, posix, deref):
    """tarball_create_compressed(file, contents, compression) -> status
    creates a tarball using the specified compression model containing contents
    retval: 1 = success, 0 = failure
    """
    mode = "w"
    # first off, check for usage
    if "" == compression:
        pass
    elif "gz" == compression:
        mode += ":gz"
    elif "bz2" == compression:
        mode += ":bz2"
    else:
        return 0
    
    tarfile.posix = posix
    tarfile.dereference = deref
    
    try:
        tar = tarfile.open(file, mode)
        for x in contents:
            tar.add(x)
        tar.close()
    except:
        return 0
    return 1


def tarball_extract_compressed(file, dir, compression, same_owner):
    """tarball_extract_compressed(file, dir, compression) -> status
    extracts a tarball using the specified compression model into dir
    retval: 1 = success, 0 = failure
    """
    mode = "r"
    # first off, check for usage
    if "" == compression:
        pass
    elif "gz" == compression:
        mode += ":gz"
    elif "bz2" == compression:
        mode += ":bz2"
    else:
        return 0
    
    try:
        tar = tarfile.open(file, mode)
        
        for x in tar:
            # don't extract "." because we don't want to change perms of "."
            if x.name == "." or x.name == "./":
                continue
            tar.extract(x, dir)
            if not same_owner:
                f = x.name
                while f != "":
                    os.lchown(os.path.join(dir, f), os.getuid(), os.getgid())
                    f = os.path.dirname(f)
        
        tar.close()
        
    except:
        return 0
    return 1


def tarball_create(file, contents, posix=False, deref=False):
    """tarball_create(file, contents) -> status
    creates a tarball named file containing contents
    retval: 1 = success, 0 = failure
    """
    return tarball_create_compressed(file, contents, "", posix, deref)


def tarball_extract(file, dir, same_owner=True):
    """tarball_extract(file, dir) -> status
    extracts a tarball named file into dir
    retval: 1 = success, 0 = failure
    """
    return tarball_extract_compressed(file, dir, "", same_owner)


def gzball_create(file, contents, posix=False, deref=False):
    """gzball_create(file, contents) -> status
    creates a gzipped tarball named file containing contents
    retval: 1 = success, 0 = failure
    """
    return tarball_create_compressed(file, contents, "gz", posix, deref)


def gzball_extract(file, dir, same_owner=True):
    """gzball_extract(file, dir) -> status
    extracts a gzipped tarball named file into dir
    retval: 1 = success, 0 = failure
    """
    return tarball_extract_compressed(file, dir, "gz", same_owner)


def bz2ball_create(file, contents, posix=False, deref=False):
    """bz2ball_create(file, contents) -> status
    creates a bz2ball named file containing contents
    retval: 1 = success, 0 = failure
    """
    return tarball_create_compressed(file, contents, "bz2", posix, deref)


def bz2ball_extract(file, dir, same_owner=True):
    """bz2ball_extract(file, dir) -> status
    extracts a bz2ball named file into dir
    retval: 1 = success, 0 = failure
    """
    return tarball_extract_compressed(file, dir, "bz2", same_owner)


def compat_unescaper(buffer):
    """compat_unescaper(buffer) -> buffer
    eats up '\' chars used to escape things out in old NOTES files (pre 2.2.7)
    """
    retval = []
    buffer = " " + buffer + " "
    num = 0
    
    for i in range(len(buffer))[1:-1]:
        #print "%s [%s] %s" % (buffer[i-1], buffer[i], buffer[i+1])
        
        # these are the things we used to have to escape out
        used_to_escape = ["\"",
                          "'",
                          "`",
                          "$",
                          "\n"]
        
        # is it an escape? (that we care about!)
        if "\\" == buffer[i] and buffer[i+1] in used_to_escape:
            # is it the first one?
            if "\\" != buffer[i-1]:
                num += 1
            # is it the last one
            elif "\\" != buffer[i+1]:
                retval.append("".ljust(num/2).replace(" ", "\\"))
                num = 0
            else:
                num += 1
        else:
            retval.append(buffer[i])
    
    return "".join(retval)


def obj_info(object):
    header_len = 60
    
    if not hasattr(object, "__dict__"):
        print object
        return
    
    print (" %s " % object).center(header_len, '-')
    for x in object.__dict__:
        print "%s = %s" % (x, object.__dict__[x])
    print "".center(60, '-')


class transparent_decorator(object):
    """This function decorator class represents a decorator generator with
    overridable pre/post decoration functions.  Its intended to be used to
    generate function decorators that create decorated methods with the same
    function signature as the original un-decorated method.
    """
    
    def __init__(self, dec):
        self.__dec = dec
    
    def __call__(self, func):
        return self.__decorate(func)
    
    def __predecorate__(self, func):
        pass
    
    def __postdecorate__(self, func):
        return func
    
    def __decorate(self, func):
        # call __predecorate__
        try:
            self.__predecorate__(func)
        except Exception, e:
            print "WARNING: __predecorate__ failed! %s" % e
            return func
        
        # inspect func to determine its function signature
        args, varargs, varkw, defaults = inspect.getargspec(func)
        defstring = inspect.formatargspec(args, varargs, varkw, defaults)[1:-1]
        callstring = inspect.formatargspec(args, varargs, varkw, defaults,
                                           formatvalue=lambda x: "")[1:-1]
        
        # create an unnamed function with the appropriate signature
        src = "lambda %s: __dec__(__func__, %s)" % (defstring, callstring)
        retval = eval(src, dict(__dec__=self.__dec, __func__=func))
        
        # clone function object members
        retval.__name__ = func.__name__
        retval.__doc__ = func.__doc__
        retval.__dict__ = func.__dict__
        retval.__module__ = func.__module__
        
        # call __postdecorate__
        try:
            retval = self.__postdecorate__(retval)
        except Exception, e:
            print "WARNING: __postdecorate__ failed! %s" % e
            return func
        
        return retval


def one_time_decorator(tag):
    """This function decorator overrides the __predecorate__ and
    __postdecorate__ methods of a transparent_decorator instance in order keep
    decorated function decorators from being able to decorate a function more
    than once.
    """
    
    def tag_check(func, args={'tag': tag}):
        #print "::tag_check::"
        tag = args['tag']
        #print "tag: %s" % tag
        
        # check for decorated_with_x attribute
        try:
            temp = func.__getattribute__("__decorated_with_%s" % tag)
        except:
            temp = False
        if temp:
            raise Exception("already decorated with '%s'" % tag)
    
    def tag_set(func, args={'tag': tag}):
        #print "::tag_set::"
        tag = args['tag']
        #print "tag: %s" % tag
        
        retval = func
        # set decorated_with_x attribute
        retval.__setattr__("__decorated_with_%s" % tag, True)
        return retval
        
    def aux(func):
        # initial decoration
        retval = transparent_decorator(func)
        
        # setup pre/post decoration methods
        retval.__predecorate__ = tag_check
        retval.__postdecorate__ = tag_set
        
        return retval
    
    return aux


@one_time_decorator("voodoo")
def voodoo(func, *__args, **__kw):
    print "voodoo"
    return func(*__args, **__kw)


def tracedmethod(header):
    def call(func, *__args, **__kw):
        print "%s: entering %s" % (header, func)
        try:
            return func(*__args, **__kw)
        finally:
            print "%s: exiting %s" % (header, func)
    
    return one_time_decorator("tracedmethod")(call)


def writemethod(dir):
    def call(func, *__args, **__kw):
        # check to see if we have write permission in dir
        if not os.access(dir, os.W_OK):
            err = "requested operation requires write permission in directory"
            err += " '%s'" % dir
            raise Exception(err)
        return func(*__args, **__kw)
    
    return transparent_decorator(call)


@one_time_decorator("ruckuswritemethod")
@writemethod(config.RUCKUS)
def ruckuswritemethod(func, *__args, **__kw):
    return func(*__args, **__kw)


@one_time_decorator("readonlyattributes")
def readonlyattributes(func, *__args, **__kw):
    
    def addaccessmethods(self):
        for x in self.__dict__:
            # private data names are actually _classname__name
            prefix = "_%s__" % self.__class__.__name__
            if x.startswith(prefix):
                
                prop = x.split(prefix)[-1]

                # this should only be done once
                try:
                    getattr(self.__class__, prop)
                    # property (or something else with its desired name)
                    # already exists.  skip it.
                    continue
                except:
                    pass

                if config.DEBUG:
                    print "adding read-only access method for __%s" % prop

                # dynamically create fget function
                f_code = "fget = lambda a: getattr(a, '%s')" % x
                exec f_code in globals(), locals()

                # we'll provide a semi-helpful docstring
                doc = "read-only attribute for __%s" % prop

                # inject the property into the class definition
                setattr(self.__class__, prop, property(fget=fget, doc=doc))
                
    retval = func(*__args, **__kw)
    addaccessmethods(__args[0])


class autodec_class(type):
    """
    this metaclass automatically decorates all a classes callable functions
    with a bunch of decorators.
    """

    def __init__(cls, name, bases, dict):
        fullclassname = "%s.%s" % (cls.__module__, name)
        if config.DEBUG:
            print "auto-decorating class: %s" % fullclassname
        
        # create list of standard decorators
        decs = []
        
        # decorate all functions in dict
        for x in dict.items():
            f_name, f_obj = x
            if type(f_obj) == types.FunctionType:
                # decorate with @tracedmethod, which takes an argument
                #header = "%s.%s" % (fullclassname, f_name)
                if config.DEBUG:
                    print "  tracedmethod('%s')(%s)" % (fullclassname, f_name)
                f_obj = tracedmethod(fullclassname)(f_obj)
                
                # decorate with standard decorators
                for dec in decs:
                    if config.DEBUG:
                        print "  %s(%s)" % (dec.__name__, f_name)
                    f_obj = dec(f_obj)

                # decorate __init__ with readonlyattributes
                if f_name == "__init__":
                    if config.DEBUG:
                        print "  readonlyattributes(%s)" % f_name
                    f_obj = readonlyattributes(f_obj)

                # replace the original class' method with the decorated one
                setattr(cls, f_name, f_obj)


class base_obj(object):
    
    __metaclass__ = autodec_class

    #__slots__ = []
    
    def info(self):
        """
        this debugging function prints out all the data members of any derived
        class.
        """
        if '__slots__' in dir(self):
            iter_target = []
            #print self.__class__
            #print self.__class__.__bases__
            for b in self.__class__.__bases__:
                if '__slots__' in dir(b):
                    iter_target.extend(b.__slots__)
                #else:
                #    #print b.__dict__
                #    for key, value in b.__dict__.items():
                #        print key, type(value)
                #    #iter_target.extend(b.__dict__)
            iter_target.extend(self.__slots__)
        else:
            iter_target = self.__dict__.keys()
            iter_target.sort()

        header = "---------- %s ----------" % self.__class__
        footer = ''
        for x in header: footer += '-'

        print header
        for x in iter_target:
            print "%s: %s" % (x, self.__getattribute__(x))
        print footer
