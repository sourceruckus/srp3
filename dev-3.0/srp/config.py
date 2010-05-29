"""config -
this is the main source ruckus python library.
it contains important internal variables."""

import os
import os.path


# the current version of srp
#VERSION = "__VERSION__"
VERSION = "3.0.0"

# this is used to install into another rootfs
# example: you've booted up into source ruckus linux 3.0 and you
# want to install into your redhat rootfs which is mounted on
# /mnt/rh_root...  you just change SRP_ROOT_PREFIX to /mnt/rh_root
# and everything is taken care of.
try:
    SRP_ROOT_PREFIX=os.environ['SRP_ROOT_PREFIX']
except:
    SRP_ROOT_PREFIX = ""


#LIBDIR_REL = "__LIBDIR__"
#LIBDIR_REL = "/usr/lib/srp"
LIBDIR_REL = "/home/mike/src/git/srp3/dev-3.0/srp"
LIBDIR = os.path.join(os.sep, SRP_ROOT_PREFIX, LIBDIR_REL[1:])

#RUCKUS_REL = "__RUCKUS__"
RUCKUS_REL = "/usr/src/ruckus"
RUCKUS = os.path.join(os.sep, SRP_ROOT_PREFIX, RUCKUS_REL[1:])

# full path to the srp lock file
#LOCK_REL = "__LOCK__"
LOCK_REL = "lock"
LOCK = os.path.join(RUCKUS, LOCK_REL)

# where is the ldconfig command?
#LDCONFIG = "__LDCONFIG__"
LDCONFIG = "/sbin/ldconfig"

# the ld config file
#LDSOCONF = "__LDSOCONF__"
LDSOCONF = "/etc/ld.so.conf"

# implicit ldpath entries
#LDPATH_DEFAULT = __LDPATH_DEFAULT__
LDPATH_DEFAULT = ['/lib', '/usr/lib', '/usr/local/lib']

# what are the infofile directory files?
#INFOFILEDIRS = __INFOFILEDIRS__
INFOFILEDIRS = ["/usr/share/info/dir",
                "/usr/local/share/info/dir",
                "/etc/info-dir"]

# what is the preferred checksum algorithm? (sha1 or md5)
#CHECKSUM = "__CHECKSUM__"
CHECKSUM = "sha1"

# default SRP_FLAGS
#DEFAULT_FLAGS = __DEFAULT_FLAGS__
DEFAULT_FLAGS = ["SRP_UPGRADABLE",
                 "SRP_CHECKSUM",
                 "SRP_PERMS",
                 "SRP_LINKTARGET",
                 "SRP_REPAIRABLE"]

# this is the search path for dependent executables
#EXEC_PATH = __EXEC_PATH__
EXEC_PATH = ["/bin",
             "/sbin",
             "/usr/bin",
             "/usr/sbin",
             "/usr/local/bin",
             "/usr/local/sbin"]

# srp will NEVER remove these dirs when uninstalling a package
#PERM_DIRS = __PERM_DIRS__
PERM_DIRS = ["/",
             "/bin",
             "/boot",
             "/dev",
             "/dev/pts",
             "/etc",
             "/home",
             "/lib",
             "/mnt",
             "/proc",
             "/root",
             "/sbin",
             "/tmp",
             "/var",
             "/opt", 
             "/usr",
             "/usr/bin",
             "/usr/etc",
             "/usr/include",
             "/usr/lib",
             "/usr/man",
             "/usr/man/man1",
             "/usr/man/man2",
             "/usr/man/man3",
             "/usr/man/man4",
             "/usr/man/man5",
             "/usr/man/man6",
             "/usr/man/man7",
             "/usr/man/man8",
             "/usr/sbin",
             "/usr/share",
             "/usr/src",
             "/usr/tmp",
             "/usr/var",
             "/usr/share/man",
             "/usr/share/doc",
             "/usr/share/info",
             "/usr/share/dict",
             "/usr/share/locale",
             "/usr/share/nls",
             "/usr/share/misc",
             "/usr/share/terminfo",
             "/usr/share/zoneifo",
             "/usr/share/man/man1",
             "/usr/share/man/man2",
             "/usr/share/man/man3",
             "/usr/share/man/man4",
             "/usr/share/man/man5",
             "/usr/share/man/man6",
             "/usr/share/man/man7",
             "/usr/share/man/man8",
             "/usr/local",
             "/usr/local/bin",
             "/usr/local/etc",
             "/usr/local/include",
             "/usr/local/lib",
             "/usr/local/sbin",
             "/usr/local/share",
             "/usr/local/src",
             "/usr/local/tmp",
             "/usr/local/var",
             "/usr/local/share/man",
             "/usr/local/share/doc",
             "/usr/local/share/info",
             "/usr/local/share/dict",
             "/usr/local/share/locale",
             "/usr/local/share/nls",
             "/usr/local/share/misc",
             "/usr/local/share/terminfo",
             "/usr/local/share/zoneifo",
             "/usr/local/share/man/man1",
             "/usr/local/share/man/man2",
             "/usr/local/share/man/man3",
             "/usr/local/share/man/man4",
             "/usr/local/share/man/man5",
             "/usr/local/share/man/man6",
             "/usr/local/share/man/man7",
             "/usr/local/share/man/man8", 
             "/var/lock",
             "/var/log",
             "/var/mail",
             "/var/run",
             "/var/spool",
             "/var/tmp",
             "/opt/bin",
             "/opt/doc",
             "/opt/include",
             "/opt/info",
             "/opt/lib",
             "/opt/man",
             "/opt/man/man1",
             "/opt/man/man2",
             "/opt/man/man3",
             "/opt/man/man4",
             "/opt/man/man5",
             "/opt/man/man6",
             "/opt/man/man7",
             "/opt/man/man8",
             "/etc/init.d",
             "/etc/rc.d",
             "/etc/rc0.d",
             "/etc/rc1.d",
             "/etc/rc2.d",
             "/etc/rc3.d",
             "/etc/rc4.d",
             "/etc/rc5.d",
             "/etc/rc6.d",
             "/etc/rc.d/init.d",
             "/etc/rc.d/rc0.d",
             "/etc/rc.d/rc1.d",
             "/etc/rc.d/rc2.d",
             "/etc/rc.d/rc3.d",
             "/etc/rc.d/rc4.d",
             "/etc/rc.d/rc5.d",
             "/etc/rc.d/rc6.d",
             "/scrap"]



