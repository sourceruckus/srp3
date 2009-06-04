"""sr -
this is the main source ruckus python library.
it contains important internal variables."""

import os


# the current version of srp
VERSION = "__VERSIONSTRING__"

# this is used to install into another rootfs
# example: you've booted up into source ruckus linux 3.0 and you
# want to install into your redhat rootfs which is mounted on
# /mnt/rh_root...  you just change SRP_ROOT_PREFIX to /mnt/rh_root
# and everything is taken care of.
try:
    SRP_ROOT_PREFIX=os.environ['SRP_ROOT_PREFIX']
except:
    SRP_ROOT_PREFIX = "__SRP_ROOT_PREFIX__"


LIBDIR_REL = "__LIBDIR__"
LIBDIR = os.path.join(os.sep, SRP_ROOT_PREFIX, LIBDIR_REL[1:])

RUCKUS_REL = "__RUCKUS__"
RUCKUS = os.path.join(os.sep, SRP_ROOT_PREFIX, RUCKUS_REL[1:])

# full path to the srp lock file
LOCK = os.path.join(RUCKUS, "lock")

READONLY = 0

# name of NOTES file for srp1 and srp2
NOTES1 = "NOTES"
NOTES2 = "NOTES-2"

# name of FILES file
FILES2 = "FILES-2"

# name of REV file
REV2 = "REV-2"

# name of LEFTOVER file
LEFTOVER2 = "LEFTOVER-2"

# name of DEPS_LIB file
DEPS_LIB2 = "DEPS_LIB-2"

# name of DEPS_PROG file
DEPS_PROG2 = "DEPS_PROG-2"

# name of DEPS_SRP file
DEPS_SRP2 = "DEPS_SRP-2"

# name of OWNEROVERRIDE file
OWNEROVERRIDE2 = "OWNEROVERRIDE-2"

# name of BLOB file
BLOB2 = "srpblob.tar.bz2"

# name of PREPOSTLIB module file
PREPOSTLIB2 = "PREPOSTLIB_2.py"

# how can we recursively create directories?
RMKDIR = "__RMKDIR__"

# how can we get archive copies of a file?
ACOPY = "__ACOPY__"

# where is the file command?
FILE = "/usr/bin/file"

# where is the ldconfig command?
LDCONFIG = "/sbin/ldconfig"

# the ld config file
LDSOCONF = "/etc/ld.so.conf"

# implicit ldpath entries
LDPATH_DEFAULT = ['/lib', '/usr/lib', '/usr/local/lib']

# what are the infofile directory files?
INFOFILEDIRS = ["/usr/share/info/dir", "/usr/local/share/info/dir", "/etc/info-dir"]

# what shell should we invoke for our scripts?
SH = "__SH__"

# what is the preferred checksum algorithm?
CHECKSUM = "__CHECKSUM__"

# global timer variable
TIMER=0

# global flag indicators
VERBOSE=0
UPGRADE=0
LISTFILES=0
LISTFLAGS=0
TALLY=0
PRETTY=1
PERSISTENT=0

# list of directories needed inside RUCKUS
ruckus_dirs = ["build",
               "brp",
               "installed",
               "package",
               "tmp"
               ]

# list of supported SRP_FLAGS
supported_flags = ["SRP_DUMMYFLAG",
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
                   "SRP_INPLACE",
                   "SRP_PREPOSTLIB",
                   "SRP_PERMS",
                   "SRP_LINKTARGET",
                   "SRP_OWNEROVERRIDE",
                   "SRP_CHAIN",
                   "SRP_LEFTOVERS",
                   "SRP_NO_UPGRADE",
                   "SRP_NO_CHECKSUM",
                   "SRP_NO_PERMS",
                   "SRP_NO_LINKTARGET",
                   "SRP_NO_INSTALLINFO",
                   "SRP_NO_LDCONFIG",
                   "SRP_NO_LEFTOVERS"
                   ]

# default SRP_FLAGS
default_flags = ["SRP_UPGRADABLE",
                 "SRP_CHECKSUM",
                 "SRP_PERMS",
                 "SRP_LINKTARGET",
                 "SRP_LEFTOVERS"
                 ]

# this is the search path for dependent executables
exec_path = []
for x in os.environ["PATH"].split(":"):
    if x[0] == "/":
        exec_path.append(os.path.join("/", SRP_ROOT_PREFIX, x[1:]))


