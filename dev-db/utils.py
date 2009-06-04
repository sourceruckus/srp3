"""utils -
contains some convenience routines for srp2."""

import os
import os.path
import string
import commands
import time
import socket
import random
import md5

import sr


def list_files(node):
    """list_files(dir) -> list of filenames
    returns a recursively generated list of the entire contents
    of the given filesystem node.  the list is sorted.
    """
    retval = []
    #if not is_dir(node) or is_symlink(node):
    if not os.path.isdir(node) or os.path.islink(node):
        #print "not a dir"
        return retval.append(node)
    else:
        list_files_iter(node, retval)
        retval.sort()
        return retval


def list_files_iter(node, retval):
    """list_files_iter()
    do not use, for internal use only
    """
    #recursively traverses a filesystem tree, creating a list of all the files
    #if not is_dir(node) or is_symlink(node):
    if not os.path.isdir(node) or os.path.islink(node):
        return retval.append(node)
    else:
        # let's try keeping track of directories too
        if node not in retval:
            retval.append(node)
        for file in os.listdir(node):
            list_files_iter(node + "/" + file, retval)


def vprint(list):
    """vprint(list)
    takes a list of args to be printed if VERBOSE == 1
    """
    if sr.VERBOSE == 0:
        return
    
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


def md5sum(filename):
    """md5sum(filename) -> md5sum or -1
    takes a filename, returns the md5sum or -1 on error
    """
    vprint("generating md5sum of " + filename)
    try:
        retval = md5.new(file(filename, "rb").read()).hexdigest()
    except:
        retval = -1
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
    if sr.FILE == "" or sr.LDCONFIG == "":
        return 0
    
    if os.path.islink(file):
        file = os.path.realpath(file)
    
    go = sr.FILE + " " + file
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
        f = open(sr.SRP_ROOT_PREFIX + sr.LDSOCONF, "r")
    except:
        vprint("error opening ldpath config file (%s) for reading" % (sr.SRP_ROOT_PREFIX + sr.LDSOCONF))
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
    ldfile = sr.SRP_ROOT_PREFIX + sr.LDSOCONF
            
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
    arch = string.join(arch.split('/'), '-')
    
    os = commands.getoutput("uname -s").lower()
    os = string.join(os.split('/'), '-')
    
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
    sr.TIMER = time.time()


def timer_stop():
    """timer_stop() -> time
    stops our timer and returns elapsed time in seconds
    """
    retval = time.time() - sr.TIMER
    sr.TIMER = 0
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