#------------------------- WARNING -------------------------
# if you change any of these variables, you risk breaking packages.
# bad bad.  don't do it.

# name of NOTES file
NOTES = "NOTES"

# BLOB compression ('bz2', 'gz', or '')
BLOB_COMPRESSION = "bz2"

# name of BLOB file
BLOB = "srpblob.tar.%s" % BLOB_COMPRESSION

# name of BRP pickle file
BRP_PICKLE = "brp.pkl"

# list of directories needed inside RUCKUS
RUCKUS_DIRS = ["build",
               "brp",
               "installed",
               "package",
               "tmp"]

# list of supported SRP_FLAGS
SUPPORTED_FLAGS = ["SRP_DUMMYFLAG",
                   "SRP_UPGRADABLE",
                   "SRP_NO_COMPILE",
                   "SRP_CANT_FOOL",
                   "SRP_MD5SUM",
                   "SRP_SHA1SUM",
                   "SRP_CHECKSUM",
                   "SRP_INSTALLINFO",
                   "SRP_LDCONFIG",
                   "SRP_ARCH_IND",
                   "SRP_OS_IND",
                   "SRP_DEPS_PROG",
                   "SRP_DEPS_SRP",
                   "SRP_PREPOSTLIB",
                   "SRP_PERMS",
                   "SRP_LINKTARGET",
                   "SRP_OWNEROVERRIDE",
                   "SRP_CHAIN",
                   "SRP_NO_UPGRADE",
                   "SRP_NO_CHECKSUM",
                   "SRP_NO_PERMS",
                   "SRP_NO_LINKTARGET",
                   "SRP_NO_INSTALLINFO",
                   "SRP_NO_LDCONFIG"]

#-----------------------------------------------------------



# insert SRP_ROOT_PREFIX in EXEC_PATH entries
for x in EXEC_PATH[:]:
    EXEC_PATH.remove(x)
    EXEC_PATH.append(os.path.join(os.sep, SRP_ROOT_PREFIX, x[1:]))

# insert SRP_ROOT_PREFIX in PERM_DIRS entries
for x in PERM_DIRS[:]:
    PERM_DIRS.remove(x)
    PERM_DIRS.append(os.path.join(os.sep, SRP_ROOT_PREFIX, x[1:]))

# add RUCKUS dirs to PERM_DIRS
for x in RUCKUS_DIRS:
    PERM_DIRS.append(os.path.join(os.sep, SRP_ROOT_PREFIX, x))

# add SRP_ROOT_REIX to PERM_DIRS, if it's set
if SRP_ROOT_PREFIX:
    PERM_DIRS.append(SRP_ROOT_PREFIX)

# remove temporary variables from namespace
del x


#-- run-time variables --------------------------------------------------------

# for deugging SRP itself
DEBUG = True

# for debugging a particular package
VERBOSE = False

# used by utils.timer_{start,stop}
TIMER = 0

READONLY = False
UPGRADE = False
LISTFILES = False
LISTFLAGS = False
TALLY = False
PRETTY = True
PERSISTENT = False