# srp will NEVER remove these dirs when uninstalling a package
perm_dirs = [SRP_ROOT_PREFIX,
             SRP_ROOT_PREFIX + "/",
             SRP_ROOT_PREFIX + "/bin",
             SRP_ROOT_PREFIX + "/boot",
             SRP_ROOT_PREFIX + "/dev",
             SRP_ROOT_PREFIX + "/dev/pts",
             SRP_ROOT_PREFIX + "/etc",
             SRP_ROOT_PREFIX + "/home",
             SRP_ROOT_PREFIX + "/lib",
             SRP_ROOT_PREFIX + "/mnt",
             SRP_ROOT_PREFIX + "/proc",
             SRP_ROOT_PREFIX + "/root",
             SRP_ROOT_PREFIX + "/sbin",
             SRP_ROOT_PREFIX + "/tmp",
             SRP_ROOT_PREFIX + "/var",
             SRP_ROOT_PREFIX + "/opt", 
             SRP_ROOT_PREFIX + "/usr",
             SRP_ROOT_PREFIX + "/usr/bin",
             SRP_ROOT_PREFIX + "/usr/etc",
             SRP_ROOT_PREFIX + "/usr/include",
             SRP_ROOT_PREFIX + "/usr/lib",
             SRP_ROOT_PREFIX + "/usr/man",
             SRP_ROOT_PREFIX + "/usr/man/man1",
             SRP_ROOT_PREFIX + "/usr/man/man2",
             SRP_ROOT_PREFIX + "/usr/man/man3",
             SRP_ROOT_PREFIX + "/usr/man/man4",
             SRP_ROOT_PREFIX + "/usr/man/man5",
             SRP_ROOT_PREFIX + "/usr/man/man6",
             SRP_ROOT_PREFIX + "/usr/man/man7",
             SRP_ROOT_PREFIX + "/usr/man/man8",
             SRP_ROOT_PREFIX + "/usr/sbin",
             SRP_ROOT_PREFIX + "/usr/share",
             SRP_ROOT_PREFIX + "/usr/src",
             SRP_ROOT_PREFIX + "/usr/tmp",
             SRP_ROOT_PREFIX + "/usr/var",
             SRP_ROOT_PREFIX + "/usr/share/man",
             SRP_ROOT_PREFIX + "/usr/share/doc",
             SRP_ROOT_PREFIX + "/usr/share/info",
             SRP_ROOT_PREFIX + "/usr/share/dict",
             SRP_ROOT_PREFIX + "/usr/share/locale",
             SRP_ROOT_PREFIX + "/usr/share/nls",
             SRP_ROOT_PREFIX + "/usr/share/misc",
             SRP_ROOT_PREFIX + "/usr/share/terminfo",
             SRP_ROOT_PREFIX + "/usr/share/zoneifo",
             SRP_ROOT_PREFIX + "/usr/share/man/man1",
             SRP_ROOT_PREFIX + "/usr/share/man/man2",
             SRP_ROOT_PREFIX + "/usr/share/man/man3",
             SRP_ROOT_PREFIX + "/usr/share/man/man4",
             SRP_ROOT_PREFIX + "/usr/share/man/man5",
             SRP_ROOT_PREFIX + "/usr/share/man/man6",
             SRP_ROOT_PREFIX + "/usr/share/man/man7",
             SRP_ROOT_PREFIX + "/usr/share/man/man8",
             SRP_ROOT_PREFIX + "/usr/local",
             SRP_ROOT_PREFIX + "/usr/local/bin",
             SRP_ROOT_PREFIX + "/usr/local/etc",
             SRP_ROOT_PREFIX + "/usr/local/include",
             SRP_ROOT_PREFIX + "/usr/local/lib",
             SRP_ROOT_PREFIX + "/usr/local/sbin",
             SRP_ROOT_PREFIX + "/usr/local/share",
             SRP_ROOT_PREFIX + "/usr/local/src",
             SRP_ROOT_PREFIX + "/usr/local/tmp",
             SRP_ROOT_PREFIX + "/usr/local/var",
             SRP_ROOT_PREFIX + "/usr/local/share/man",
             SRP_ROOT_PREFIX + "/usr/local/share/doc",
             SRP_ROOT_PREFIX + "/usr/local/share/info",
             SRP_ROOT_PREFIX + "/usr/local/share/dict",
             SRP_ROOT_PREFIX + "/usr/local/share/locale",
             SRP_ROOT_PREFIX + "/usr/local/share/nls",
             SRP_ROOT_PREFIX + "/usr/local/share/misc",
             SRP_ROOT_PREFIX + "/usr/local/share/terminfo",
             SRP_ROOT_PREFIX + "/usr/local/share/zoneifo",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man1",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man2",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man3",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man4",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man5",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man6",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man7",
             SRP_ROOT_PREFIX + "/usr/local/share/man/man8", 
             SRP_ROOT_PREFIX + "/var/lock",
             SRP_ROOT_PREFIX + "/var/log",
             SRP_ROOT_PREFIX + "/var/mail",
             SRP_ROOT_PREFIX + "/var/run",
             SRP_ROOT_PREFIX + "/var/spool",
             SRP_ROOT_PREFIX + "/var/tmp",
             SRP_ROOT_PREFIX + "/opt/bin",
             SRP_ROOT_PREFIX + "/opt/doc",
             SRP_ROOT_PREFIX + "/opt/include",
             SRP_ROOT_PREFIX + "/opt/info",
             SRP_ROOT_PREFIX + "/opt/lib",
             SRP_ROOT_PREFIX + "/opt/man",
             SRP_ROOT_PREFIX + "/opt/man/man1",
             SRP_ROOT_PREFIX + "/opt/man/man2",
             SRP_ROOT_PREFIX + "/opt/man/man3",
             SRP_ROOT_PREFIX + "/opt/man/man4",
             SRP_ROOT_PREFIX + "/opt/man/man5",
             SRP_ROOT_PREFIX + "/opt/man/man6",
             SRP_ROOT_PREFIX + "/opt/man/man7",
             SRP_ROOT_PREFIX + "/opt/man/man8",
             SRP_ROOT_PREFIX + "/etc/init.d",
             SRP_ROOT_PREFIX + "/etc/rc.d",
             SRP_ROOT_PREFIX + "/etc/rc0.d",
             SRP_ROOT_PREFIX + "/etc/rc1.d",
             SRP_ROOT_PREFIX + "/etc/rc2.d",
             SRP_ROOT_PREFIX + "/etc/rc3.d",
             SRP_ROOT_PREFIX + "/etc/rc4.d",
             SRP_ROOT_PREFIX + "/etc/rc5.d",
             SRP_ROOT_PREFIX + "/etc/rc6.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/init.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc0.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc1.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc2.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc3.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc4.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc5.d",
             SRP_ROOT_PREFIX + "/etc/rc.d/rc6.d",
             SRP_ROOT_PREFIX + "/scrap",
             RUCKUS,
             RUCKUS + "/build",
             RUCKUS + "/brp",
             RUCKUS + "/installed",
             RUCKUS + "/package",
             RUCKUS + "/tmp"
             ]
