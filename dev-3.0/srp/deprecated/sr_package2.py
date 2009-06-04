"""sr_package2 -
srp python library for version 2.0+ packages.
this will be used by srp to install and maintain packages from
source ruckus linux 3.0 and beyond."""


import os
import os.path
import sys
import stat
import string
import socket
import commands
import re
import tarfile
import pwd
import grp

import sr
import utils


class package:
    """package
    the base package class
    """
    
    
    def __init__(self, logname=""):
        """__init__() -> package
        base package class initialization constructor.
        retval: initialized package
        """
        if logname:
            # this is used for already installed packages
            temp = logname.split('_-_')
            self.name = os.path.basename(temp[0])
            self.dirname = temp[1]
            self.package_rev = temp[-1]
            self.logfile = sr.RUCKUS + "/installed/" + logname
            f = open(self.logfile, 'r')
            self.srp_flags = f.readline().rstrip().split('srp_flags = ')[-1].split()
            f.close()

            if "SRP_MD5SUM" in self.srp_flags:
                sr.CHECKSUM = "md5"
            elif "SRP_SHA1SUM" in self.srp_flags:
                sr.CHECKSUM = "sha1"
            
        else:
            self.name = ""
            self.dirname = ""
            self.package_rev = ""
            self.logfile = ""
            self.srp_flags = []

        self.filename = ""
        self.description = ""
        self.flags = ""
        self.prefix = ""
        self.eprefix = ""
        self.bindir = ""
        self.sbindir = ""
        self.libexecdir = ""
        self.datadir = ""
        self.sysconfdir = ""
        self.sharedstatedir = ""
        self.localstatedir = ""
        self.libdir = ""
        self.includedir = ""
        self.oldincludedir = ""
        self.infodir = ""
        self.mandir = ""
        self.srcdir = ""
        self.otheropts = ""
        self.i_script = ""
        self.inplace = ""
        self.ldpath = []
        self.ownerinfo = {}
    
    def _read_notes(self):
        """_read_notes()
        this function will read the NOTES file
        retval: none
        """
        temp = ""
        fool = ""
        fool2 = ""
        f = open(sr.RUCKUS + "/package/" + sr.NOTES2, 'r')
        self.name = f.readline().rstrip()
        self.filename = f.readline().rstrip()
        self.dirname = f.readline().rstrip()
        self.description = f.readline().rstrip()
        
        self.srp_flags = f.readline().rstrip().split('srp_flags = ')[-1].split()
        # we don't want to save flags we didn't use during the install...
        utils.vprint("srp_flags pre-pruning: %s" % (self.srp_flags))
        for i in self.srp_flags[:]:
            if "=" in i:
                flagarg = i.split("=")
                x = flagarg[0]
                y = flagarg[1]
                self.srp_flags.remove(i)
                self.srp_flags.append(x)
            else:
                x = i
                y = ""
            if x not in sr.supported_flags:
                utils.vprint("dropping unsupported srp_flag: " + x)
                self.srp_flags.remove(x)
            elif y != "":
                if x == "SRP_INPLACE":
                    utils.vprint("initializing self.inplace")
                    self.inplace = sr.SRP_ROOT_PREFIX + y
                elif x == "SRP_LDCONFIG":
                    utils.vprint("initializing self.ldpath")
                    self.ldpath = y.split(',')
                
        # add default_flags, if necesary
        for x in sr.default_flags:
            if x not in self.srp_flags:
                # special case for CHECKSUM variants
                if x == "SRP_CHECKSUM":
                    if utils.any_of_in(["SRP_MD5SUM", "SRP_SHA1SUM"],
                                       self.srp_flags):
                        continue
                self.srp_flags.append(x)

        # check for default overrides
        if "SRP_NO_UPGRADE" in self.srp_flags:
            self.srp_flags.remove("SRP_UPGRADABLE")
            self.srp_flags.remove("SRP_NO_UPGRADE")

        if "SRP_NO_CHECKSUM" in self.srp_flags:
            self.srp_flags.remove("SRP_CHECKSUM")
            self.srp_flags.remove("SRP_NO_CHECKSUM")

        if "SRP_NO_PERMS" in self.srp_flags:
            self.srp_flags.remove("SRP_PERMS")
            self.srp_flags.remove("SRP_NO_PERMS")

        if "SRP_NO_LINKTARGET" in self.srp_flags:
            self.srp_flags.remove("SRP_LINKTARGET")
            self.srp_flags.remove("SRP_NO_LINKTARGET")

        if "SRP_NO_INSTALLINFO" in self.srp_flags:
            self.srp_flags.remove("SRP_INSTALLINFO")
            self.srp_flags.remove("SRP_NO_INSTALLINFO")

        if "SRP_NO_LDCONFIG" in self.srp_flags:
            self.srp_flags.remove("SRP_LDCONFIG")
            self.srp_flags.remove("SRP_NO_LDCONFIG")
        
        self.flags = f.readline().rstrip()
        
        self.prefix = f.readline().rstrip()
        if self.prefix != "SRP_NONE":
            temp = temp + " --prefix=" + sr.RUCKUS + "/tmp" + self.prefix
            fool = fool + " --prefix=" + self.prefix
            fool2 = fool2 + " prefix=" + sr.RUCKUS + "/tmp" + self.prefix
            
        self.eprefix = f.readline().rstrip()
        if self.eprefix != "SRP_NONE":
            temp = temp + " --exec-prefix=" + sr.RUCKUS + "/tmp" + self.eprefix
            fool = fool + " --exec-prefix=" + self.eprefix
            fool2 = fool2 + " exec-prefix=" + sr.RUCKUS + "/tmp" + self.eprefix

        self.bindir = f.readline().rstrip()
        if self.bindir != "SRP_NONE":
            temp = temp + " --bindir=" + sr.RUCKUS + "/tmp" + self.bindir
            fool = fool + " --bindir=" + self.bindir
            fool2 = fool2 + " bindir=" + sr.RUCKUS + "/tmp" + self.bindir

        self.sbindir = f.readline().rstrip()
        if self.sbindir != "SRP_NONE":
            temp = temp + " --sbindir=" + sr.RUCKUS + "/tmp" + self.sbindir
            fool = fool + " --sbindir=" + self.sbindir
            fool2 = fool2 + " sbindir=" + sr.RUCKUS + "/tmp" + self.sbindir

        self.libexecdir = f.readline().rstrip()
        if self.libexecdir != "SRP_NONE":
            temp = temp + " --libexecdir=" + sr.RUCKUS + "/tmp" + self.libexecdir
            fool = fool + " --libexecdir=" + self.libexecdir
            fool2 = fool2 + " libexecdir=" + sr.RUCKUS + "/tmp" + self.libexecdir

        self.datadir = f.readline().rstrip()
        if self.datadir != "SRP_NONE":
            temp = temp + " --datadir=" + sr.RUCKUS + "/tmp" + self.datadir
            fool = fool + " --datadir=" + self.datadir
            fool2 = fool2 + " datadir=" + sr.RUCKUS + "/tmp" + self.datadir

        self.sysconfdir = f.readline().rstrip()
        if self.sysconfdir != "SRP_NONE":
            temp = temp + " --sysconfdir=" + sr.RUCKUS + "/tmp" + self.sysconfdir
            fool = fool + " --sysconfdir=" + self.sysconfdir
            fool2 = fool2 + " sysconfdir=" + sr.RUCKUS + "/tmp" + self.sysconfdir

        self.sharedstatedir = f.readline().rstrip()
        if self.sharedstatedir != "SRP_NONE":
            temp = temp + " --sharedstatedir=" + sr.RUCKUS + "/tmp" + self.sharedstatedir
            fool = fool + " --sharedstatedir=" + self.sharedstatedir
            fool2 = fool2 + " sharedstatedir=" + sr.RUCKUS + "/tmp" + self.sharedstatedir

        self.localstatedir = f.readline().rstrip()
        if self.localstatedir != "SRP_NONE":
            temp = temp + " --localstatedir=" + sr.RUCKUS + "/tmp" + self.localstatedir
            fool = fool + " --localstatedir=" + self.localstatedir
            fool2 = fool2 + " localstatedir=" + sr.RUCKUS + "/tmp" + self.localstatedir

        self.libdir = f.readline().rstrip()
        if self.libdir != "SRP_NONE":
            temp = temp + " --libdir=" + sr.RUCKUS + "/tmp" + self.libdir
            fool = fool + " --libdir=" + self.libdir
            fool2 = fool2 + " libdir=" + sr.RUCKUS + "/tmp" + self.libdir

        self.includedir = f.readline().rstrip()
        if self.includedir != "SRP_NONE":
            temp = temp + " --includedir=" + sr.RUCKUS + "/tmp" + self.includedir
            fool = fool + " --includedir=" + self.includedir
            fool2 = fool2 + " includedir=" + sr.RUCKUS + "/tmp" + self.includedir
        
        self.oldincludedir = f.readline().rstrip()
        if self.oldincludedir != "SRP_NONE":
            temp = temp + " --oldincludedir=" + sr.RUCKUS + "/tmp" + self.oldincludedir
            fool = fool + " --oldincludedir=" + self.oldincludedir
            fool2 = fool2 + " oldincludedir=" + sr.RUCKUS + "/tmp" + self.oldincludedir
        
        self.infodir = f.readline().rstrip()
        if self.infodir != "SRP_NONE":
            temp = temp + " --infodir=" + sr.RUCKUS + "/tmp" + self.infodir
            fool = fool + " --infodir=" + self.infodir
            fool2 = fool2 + " infodir=" + sr.RUCKUS + "/tmp" + self.infodir
        
        self.mandir = f.readline().rstrip()
        if self.mandir != "SRP_NONE":
            temp = temp + " --mandir=" + sr.RUCKUS + "/tmp" + self.mandir
            fool = fool + " --mandir=" + self.mandir
            fool2 = fool2 + " mandir=" + sr.RUCKUS + "/tmp" + self.mandir
        
        self.srcdir = f.readline().rstrip()
        if self.srcdir != "SRP_NONE":
            temp = temp + " --srcdir=" + sr.RUCKUS + "/tmp" + self.srcdir
            fool = fool + " --srcdir=" + self.srcdir
            fool2 = fool2 + " srcdir=" + sr.RUCKUS + "/tmp" + self.srcdir
        
        self.otheropts = f.readline().rstrip()
        if self.otheropts != "SRP_NONE":
            temp = temp + " " + self.otheropts
            fool += " " + self.otheropts
        
        if 'SRP_CANT_FOOL' not in self.srp_flags:
            self.i_script = "export SRP_OPTS='" + fool + "' && \nexport FOOL_OPTS='" + fool2 + "' && \n"
        else:
            self.i_script = "export SRP_OPTS='" + temp + "' && \nexport FOOL_OPTS='' && \n"
        
        if 'SRP_INPLACE' in self.srp_flags:
            self.i_script += "export INPLACE='" + self.inplace + "' && \n"
        
        self.i_script += "export SRP_ROOT='" + sr.RUCKUS + "/tmp' && \n"

        if self.flags != "SRP_NONE":
            self.i_script += "export CFLAGS=" + self.flags + " && \nexport CXXFLAGS=" + self.flags + " && \n"

        # the rest of the file is i_script
        buf = string.join(f.readlines(), "").rstrip()
        self.i_script += utils.compat_unescaper(buf)
        
        f.close()
        
        if "SRP_PREPOSTLIB" in self.srp_flags:
            utils.vprint("loading included PREPOSTLIB module...")
            sys.path.append(sr.RUCKUS + "/package")
            modname = sr.PREPOSTLIB2.split(".py")[0]
            self.prepost=__import__(modname)

        if "SRP_OWNEROVERRIDE" in self.srp_flags:
            utils.vprint("reading OWNEROVERRIDE file...")
            self._read_owneroverride()
        

    def _read_owneroverride(self):
        """_read_owneroverride()
        reads the OWNEROVERRIDE file and creates self.ownerinfo dict
        """
        f = file(sr.RUCKUS + "/package/" + sr.OWNEROVERRIDE2, 'r')
        self.ownerinfo = {}
        line = f.readline().strip()
        while line != "":
            temp1 = line.split(":")[0]
            temp2 = string.join(line.split(":")[1:], ":")
            self.ownerinfo[temp1] = temp2
            line = f.readline().strip()
        f.close()


    def _failure(self, attempt, msg=""):
        """_failure(attempt, msg="")
        prints a failure message
        retval: none
        """
        if msg:
            print ""
            print msg
        print ""
        print attempt + " failed."
        print "package was: " + self.name
        print "the source code is in " + sr.RUCKUS + "/build and a lock file"
        print "is in " + sr.RUCKUS + "/package.  see if you can get the source"
        print "to compile and install by hand, then remove everything in"
        print sr.RUCKUS + "/build and " + sr.RUCKUS + "/package.  then make"
        print "appropriate changes to the notes file, recreate the package,"
        print "and re-run srp."
        print ""
        print "note - if you install by hand, srp won\'t know how to uninstall the package"
        print ""

    
    def _dump(self, logs=[], force=0, fake=0, inplace_log=0):
        """_dump(self, list, logs, force) -> log, deps_lib
        dumps all the files from $RUCKUS/tmp to their appropriate locations
        retval0: log of installed files
        retval1: list of dependencies
        """
        newlist = []
        deps_lib = []
        
        if fake and not inplace_log:
            silent = 1
        else:
            silent = 0
        
        if not silent:
            sys.stdout.write("dumping: ")
            sys.stdout.flush()
        
        size_installed = 0
        hash_count = 0
        
        if inplace_log:
            location = self.inplace + "/" + self.dirname
        else:
            location = sr.RUCKUS + "/tmp"
        os.chdir(location)
        
        list = utils.list_files(".")
        list.remove(".")
        
        temp = location
        while os.path.islink(temp):
            i = os.path.dirname(temp)
            j = os.path.basename(temp)
            if i:
                os.chdir(i)
            temp = os.readlink(j)
#        print "***** temp: %s" % (temp)
        os.chdir(location)
#        print "***** " + os.getcwd()
        
        size_total = commands.getoutput("du -bs " + temp).split()[0]
#        print "***** size_total: %s" % (size_total)
        
        for i in list:
            utils.vprint("installing: " + i)
            size_installed = size_installed + utils.getsize(i)

            # do SRP_PERMS and/or SRP_OWNEROVERRIDE stuff.
            # if SRP_OWNEROVERRIDE info is supplied for a file, chown it
            # accordingly.  otherwise, chown the file to uid/gid of the
            # installing user.
            if ("SRP_PERMS" in self.srp_flags or
                "SRP_OWNEROVERRIDE" in self.srp_flags):
                # lchown the file!
                if i[1:] in self.ownerinfo:
                    uid = self.ownerinfo[i[1:]]
                    utils.vprint("ownerinfo[%s]: %s" % (i[1:], uid))
                    gid = uid.split(":")[1]
                    uid = uid.split(":")[0]
                    # convert gid to int
                    try:
                        gid = int(gid)
                    except:
                        try:
                            gid = grp.getgrnam(gid)[2]
                        except:
                            gid = -1
                    # convert uid to int
                    try:
                        uid = int(uid)
                    except:
                        try:
                            uid = pwd.getpwnam(uid)[2]
                        except:
                            uid = -1
                else:
                    uid = os.getuid()
                    gid = os.getgid()
                    
                # now do the chowning
                try:
                    utils.vprint("chowning %s: %d, %d" % (i, uid, gid))
                    os.lchown(i, uid, gid)
                except:
                    # if this failed, it's ok.  check() will notice later
                    # on and give the user a warning.
                    utils.vprint("failed to chown file!")
                    pass
            
            if os.path.islink(i):
                utils.vprint("link")

                # look for (and fix!) embedded absolute paths here
                target = os.readlink(i)
                if os.path.isabs(target):
                    # absolute path in symlink!
                    target = target.split(os.path.join(sr.RUCKUS, "tmp"))[-1]
                    utils.vprint("fixing symlink: %s -> %s" % (i, target))
                    os.unlink(i)
                    os.symlink(target, i)
                
                if not fake:
                    link = os.path.join("/", sr.SRP_ROOT_PREFIX, i[2:])
                    if os.path.exists(link) or os.path.islink(link):
                        utils.vprint("exists!!!")
                        os.unlink(link)

                    # since we already fixed any bad paths, we can just copy
                    # the symlink
                    utils.vprint("creating symlink: %s -> %s" % (link, target))
                    os.symlink(target, link)
                    
                if inplace_log:
                    if sr.SRP_ROOT_PREFIX:
                        temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
                    else:
                        temp=self.inplace
                    newlist.append(temp + "/" + self.dirname + i[1:])
                else:
                    newlist.append(i[1:])

                # add checksum line, if configured
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM"],
                                   self.srp_flags):
                    newlist.append("link")

            elif os.path.isdir(i):
                utils.vprint("directory")
                if not fake:
                    file = os.path.join("/", sr.SRP_ROOT_PREFIX, i[2:])
                    utils.vprint("making dir: %s" % (file))
                    try:
                        os.makedirs(file)
                        # preserve directory permisions...
                        utils.vprint("matching permisions with " + i)
                        os.chmod(file, os.stat(i)[stat.ST_MODE])
                        # preserve directory owner/group associations
                        os.chown(file,
                                 os.stat(i)[stat.ST_UID],
                                 os.stat(i)[stat.ST_GID])
                    except:
                        utils.vprint("couldn't make dir: %s" % (file))
                        # we didn't create the dir, so we should make sure we
                        # don't log what we would have chmoded it to.
                        try:
                            os.chmod(i, os.stat(file)[stat.ST_MODE])
                            os.chown(i,
                                     os.stat(file)[stat.ST_UID],
                                     os.stat(file)[stat.ST_GID])
                        except:
                            # unless we're running as non-root and existing dir
                            # was owned by root...
                            pass
                        
                    
                if inplace_log:
                    if sr.SRP_ROOT_PREFIX:
                        temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
                    else:
                        temp=self.inplace
                    newlist.append(temp + "/" + self.dirname + i[1:])
                else:
                    newlist.append(i[1:])

                # add checksum line, if configured
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM"],
                                   self.srp_flags):
                    newlist.append("dir")

            else:
                utils.vprint("normal file")
                # don't accidentally overwrite a system info dir file
                if i[1:] in sr.INFOFILEDIRS:
                    #os.unlink(i[1:])
                    #print "FOOOOOOOOOOOOOOOOOOOOO"
                    break
                
                if not fake:
                    thefile = os.path.join("/", sr.SRP_ROOT_PREFIX, i[2:])
                    if os.path.exists(thefile) or os.path.islink(thefile):
                        utils.vprint("exists!!!")
                        if not force or not utils.any_of_in(["SRP_MD5SUM",
                                                             "SRP_SHA1SUM",
                                                             "SRP_CHECKSUM"],
                                                            self.srp_flags):
                            os.rename(thefile, thefile + ".srpbak")
                        else:
                            utils.vprint(logs)
                            for j in logs:
                                utils.vprint("j: %s" % j)
                                utils.vprint("i[1:]: " + i[1:])
                                log = os.path.join(sr.RUCKUS, "installed", j)
                                utils.vprint("log: %s" % log)
                                sum_correct = lookup_checksum(i[1:], log)
                                utils.vprint("sum_correct: %s" % sum_correct)
                                sum_real = utils.checksum(sr.SRP_ROOT_PREFIX + "/" + i[1:])
                                utils.vprint("sum_real: %s" % sum_real)
                                if sum_correct != "" and sum_correct != sum_real:
                                    utils.vprint("creating srpbak")
                                    os.rename(thefile, thefile + ".srpbak")


                    go = sr.ACOPY + " " + i + " " + sr.SRP_ROOT_PREFIX + "/" + i[1:]
                    utils.vprint(go)
                    status = os.system(go)
                    if status != 0:
                        print "couldn't create link: " + sr.SRP_ROOT_PREFIX + "/" + i[1:]
                        return []
                    
                if inplace_log:
                    if sr.SRP_ROOT_PREFIX:
                        temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
                    else:
                        temp=self.inplace
                    newlist.append(temp + "/" + self.dirname + i[1:])
                else:
                    newlist.append(i[1:])

                # add checksum line, if configured
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM"],
                                   self.srp_flags):
                    newlist.append(utils.checksum(i))

                # update deps_lib
                if os.access(i, os.X_OK):
                    temp = commands.getstatusoutput("ldd " + i)
                    # some plain text files with execute permissions are
                    # causing ldd to spit up, but still return 0 like this:
                    # (0, "lddlibc4: cannot read header from `/opt/ACE/ACE-5.3a/bin/.cvsignore'")
                    if temp[0] == 0:
                        if temp[1].split(':')[0] != "lddlibc4":
                            temp = temp[1].split('\n')
                            for x in temp:
                                x = x.split()[0].strip()
                                if x not in deps_lib:
                                    deps_lib.append(x)

            # add file perms line, if configured
            if "SRP_PERMS" in self.srp_flags:
                # make sure the supposed ownership is preserverd, even if the
                # installing user failed to chown the file.  check() will flag
                # this as a warning later on.
                if ("SRP_OWNEROVERRIDE" in self.srp_flags and
                    i[1:] in self.ownerinfo):
                    mode = "%s" % os.lstat(i)[stat.ST_MODE]
                    newlist.append(string.join([mode, self.ownerinfo[i[1:]]],
                                               ":"))
                else:
                    newlist.append(utils.file_perms(i))

            # add link target line, if configured
            if "SRP_LINKTARGET" in self.srp_flags:
                newlist.append(utils.link_target(i))
            
            percent = float(size_installed)/float(size_total)*100
            utils.vprint("---")
            utils.vprint("percent %.2f" % percent)
            utils.vprint("%d" % int((percent/100.0)*59))
            utils.vprint("hash_count %d" % hash_count)
            utils.vprint("%d of %d" % (size_installed, int(size_total)))
            if not silent:
                while int((percent/100.0)*58) - hash_count > 0:
                    sys.stdout.write("#")
                    sys.stdout.flush()
                    hash_count = hash_count + 1
            
        if not silent:
            while hash_count < 59:
                sys.stdout.write("#")
                sys.stdout.flush()
                hash_count = hash_count + 1

            print " [  done  ]"
        
        utils.vprint(hash_count)
        utils.vprint(size_installed)
        utils.vprint(size_total)
        
        if inplace_log:
            if sr.SRP_ROOT_PREFIX:
                temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
            else:
                temp=self.inplace
            temp += "/" + self.dirname
            while temp != "/":
                newlist.insert(0, "dir")
                newlist.insert(0, temp)
                temp = os.path.dirname(temp)
        
        return newlist, deps_lib
    
    
    def _build(self):
        """_build() -> status
        this actually builds the installable fileset
        retval: 1 = success, 0 = failure
        """
        print "extracting %s..." % (self.filename)
        if not utils.bz2ball_extract(os.path.join(sr.RUCKUS,
                                                  "package",
                                                  self.filename),
                                     os.path.join(sr.RUCKUS,
                                                  "build")):
            utils.vprint("failed while extracting")
            return 0

        print "prebuild..."
        try:
            f = file(os.path.join(sr.RUCKUS, "build/srp_go"), "w")
            f.write("#!" + sr.SH + "\n")
            f.write("cd " + self.dirname + "\n")
            f.write(self.i_script + "\n")
            f.close()
            os.chmod(os.path.join(sr.RUCKUS, "build/srp_go"), 0755)
        except:
            utils.vprint("failed while doing prebuild")
            return 0

        print "build..."
        go = """\
cd """ + sr.RUCKUS + """/build &&
./srp_go """
        
        utils.vprint(go)
        status = os.system(go)
        utils.vprint(status)
        if status != 0:
            utils.vprint("failed while doing build")
            return 0
        return 1
    

    def _build_inplace(self):
        """_build_inplace() -> status
        this actually builds the installable fileset
        retval: 1 = success, 0 = failure
        """
        print "extracting %s..." % (self.filename)
        try:
            utils.vprint("trying to create inplace dir: %s" % self.inplace)
            os.makedirs(self.inplace)
        except:
            utils.vprint("failed while creating inplace dir")
            #return 0
            # ^^ actually, this shouldn't be fatal.
        if not utils.bz2ball_extract(os.path.join(sr.RUCKUS,
                                                  "package",
                                                  self.filename),
                                     self.inplace):
            utils.vprint("failed while extracting")
            return 0

        print "prebuild..."
        try:
            f = file(os.path.join(self.inplace, "srp_go"), "w")
            f.write("#!" + sr.SH + "\n")
            f.write("cd " + self.dirname + "\n")
            f.write(self.i_script + " && \n")
            f.write("rm $INPLACE/srp_go\n")
            f.close()
            os.chmod(os.path.join(self.inplace, "srp_go"), 0755)
        except:
            utils.vprint("failed while doing prebuild")
            return 0

        print "build..."
        go = """\
cd """ + self.inplace + """ &&
./srp_go """
        
        utils.vprint(go)
        status = os.system(go)
        utils.vprint(status)
        if status != 0:
            utils.vprint("failed while doing build")
            return 0
        return 1


    def _finalize(self, log):
        """_finalize(log) -> status
        writes the logfile and takes care of other finishing touches
        retval: 1 = success, 0 = failure
        """
        # write the logfile
        sys.stdout.write(string.ljust("writing logfile...", 69))
        sys.stdout.flush()

        flags_to_write = self.srp_flags[:]
        
        if "SRP_INSTALLINFO" in self.srp_flags:
            # we will track installed infofiles with this
            info = []
        
        if "SRP_LDCONFIG" in self.srp_flags:
            ldpath = utils.read_ldpath()
            ldpath_pruned = ldpath[:]
            ldpath_orig = ldpath[:]
            if self.ldpath != []:
                flags_to_write.remove("SRP_LDCONFIG")
                flags_to_write.append("SRP_LDCONFIG=" +
                                      string.join(self.ldpath, ','))

        if "SRP_INPLACE" in self.srp_flags:
            flags_to_write.remove("SRP_INPLACE")
            if sr.SRP_ROOT_PREFIX:
                temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
            else:
                temp=self.inplace
            flags_to_write.append("SRP_INPLACE=" + temp)

        if "SRP_CHECKSUM" in self.srp_flags:
            flags_to_write.remove("SRP_CHECKSUM")
            if "md5" == sr.CHECKSUM:
                flags_to_write.append("SRP_MD5SUM")
            elif "sha1" == sr.CHECKSUM:
                flags_to_write.append("SRP_SHA1SUM")
        
        try:
            f = open(self.logfile, 'w')
            f.write("srp_flags = " + string.join(flags_to_write) + "\n")
            for i in log:
                f.write(i + "\n")
                if "SRP_INSTALLINFO" in self.srp_flags:
                    temp = sr.SRP_ROOT_PREFIX + i
                    if utils.is_infofile(temp):
                        info.append(
                            [temp, temp[:temp.find('/info/')] + '/info/dir'])
                if "SRP_LDCONFIG" in self.srp_flags and self.ldpath == []:
                    if utils.is_so(sr.SRP_ROOT_PREFIX + i):
                        temp = os.path.dirname(i)
                        utils.vprint("ld temp: %s" % temp)
                        if (temp not in ldpath_pruned and
                            temp not in sr.LDPATH_DEFAULT):
                            ldpath.append(temp)
                            ldpath_pruned.append(temp)
            if "SRP_PREPOSTLIB" in self.srp_flags:
                prepost = self.logfile + "_-_" + sr.PREPOSTLIB2
                if os.path.exists(prepost) or os.path.islink(prepost):
                    os.unlink(prepost)
                os.link(sr.RUCKUS + "/package/" + sr.PREPOSTLIB2, prepost)
                
                if sr.SRP_ROOT_PREFIX:
                    temp = self.logfile.split(sr.SRP_ROOT_PREFIX)[-1]
                else:
                    temp = self.logfile
                
                f.write(temp + "_-_" + sr.PREPOSTLIB2 + "\n")
                
                # add checksum line, if configured
                fname = self.logfile + "_-_" + sr.PREPOSTLIB2
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM"],
                                   self.srp_flags):
                    f.write(utils.checksum(fname) + "\n")

                # add file perms line, if configured
                if "SRP_PERMS" in self.srp_flags:
                    f.write(utils.file_perms(fname) + "\n")

                # add link target line, if configured
                if "SRP_LINKTARGET" in self.srp_flags:
                    f.write(utils.link_target(fname) + "\n")
                
            f.close
        except:
            print "[ failed ]"
            return 0
        print "[  done  ]"
        
        # take care of infofile installation, if need be
        if "SRP_INSTALLINFO" in self.srp_flags:
            sys.stdout.write(string.ljust("installing infofiles...", 69))
            sys.stdout.flush()
            for i in info:
                #install the infofile
                utils.vprint(i)
                go = "install-info " + i[0] + " " + i[1] + " > /dev/null 2>&1"
                utils.vprint(go)
                if os.system(go) != 0:
                    pass
                    #print "[ failed ]"
                    #return 0
                    # i don't think i care about install-info failing...
            print "[  done  ]"
        
        # take care of ldconfig updates, if need be
        if "SRP_LDCONFIG" in self.srp_flags:
            sys.stdout.write(string.ljust("updating gnu linker...", 69))
            sys.stdout.flush()
            # did we provide an ldpath update in the NOTES file?
            if self.ldpath != []:
                self.srp_flags.remove("SRP_LDCONFIG")
                self.srp_flags.append("SRP_LDCONFIG=" + string.join(self.ldpath, ','))

                for i in self.ldpath:
                    #if i not in ldpath_orig:
                    if i not in ldpath_pruned:
                        ldpath.append(i)
                        ldpath_pruned.append(i)
                utils.vprint("writing new ldpath config file (%s)" %
                             (sr.SRP_ROOT_PREFIX + sr.LDSOCONF))
                if not utils.write_ldpath(ldpath):
                    print "[ failed ]"
                    return 0
                
            else:
                # save our autodetected changes to ldpath...
                utils.vprint("ldpath_orig: %s" % ldpath_orig)
                utils.vprint("ldpath: %s" % ldpath)
                if ldpath != ldpath_orig:
                    utils.vprint("writing new ldpath config file (%s)" % (sr.SRP_ROOT_PREFIX + sr.LDSOCONF))
                    if not utils.write_ldpath(ldpath):
                        print "[ failed ]"
                        return 0
            print "[  done  ]"
        
        return 1
    
    
    def _check_installed(self, force=0):
        """_check_installed() -> status, current, previous
        checks to see if we're already installed
        retval0: 1 = success, 0 = failure
        retval1: list of currently installed packages (should never be > 1)
        retval2: list of previously installed packages (upgraded)
        """
        sys.stdout.write(string.ljust("checking for previous installations...", 69))
        sys.stdout.flush()
        
        current = []
        previous = []
        
        os.chdir(sr.RUCKUS + "/installed")
        ls = os.listdir("./")

        # prune out PREPOSTLIBs
        for i in ls[:]:
            if i.split('_-_')[-1] == sr.PREPOSTLIB2:
                ls.remove(i)

        for file in ls:
            i = file.split('_-_')
            if i[0] == self.name:
                if i[-1].split('_--_')[-1] == "srp-upgrade-leftovers":
                    previous.append(file)
                else:
                    current.append(file)
        
        #don't install if there's a current (or upgraded) installation
        #(unless install is called from upgrade() with force=1
        if not force:
            if current != [] or previous != []:
                print "[ failed ]"
                print "%s is already installed." % (self.name)
                print "installed versions: "
                if current != []:
                    for i in current:
                        print "  %s" % (i)
                if previous != []:
                    for i in previous:
                        print "  %s" % (i)
                return 0, current, previous
        else:
            # we're upgrading...
            if current == [] and previous == []:
                print "[ failed ]"
                if not sr.PERSISTENT:
                    print "%s isn't installed.  can't upgrade" % (self.name)
                    return 0, current, previous
                else:
                    print "%s isn't installed.  installing..."  % (self.name)
                    return 1, current, previous
            
            if current != []:
                if len(current) > 1:
                    print "[ failed ]"
                    print "err - more than one currently installed version!"
                    print "installed versions: "
                    for i in current:
                        print "  %s" % (i)
                    return 0, current, previous
                
                if current[0] == os.path.basename(self.logfile):
                    print "[ failed ]"
                    print "current package and upgrade package are the same"
                    if not sr.PERSISTENT:
                        return 0, current, previous
                    else:
                        print "attempting to upgrade anyway..."
                        # move /installed/file to
                        # /installed/file_--_srp-upgrade-leftovers
                        os.rename(current[0],
                                  current[0] + "_--_srp-upgrade-leftovers")
                        
                        # rename PREPOSTLIB too, if it exists!
                        if os.path.exists(current[0] + "_-_" + sr.PREPOSTLIB2):
                            oldname = current[0] + "_-_" + sr.PREPOSTLIB2
                            newname = oldname + "_--_srp-upgrade-leftovers"
                            os.rename(oldname, newname)
                        
                        previous.append(
                            current[0] + "_--_srp-upgrade-leftovers")
                        
                        current.pop(0)

                        return 1, current, previous
                
                #is the old package upgradable?
                f = open(sr.RUCKUS + "/installed/" + current[0], "r")
                srp_flags = f.readline().rstrip().split("srp_flags = ")[-1].split()
                f.close()
                if "SRP_UPGRADABLE" not in srp_flags:
                    print "[ failed ]"
                    print "package is not upgradable."
                    return 0, current, previous
            
            # move /installed/file to /installed/file_--_srp-upgrade-leftovers
            os.rename(current[0], current[0] + "_--_srp-upgrade-leftovers")
            
            # rename PREPOSTLIB too, if it exists!
            if os.path.exists(current[0] + "_-_" + sr.PREPOSTLIB2):
                oldname = current[0] + "_-_" + sr.PREPOSTLIB2
                newname = oldname + "_--_srp-upgrade-leftovers"
                os.rename(oldname, newname)
                
            previous.append(current[0] + "_--_srp-upgrade-leftovers")
            current.pop(0)
        
        print "[ passed ]"
        return 1, current, previous
    
    
    def info(self):
        """info()
        displays important info about the package.
        retval: none
        """
        print "name: %s" % (self.name)
        print "filename: %s" % (self.filename)
        print "dirname: %s" % (self.dirname)
        print "description: %s" % (self.description)
        print "srp_flags: %s" % (string.join(self.srp_flags))
        if "SRP_INPLACE" in self.srp_flags:
            print "inplace: %s" % (self.inplace)
        if "SRP_LDCONFIG" in self.srp_flags:
            print "ldpath: %s" % (self.ldpath)
        if "SRP_PREPOSTLIB" in self.srp_flags:
            print "prepost: %s" % (self.prepost)
        if "SRP_OWNEROVERRIDE" in self.srp_flags:
            print "ownerinfo: %s" % (self.ownerinfo)
        print "flags: %s" % (self.flags)
        print "prefix: %s" % (self.prefix)
        print "eprefix: %s" % (self.eprefix)
        print "bindir: %s" % (self.bindir)
        print "sbindir: %s" % (self.sbindir)
        print "libexecdir: %s" % (self.libexecdir)
        print "datadir: %s" % (self.datadir)
        print "sysconfdir: %s" % (self.sysconfdir)
        print "sharedstatedir: %s" % (self.sharedstatedir)
        print "localstatedir: %s" % (self.localstatedir)
        print "libdir: %s" % (self.libdir)
        print "includedir: %s" % (self.includedir)
        print "oldincludedir: %s" % (self.oldincludedir)
        print "infodir: %s" % (self.infodir)
        print "mandir: %s" % (self.mandir)
        print "srcdir: %s" % (self.srcdir)
        print "otheropts: %s" % (self.otheropts)
        print "i_script:"
        print self.i_script
        print
        print "package_rev: %s" % self.package_rev
        print "logname: %s" % self.logfile
    
    
    def install(self, force=0, current=[], previous=[]):
        """install(force) -> status
        installs the package. 'force' should only bet passed in (as 1) if
        we're being called from upgrade().
        retval: 1 = success, 0 = failure, -1 = already installed
        """
        if not force:
            status, current, previous = self._check_installed()
            if not status:
                return -1

        if "SRP_PREPOSTLIB" in self.srp_flags:
            sys.stdout.write("doing preinstall...".ljust(69))
            try:
                status = self.prepost.preinstall(self)
                if status != None and status != 1:
                    raise Exception("preinstall() returned %s" % status)
            except Exception, e:
                print "[ failed ]"
                print e
                return -1
            else:
                print "[  done  ]"
        
        print "building..."
        if "SRP_INPLACE" in self.srp_flags:
            # this is a special case...  /opt style build where the whole
            # source tree is going to be installed somewhere and nothing is
            # installed outside of the source area (i.e. mozilla)

            # make sure inplace dir doesn't already exist
            if os.path.exists(os.path.join(self.inplace, self.dirname)):
                print "ERROR: trying to build inplace in existing directory"
                return -1
        
            # now do the building
            if not self._build_inplace():
                self._failure("install")
                return 0
            newlist, deps_lib = self._dump(previous, force, fake=1, inplace_log=1)
            
        else:
            if not self._build():
                self._failure("install")
                return 0

            print "installing..."

            utils.vprint("\n\n\n***")
            utils.vprint("here we go!")
            utils.vprint("***\n\n\n")

            #--- here's the new install algorithm
            if "SRP_NO_COMPILE" in self.srp_flags:
                # the install script doesn't compile anything (or at least
                # doesn't embed the install path in the executables...
                utils.vprint("no compile problems")
                newlist, deps_lib = self._dump(previous, force)
                if newlist == []:
                    self._failure("install")
                    return 0
            elif "SRP_CANT_FOOL" not in self.srp_flags:
                # the package will be compiling but either there's no path
                # embedded in the binaries or we can fool the build procedure
                utils.vprint("foolable")
                newlist, deps_lib = self._dump(previous, force)
                if newlist == []:
                    self._failure("install")
                    return 0
            else:
                # alright, our current binary has the wrong path embedded in it
                # and can't be fooled...
                # this is slow as dirt (compiling the entire packge twice...),
                # but it's a necessary fallback
                sys.stdout.write("generating file list...".ljust(69))
                fudge = []
                for flag in ["SRP_MD5SUM", "SRP_SHA1SUM", "SRP_CHECKSUM"]:
                    if flag in self.srp_flags:
                        self.srp_flags.remove(flag)
                        fudge.append(flag)
                newlist, deps_lib = self._dump(fake=1)
                self.srp_flags.extend(fudge)
                if not newlist:
                    print "[ failed ]"
                    self._failure("install")
                    return 0
                print "[  done  ]"
                
                print "rebuilding for real install..."
                
                print "removing old files..."
                try:
                    utils.nuke_fs_node(os.path.join(sr.RUCKUS,
                                                    "build",
                                                    self.dirname))
                except:
                    utils.vprint("failed while removing old files")
                    self._failure("install")
                    return 0

                print "extracting %s..." % (self.filename)
                if not utils.bz2ball_extract(os.path.join(sr.RUCKUS,
                                                          "package",
                                                          self.filename),
                                             os.path.join(sr.RUCKUS,
                                                          "build")):
                    utils.vprint("failed while extracting")
                    self._failure("install")
                    return 0

                print "prebuild..."
                go = "cd " + sr.RUCKUS + "/build &&"
                go += "sed 's|" + sr.RUCKUS + "/tmp|" + sr.SRP_ROOT_PREFIX + "|g' srp_go > srp_go2 &&"
                go += "chmod 755 srp_go2"

                utils.vprint(go)
                status = os.system(go)
                if status != 0:
                    utils.vprint(status)
                    utils.vprint("failed while doing prebuild")
                    self._failure("install")
                    return 0

                print "build"
                go = "cd " + sr.RUCKUS + "/build &&"
                go += "./srp_go2"
                
                utils.vprint("can't fool")
                utils.vprint(go)
                status = os.system(go)
                if status != 0:
                    utils.vprint(status)
                    self._failure("install")
                    return 0

                # generate other file info, if necessary
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM",
                                    "SRP_PERMS",
                                    "SRP_LINKTARGET"],
                                   self.srp_flags):
                    sys.stdout.write("generating file info...".ljust(69))
                    list = newlist[:]
                    newlist = []
                    for i in list:
                        newlist.append(i)
                        i = sr.SRP_ROOT_PREFIX + i

                        # add checksum line, if configured
                        if utils.any_of_in(["SRP_MD5SUM",
                                            "SRP_SHA1SUM",
                                            "SRP_CHECKSUM"],
                                           self.srp_flags):
                            if os.path.islink(i):
                                utils.vprint("link")
                                newlist.append("link")

                            elif os.path.isdir(i):
                                utils.vprint("dir")
                                newlist.append("dir")

                            else:
                                utils.vprint("normal file")
                                newlist.append(utils.checksum(i))

                        # add file perms line, if configured
                        if "SRP_PERMS" in self.srp_flags:
                            newlist.append(utils.file_perms(i))

                        # add link target line, if configured
                        if "SRP_LINKTARGET" in self.srp_flags:
                            newlist.append(utils.link_target(i))

                    print "[  done  ]"
        
        if not self._finalize(newlist):
            return 0
        
        if "SRP_PREPOSTLIB" in self.srp_flags:
            sys.stdout.write("doing postinstall...".ljust(69))
            try:
                status = self.prepost.postinstall(self)
                if status and status != 1:
                    raise Exception("postinstall() returned %s" % status)
            except Exception, e:
                print "[ failed ]"
                # must actually uninstall now...
                print
                print "*** uninstalling package remains ***"
                print
                sr.PERSISTENT = 1
                self.uninstall()
                return -1
            else:
                print "[  done  ]"
                
        # let's have installations report tally status as well
        sr.TALLY=1
        if not self.check():
            return 0
        
        print "installation complete"
        return 1

    
    def check(self):
        """check() -> status
        checks installation status.
        retval: 1 = success, 0 = failure, -1 = not installed
        """
        sys.stdout.write(string.ljust("verifying...", 69))
        sys.stdout.flush()
        if self.name == "":
            print "[ failed ]"
            print "invalid install file format"
            return -1
        
        size = 0
        numfiles = 0
        missing = []
        modified = []
        temp = os.access(self.logfile, os.F_OK)
        if temp != 1:
            print "[ failed ]"
            print "package is not installed."
            return -1
        
        good = 1
        f = open(self.logfile, 'r')
        # get rid of srp_flags; we already looked at this in the constructor
        f.readline()
        
        file = f.readline().rstrip()
        while file != '':
            file = sr.SRP_ROOT_PREFIX + file
            #check each file...
            utils.vprint("checking: " + file)
            try:
                # get extra info out of logfile

                # get checksum info, if configured
                sum = ""
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM"],
                                   self.srp_flags):
                    sum = f.readline().rstrip()

                # get perms info, if configured
                perms = ""
                if "SRP_PERMS" in self.srp_flags:
                    perms = f.readline().rstrip().split(":")
                    #print "\noriginal: %s" % perms
                    # convert uid to int
                    try:
                        perms[1] = int(perms[1])
                        #print "first try: %s" % perms
                    except:
                        try:
                            perms[1] = pwd.getpwnam(perms[1])[2]
                            #print "second try: %s" % perms
                        except:
                            perms[1] = -1
                            #print "second except: %s" % perms
                    # convert gid to int
                    try:
                        perms[2] = int(perms[2])
                        #print "first try: %s" % perms
                    except:
                        try:
                            perms[2] = grp.getgrnam(perms[2])[2]
                            #print "second try: %s" % perms
                        except:
                            perms[2] = -1
                            #print "second except: %s" % perms
                    # convert the whole thing back into a string
                    #print "before stringing: %s" % perms
                    for i in range(len(perms)):
                        perms[i] = str(perms[i])
                    perms = string.join(perms, ":")
                    #print "final: %s" % perms

                # get linktarget, if configured
                linktarget = ""
                if "SRP_LINKTARGET" in self.srp_flags:
                    linktarget = f.readline().rstrip()

                # get file's actual stats.  an exception will be raised if
                # the file is missing.
                stats = os.lstat(file)

                # check checksum
                temp = utils.checksum(file)
                if sum != "" and sum != "dir" and sum != "link" and sum != temp:
                    utils.vprint("file exists, but checksum failed")
                    modified.append([file, "checksum", sum, temp])

                # check perms
                temp = utils.file_perms(file)
                if perms != "" and perms != temp:
                    utils.vprint("file exists, but permissions changed")
                    modified.append([file, "permissions", perms, temp])

                # check linktarget
                temp = utils.link_target(file)
                if linktarget != "" and linktarget != temp:
                    utils.vprint("symlink exists, but target changed")
                    modified.append([file, "symlink", linktarget, temp])

                # tally, if configured
                if sr.TALLY == 1:
                    utils.vprint("size: %d bytes" % (stats[stat.ST_SIZE]))
                    size = size + stats[stat.ST_SIZE]
                    numfiles = numfiles + 1
                
                utils.vprint("^^ passed ^^")
            except:
                missing.append(file)
                utils.vprint("^^ failed ^^")
            file = f.readline().rstrip()
        f.close()

        # remove potential duplicates from missing and modified
        missing = utils.remove_duplicates(missing)
        modified = utils.remove_duplicates(modified)
        
        if missing != []:
            print "[ failed ]"
            print "package installed but broken: installed file(s) not found"
            print "missing files:"
            for f in missing:
                print f
            print "total missing files: %d files" % (len(missing))
            status = -1

            # we might have missing and modified...
            if modified != []:
                print "some installed files have been modified!"
                print "--- modified files ---"
                for f in modified:
                    print "%s: %s (recorded: %s, actual: %s)" % (f[0], f[1], f[2], f[3])
                print "total modified files: %d files" % (len(modified))

        elif modified != []:
            print "[ passed ]"
            print "some installed files have been modified!"
            print "--- modified files ---"
            for f in modified:
                print "%s: %s (recorded: %s, actual: %s)" % (f[0], f[1], f[2], f[3])
            print "total modified files: %d files" % (len(modified))
            status = 1

        else:
            print "[ passed ]"
            status = 1

        # final tally
        if sr.TALLY == 1:
            stats = os.lstat(self.logfile)
            utils.vprint("getting size of: " + self.logfile)
            utils.vprint(stats[stat.ST_SIZE])
            size = size + stats[stat.ST_SIZE]
            numfiles = numfiles + 1
            
            print "total installed files: %d files" % (numfiles)
            print "total installed size: %s" % (utils.format_size(size))
        
        return status
    
    
    def uninstall(self):
        """uninstall() -> status
        uninstalls the package.
        retval: 1 = success, 0 = failure, -1 = not installed
        """
        status = self.check()
        if status != 1:
            if sr.PERSISTENT == 1:
                print "fighting through errors...  rargh"
            else:
                return -1
            
        f = open(self.logfile, 'r')
        # get rid of srp_flags; we already looked at this in the constructor
        f.readline()
        
        files = []
        file = f.readline().rstrip()
        while file != '':
            files.append(sr.SRP_ROOT_PREFIX + file)

            # strip off checksum line, if configured
            if utils.any_of_in(["SRP_MD5SUM",
                                "SRP_SHA1SUM",
                                "SRP_CHECKSUM"],
                               self.srp_flags):
                f.readline()

            # strip off perms line, if configured
            if "SRP_PERMS" in self.srp_flags:
                f.readline()

            # strip off linktarget line, if configured
            if "SRP_LINKTARGET" in self.srp_flags:
                f.readline()

            file = f.readline().rstrip()
        f.close()
        
        # prune our srp_flags and initialize arguments
        for i in self.srp_flags[:]:
            if "=" in i:
                flagarg = i.split("=")
                x = flagarg[0]
                y = flagarg[1]
                self.srp_flags.remove(i)
                self.srp_flags.append(x)
            else:
                x = i
                y = ""
            if x not in sr.supported_flags:
                print "ERROR: encountered unsupported srp_flag: %s" % (x)
                return -1
            elif y != "":
                if x == "SRP_INPLACE":
                    utils.vprint("initializing self.inplace")
                    self.inplace = sr.SRP_ROOT_PREFIX + y
                elif x == "SRP_LDCONFIG":
                    utils.vprint("initializing self.ldpath")
                    self.ldpath = y.split(',')
        utils.vprint("srp_flags: %s" % (self.srp_flags))
        utils.vprint("inplace: %s" % (self.inplace))
        utils.vprint("ldpath: %s" % (self.ldpath))
        
        # read in the PREPOSTLIB and do preuninstall stuff
        if "SRP_PREPOSTLIB" in self.srp_flags:
            utils.vprint("loading included PREPOSTLIB module...")
            sys.path.append(sr.RUCKUS + "/package/")
            utils.vprint(sys.path)
            temp=self.logfile.split("_--_srp-upgrade-leftovers")[0]
            #print temp
            try:
                os.link(temp + "_-_" + sr.PREPOSTLIB2,
                        sr.RUCKUS + "/package/" + sr.PREPOSTLIB2)
            except:
                pass
            # ^^ we let this exception fly so that install() can call ^^
            #    uninstall even though it already made this link.
            try:
                modname = sr.PREPOSTLIB2.split(".py")[0]
                self.prepost=__import__(modname)

            except:
                # this will also be acceptable.  if this package is upgrade
                # leftovers, the PREPOSTLIB will have been deleted.  just
                # make sure to take SRP_PREPOSTLIB out of self.srp_flags
                self.srp_flags.remove("SRP_PREPOSTLIB")

            else:
                sys.stdout.write("doing preuninstall...".ljust(69))
                try:
                    status = self.prepost.preuninstall(self)
                    if status and status != 1:
                        raise Exception("preuninstall() returned %s" % status)
                except Exception, e:
                    print "[ failed ]"
                    print e
                    if not sr.PERSISTENT:
                        return -1
                else:
                    print "[  done  ]"
        

        sys.stdout.write(string.ljust("removing installed files...", 69))
        sys.stdout.flush()
        
        files.sort()
        files.reverse()
        utils.vprint(files)

        # ok, removal time
        failed = 0
        shared_objects = []
        ldpath_rmlist = []
        for f in files:
            if (os.path.islink(f) or os.path.exists(f)) and f != sr.SRP_ROOT_PREFIX + "dir" and f != sr.SRP_ROOT_PREFIX + "link":
                if os.path.isdir(f) and not os.path.islink(f):
                    if f not in sr.perm_dirs:
                        utils.vprint("trying to rmdir: " + f)
                        try:
                            os.rmdir(f)
                        except:
                            utils.vprint("not empty, which is ok")
                            
                    else:
                        utils.vprint("ignoring: " + f + "  (in perm_dirs[])")
                else:
                    if "SRP_INSTALLINFO" in self.srp_flags:
                        if utils.is_infofile(f):
                            utils.vprint("uninstalling infofile: " + f)
                            go = "install-info --delete " + f + " " + f[:f.find('/info/')] + "/info/dir > /dev/null 2>&1"
                            utils.vprint(go)
                            os.system(go)
                    if "SRP_LDCONFIG" in self.srp_flags and self.ldpath == []:
                        if utils.is_so(f):
                            utils.vprint("so: %s" % f)
                            shared_objects.append(f)
                    
                    if f not in sr.perm_dirs:
                        utils.vprint("trying to unlink: " + f)
                        try:
                            os.unlink(f)
                        except:
                            utils.vprint("failed")
                            failed = failed + 1
                    else:
                        utils.vprint("ignoring: " + f + "  (in perm_dirs[])")
        
        utils.vprint("shared_objects: %s" % shared_objects)
        ldpath = utils.read_ldpath()
        ldpath_orig = ldpath[:]
        utils.vprint("ldpath: %s" % ldpath)
        
        # did we provide ldpath changes manually?
        if self.ldpath != []:
            for i in self.ldpath:
                if i in ldpath:
                    really=0
                    try:
                        if len(os.listdir(sr.SRP_ROOT_PREFIX + i)) == 0:
                            really = 1
                    except:
                        really = 1
                    if really:
                        ldpath.remove(i)
            if ldpath != ldpath_orig:
                utils.vprint("writing new ldpath: " + string.join(ldpath))
                utils.write_ldpath(ldpath)

        else:
            # clean up after autodetected ldpath changes
            for i in shared_objects:
                temp = os.path.dirname(i)
                if sr.SRP_ROOT_PREFIX != "":
                    temp = temp.split(sr.SRP_ROOT_PREFIX)[-1]
                utils.vprint("temp sodir: %s" % temp)
                if temp not in ldpath_rmlist:
                    ldpath_rmlist.append(temp)
            utils.vprint("ldpath_rmlist: %s" % ldpath_rmlist)

            for i in ldpath_rmlist[:]:
                if i in ldpath:
                    really=0
                    try:
                        if len(os.listdir(sr.SRP_ROOT_PREFIX + i)) == 0:
                            really = 1
                    except:
                        really = 1
                    if really:
                        ldpath.remove(i)
                    else:
                        ldpath_rmlist.remove(i)

            utils.vprint("pruned ldpath_rmlist: %s" % ldpath_rmlist)
            if ldpath_rmlist != []:
                utils.vprint("writing new ldpath")
                utils.write_ldpath(ldpath)
        
        if not failed:
            print "[  done  ]"
            sys.stdout.write(string.ljust("removing log file...", 69))
            sys.stdout.flush()
            try:
                os.unlink(self.logfile)
            except:
                print "[ failed ]"
                print "couldn't remove file: " + self.logfile
                return -1
            
            print "[  done  ]"
        else:
            print "[ failed ]"
            print "%d failures, log file NOT removed" % (failed)
            return -1

        if "SRP_PREPOSTLIB" in self.srp_flags:
            sys.stdout.write("doing postuninstall...".ljust(69))
            try:
                status = self.prepost.postuninstall(self)
                if status and status != 1:
                    raise Exception("postuninstall() returned %s" % status)
            except:
                print "[ failed ]"
                if not sr.PERSISTENT:
                    return -1
            else:
                print "[  done  ]"

        print "package successfully uninstalled"
        return 1
    
    
    def upgrade(self):
        """upgrade() -> status
        upgrades a package.
        retval: 1 = success, 0 = failure, -1 = not installed
        """
        if "" != self.inplace and os.path.exists(os.path.join(self.inplace,
                                                              self.dirname)):
            print "ERROR: trying to build inplace in existing directory"
            return -1
        
        status, current, previous = self._check_installed(1)
        if not status:
            return -1
        
        status = self.install(1, current, previous)
        if status == -1:
            # failed, but we should clean up
            # _check_installed() moved our logfile around...  better fix it
            #move /installed/file to /installed/file_--_srp-upgrade-leftovers
            os.link(previous[-1], previous[-1].split("_--_srp-upgrade-leftovers")[0])
            os.unlink(previous[-1])
            return -1
        elif status == 0:
            # failed
            return 0
        
        #prune all previous_versions
        f = file(self.logfile, "r")
        f.readline()  #this gets rid of the "srp_flags" line
        new_files = f.readlines()
        f.close()
        
        for i in previous:
            utils.vprint("pruning previous versions: " + i)
            log = os.path.join(sr.RUCKUS, "installed", i)
            f = file(log, "r")
            srp_flags = f.readline().rstrip().split()
            utils.vprint(srp_flags)

            # iterate over the list of installed files
            old_files = []
            filename = f.readline()
            while filename != '':
                filename = filename.rstrip()
                utils.vprint("filename: " + filename)
                utils.vprint("foo: %s" % os.path.dirname(filename))

                # we renamed PREPOSTLIB (if it existed), so we'll have to do
                # some forgery here.
                temp1 = os.path.join(sr.SRP_ROOT_PREFIX, filename[1:])
                temp2 = log.split("_--_")[0] + "_-_" + sr.PREPOSTLIB2
                utils.vprint("temp1: %s" % temp1)
                utils.vprint("temp2: %s" % temp2)
                if temp1 == temp2:
                    filename += "_--_srp-upgrade-leftovers"
                    utils.vprint("*** actually, filename was: %s" % filename)
                    # we just want to remove the old PREPOSTLIB now
                    os.remove(os.path.join(sr.SRP_ROOT_PREFIX,
                                           filename[1:]))
                    
                    # eat up the checksum line, if it's there
                    if utils.any_of_in(["SRP_MD5SUM",
                                        "SRP_SHA1SUM",
                                        "SRP_CHECKSUM"],
                                       srp_flags):
                        f.readline()

                    # eat up the perms line, if it's there
                    if "SRP_PERMS" in srp_flags:
                        f.readline()

                    # eat up the linktarget line, if it's there
                    if "SRP_LINKTARGET" in srp_flags:
                        f.readline()

                # or is it a leftover file...?
                elif filename + "\n"  not in new_files:
                    utils.vprint("leftover!")
                    old_files.append(filename + "\n")

                    # copy the checksum line, if it's there
                    if utils.any_of_in(["SRP_MD5SUM",
                                        "SRP_SHA1SUM",
                                        "SRP_CHECKSUM"],
                                       srp_flags):
                        sum = f.readline()
                        utils.vprint("checksum: " + sum.rstrip())
                        old_files.append(sum)

                    # copy the perms line, if it's there
                    if "SRP_PERMS" in srp_flags:
                        perms = f.readline()
                        utils.vprint("perms: " + perms.rstrip())
                        old_files.append(perms)

                    # copy the linktarget line, if it's there
                    if "SRP_LINKTARGET" in srp_flags:
                        linktarget = f.readline()
                        utils.vprint("linktarget: " + linktarget.rstrip())
                        old_files.append(linktarget)

                # otherwise, it's a file that's been upgraded
                else:
                    # eat up the checksum line, if it's there
                    if utils.any_of_in(["SRP_MD5SUM",
                                        "SRP_SHA1SUM",
                                        "SRP_CHECKSUM"],
                                       srp_flags):
                        f.readline()

                    # eat up the perms line, if it's there
                    if "SRP_PERMS" in srp_flags:
                        f.readline()

                    # eat up the linktarget line, if it's there
                    if "SRP_LINKTARGET" in srp_flags:
                        f.readline()

                # read the next file...
                filename = f.readline()
            f.close()

            # do something with old_files, if non-emtpy
            utils.vprint(old_files)
            if old_files != []:
                extras = 1

                # check for checksum line
                if utils.any_of_in(["SRP_MD5SUM",
                                    "SRP_SHA1SUM",
                                    "SRP_CHECKSUM"],
                                   srp_flags):
                    extras += 1

                # check for perms line
                if "SRP_PERMS" in srp_flags:
                    extras += 1

                # check for linktarget line
                if "SRP_LINKTARGET" in srp_flags:
                    extras += 1

                print "%s: %d files left behind" % (i, len(old_files)/extras)

                # write the leftovers logfile
                f = open(sr.RUCKUS + "/installed/" + i, "w")
                f.write(string.join(srp_flags) + '\n')
                f.writelines(old_files)
                f.close()
                
            else:
                # no leftovers, nuke the logfile
                os.unlink(sr.RUCKUS + "/installed/" + i)

        return 1




class srp(package):
    """srp
    package class for source ruckus packages
    """
    def __init__(self, filename):
        package.__init__(self)
        self.package_name = os.path.basename(filename)
        self.package_rev = self.package_name.split('-')[-1].split(".srp")[0]
        self._read_notes()
        self.logfile = sr.RUCKUS + "/installed/" + self.name + "_-_" + self.dirname + "_-_" + self.package_rev
        
        if "SRP_MD5SUM" in self.srp_flags:
            sr.CHECKSUM = "md5"
        elif "SRP_SHA1SUM" in self.srp_flags:
            sr.CHECKSUM = "sha1"
    
    
    def info(self):
        """info()
        displays important info about the package.
        retval: none
        """
        print "package name: " + self.package_name
        print
        package.info(self)
    
    
    def build_brp(self, filename, destination):
        """build_brp(filename, destination) -> status
        this will build a brp
        retval: 1 = success, 0 = failure
        """
        # this is a temporary workaround for bug #032
        if "SRP_CANT_FOOL" in self.srp_flags:
            print "ERROR: srp currently does not support building brps from non-foolable srps"
            return -1
        
        # go through the build procedure
        utils.timer_start()
        if "SRP_INPLACE" in self.srp_flags:
            # this is a special case...  /opt style build where the whole
            # source tree is going to be installed somewhere and nothing is
            # installed outside of the source area (i.e. mozilla)

            # make sure inplace dir doesn't already exist
            if os.path.exists(os.path.join(self.inplace, self.dirname)):
                print "ERROR: trying to build inplace in existing directory"
                return -1
            
            # now do the building
            if not self._build_inplace():
                self._failure("build_brp")
                return 0
            #newlist, deps_lib = self._dump(previous, force, fake=1, inplace=1)
            
        else:
            if not self._build():
                self._failure("build_brp")
                return 0
        
        build_time = utils.timer_stop()
        
        # run _dump in fake mode to get log and deps_lib
        #os.chdir(sr.RUCKUS + "/tmp")
        #list = utils.list_files(".")
        if "SRP_INPLACE" in self.srp_flags:
            log, deps_lib = self._dump(fake=1, inplace_log=1)
            location = sr.SRP_ROOT_PREFIX
        else:
            log, deps_lib = self._dump(fake=1)
            location = sr.RUCKUS + "/tmp"
        
        if not log:
            print "cowardly refusing to create an empty package"
            return 0
        
        # prune provided so files out of deps_lib
        sys.stdout.write("mapping dependencies...".ljust(69))
        sys.stdout.flush()
        for i in log:
            utils.vprint(location + i)
            if utils.is_so(location + i):
                utils.vprint("^^^ is so ^^^")
                utils.vprint(os.path.basename(i))
                if os.path.basename(i) in deps_lib:
                    utils.vprint("^^^ is in deps_lib already ^^^")
                    deps_lib.remove(os.path.basename(i))
                else:
                    utils.vprint("^^^ not in deps_lib yet ^^^")
            else:
                utils.vprint("^^^ not an so ^^^")
                
        deps_lib.sort()
        print "[  done  ]"
        
        # create our BLOB
        sys.stdout.write("creating srpblob.tar.bz2...".ljust(69))
        sys.stdout.flush()
        if "SRP_INPLACE" in self.srp_flags:
            if sr.SRP_ROOT_PREFIX:
                os.chdir(sr.SRP_ROOT_PREFIX)
                temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
            else:
                os.chdir("/")
                temp=self.inplace

            location = "." + temp + "/" + self.dirname
        else:
            location = "."

        if not utils.bz2ball_create(os.path.join(sr.RUCKUS,
                                                 "brp",
                                                 sr.BLOB2),
                                    [location]):
            print "[ failed ]"
            return 0
        print "[  done  ]"

        # write FILES
        sys.stdout.write("creating package meta-data...".ljust(69))
        sys.stdout.flush()
        os.chdir(sr.RUCKUS + "/brp")
        try:
            if "SRP_LDCONFIG" in self.srp_flags and self.ldpath != []:
                self.srp_flags.remove("SRP_LDCONFIG")
                self.srp_flags.append("SRP_LDCONFIG=" + string.join(self.ldpath, ','))
            if "SRP_INPLACE" in self.srp_flags:
                self.srp_flags.remove("SRP_INPLACE")
                if sr.SRP_ROOT_PREFIX:
                    temp=self.inplace.split(sr.SRP_ROOT_PREFIX)[-1]
                else:
                    temp=self.inplace
                self.srp_flags.append("SRP_INPLACE=" + temp)
                
            if "SRP_CHECKSUM" in self.srp_flags:
                self.srp_flags.remove("SRP_CHECKSUM")
                if "md5" == sr.CHECKSUM:
                    self.srp_flags.append("SRP_MD5SUM")
                elif "sha1" == sr.CHECKSUM:
                    self.srp_flags.append("SRP_SHA1SUM")

            f = open(sr.FILES2, "w")
            f.write(socket.gethostname() + "\n")
            f.write(utils.timestamp_utc() + "\n")
            f.write(str(build_time) + "\n")
            f.write(utils.contact() + "\n")
            f.write("srp_flags = " + string.join(self.srp_flags) + "\n")
            for i in log:
                f.write(i + "\n")
            f.close()
        except:
            print "[ failed ]"
            print "failed to create logfile"
            return 0
        
        # write DEPS_LIB
        try:
            f = open(sr.DEPS_LIB2, "w")
            for i in deps_lib:
                f.write(i + "\n")
            f.close()
        except:
            print "[ failed ]"
            print "failed to create deps_lib file"
            return 0
        
        # write DEPS_PROG
        if "SRP_DEPS_PROG" in self.srp_flags:
            try:
                os.link(sr.RUCKUS + "/package/" + sr.DEPS_PROG2, sr.DEPS_PROG2)
            except:
                print "[ failed ]"
                print "error copying DEPS_PROG file"
                return 0
        else:
            try:
                f = open(sr.DEPS_PROG2, "w")
                f.close()
            except:
                print "[ failed ]"
                print "error writing DEPS_PROG file"
                return 0
        
        # write DEPS_SRP
        if "SRP_DEPS_SRP" in self.srp_flags:
            try:
                os.link(sr.RUCKUS + "/package/" + sr.DEPS_SRP2, sr.DEPS_SRP2)
            except:
                print "[ failed ]"
                print "error copying DEPS_SRP file"
                return 0
        else:
            try:
                f = open(sr.DEPS_SRP2, "w")
                f.close()
            except:
                print "[ failed ]"
                print "error writing DEPS_SRP file"
                return 0
        
        # grab NOTES
        try:
            os.link(sr.RUCKUS + "/package/" + sr.NOTES2, sr.NOTES2)
        except:
            print "[ failed ]"
            print "error copying NOTES file"
            return 0

        # grab PREPOSTLIB, if necessary
        if "SRP_PREPOSTLIB" in self.srp_flags:
            try:
                os.link(sr.RUCKUS + "/package/" + sr.PREPOSTLIB2,
                        sr.PREPOSTLIB2)
            except:
                print "[ failed ]"
                print "error copying PREPOSTLIB file"
                return 0
        
        # grab OWNEROVERRIDE, if necessary
        if "SRP_OWNEROVERRIDE" in self.srp_flags:
            try:
                os.link(sr.RUCKUS + "/package/" + sr.OWNEROVERRIDE2,
                        sr.OWNEROVERRIDE2)
            except:
                print "[ failed ]"
                print "error copying OWNEROVERRIDE file"
                return 0
        
        print "[  done  ]"
        
        # generate our hosttype string for the package
        hosttype = utils.hosttype()
        if "SRP_ARCH_IND" in self.srp_flags:
            hosttype = hosttype.split('.')[0] + ".any"
        if "SRP_OS_IND" in self.srp_flags:
            hosttype = "any." + hosttype.split('.')[1]
        
        # now, tar up the appropriate files to create the brp
        brp_name = os.path.join(destination,
                                self.package_name.split('.srp')[0])
        brp_name += "." + hosttype + ".brp"

        blarg = "writing brp: " + os.path.basename(brp_name)
        sys.stdout.write(blarg.ljust(69))
        sys.stdout.flush()

        brp_contents = []
        brp_contents.append(sr.NOTES2)
        brp_contents.append(sr.FILES2)
        brp_contents.append(sr.DEPS_LIB2)
        brp_contents.append(sr.DEPS_PROG2)
        brp_contents.append(sr.DEPS_SRP2)
        brp_contents.append(sr.BLOB2)
        if "SRP_PREPOSTLIB" in self.srp_flags:
            brp_contents.append(sr.PREPOSTLIB2)
        if "SRP_OWNEROVERRIDE" in self.srp_flags:
            brp_contents.append(sr.OWNEROVERRIDE2)

        if not utils.tarball_create(brp_name, brp_contents):
            print "[ failed ]"
            return 0
        print "[  done  ]"

        # clean up external dir if we built inplace
        if self.inplace != "":
            utils.vprint("cleaning up external build area")
            go = "rm -rf " + self.inplace + "/" + self.dirname
            #print go
            status = os.system(go)
            if status != 0:
                print "couldn't clean up..."
                return 0
            
            if self.inplace not in sr.perm_dirs:
                try:
                    os.rmdir(self.inplace)
                except:
                    pass
        
        return 1
    


class brp(package):
    """brp
    package class for binary ruckus packages
    """
    
    def __init__(self, filename):
        package.__init__(self)
            
        self.package_name = os.path.basename(filename)
        self.package_rev = self.package_name.split('-')[-1].split(".brp")[0].split('.')[0]
        self.hosttype = string.join(self.package_name.split('.')[-3:-1], ".")

        self.buildhost = ""
        self.builddate = ""
        self.buildtime = ""
        self.buildcontact = ""
        self.file_list = []
        self.deps_lib = []
        self.unsupported_flags = []

        self._read_notes()
        self.logfile = sr.RUCKUS + "/installed/" + self.name + "_-_" + self.dirname + "_-_" + self.package_rev

        self._read_files()
        self._read_deps_lib()
        self._read_deps_prog()
        self._read_deps_srp()
    
    
    def _read_files(self):
        """_read_files()
        this reads all the data out of a brp FILES file
        retval: none
        """
        f = open(sr.RUCKUS + "/package/" + sr.FILES2, 'r')
        self.buildhost = f.readline().rstrip()
        self.builddate = f.readline().rstrip()
        self.buildtime = f.readline().rstrip()
        self.buildcontact = f.readline().rstrip()
        self.srp_flags = f.readline().rstrip().split('srp_flags = ')[-1].split()
        # ^^ this is already initialized by _read_notes()
        #    however, the flags in the FILES file indicate what was actually
        #    _USED_ to generate the package.

        # if the package was built using unsupported flags, puke!
        utils.vprint("srp_flags pre-pruning: %s" % (self.srp_flags))
        for i in self.srp_flags[:]:
            if "=" in i:
                flagarg = i.split("=")
                x = flagarg[0]
                y = flagarg[1]
                self.srp_flags.remove(i)
                self.srp_flags.append(x)
            else:
                x = i
                y = ""
            if x not in sr.supported_flags:
                utils.vprint("dropping unsupported srp_flag: " + x)
                self.srp_flags.remove(x)
                self.unsupported_flags.append(x)
            elif y != "":
                if x == "SRP_INPLACE":
                    utils.vprint("initializing self.inplace")
                    self.inplace = sr.SRP_ROOT_PREFIX + y
                elif x == "SRP_LDCONFIG":
                    utils.vprint("initializing self.ldpath")
                    self.ldpath = y.split(',')

        self.file_list = f.readlines()
        # strip out the carriage returns
        for i in self.file_list:
            self.file_list[self.file_list.index(i)] = i.rstrip()

        if "SRP_MD5SUM" in self.srp_flags:
            sr.CHECKSUM = "md5"
        elif "SRP_SHA1SUM" in self.srp_flags:
            sr.CHECKSUM = "sha1"
        
        f.close()
    
    
    def _read_deps_lib(self):
        """_read_deps_lib()
        this reads all the data out of a brp DEPS_LIB file
        retval: none
        """
        f = open(sr.RUCKUS + "/package/" + sr.DEPS_LIB2, 'r')
        self.deps_lib = f.readlines()
        f.close()
        
        # now prune the carriage returns out
        for i in self.deps_lib:
            self.deps_lib[self.deps_lib.index(i)] = i.rstrip()
    
    
    def _read_deps_prog(self):
        """_read_deps_prog()
        this reads all the data out of a brp DEPS_PROG file
        retval: none
        """
        f = open(sr.RUCKUS + "/package/" + sr.DEPS_PROG2, 'r')
        self.deps_prog = f.readlines()
        f.close()
        
        # now prune the carriage returns out
        for i in self.deps_prog:
            self.deps_prog[self.deps_prog.index(i)] = i.rstrip()
    
    
    def _read_deps_srp(self):
        """_read_deps_srp()
        this reads all the data out of a brp DEPS_SRP file
        retval: none
        """
        f = open(sr.RUCKUS + "/package/" + sr.DEPS_SRP2, 'r')
        self.deps_srp = f.readlines()
        f.close()
        
        # now prune the carriage returns out
        for i in self.deps_srp:
            self.deps_srp[self.deps_srp.index(i)] = i.rstrip()
    
    
    def _check_hosttype(self):
        """_check_hosttype() -> 1 or 0
        checks to see if we are running on a host compatible with target
        retval: 1 = success, 0 = failure
        """
        sys.stdout.write(string.ljust("checking host-type...", 69))
        sys.stdout.flush()
        
        target_os, target_arch  = self.hosttype.split('.')
        host_os, host_arch = utils.hosttype().split('.')
        
        # make sure our os matches
        if target_os != host_os and target_os != "any":
            print "[ failed ]"
            return 0
        
        # take care of our special case comparisons
        if target_arch == "any":
            # architecture independent
            print "[ passed ]"
            return 1
        
        elif re.search("^i\d{3}$", target_arch):
            # intel
            x = int(target_arch[1:])
            y = int(host_arch[1:])
            if y >= x:
                print "[ passed ]"
                return 1
            else:
                print "[ failed ]"
                return 0
        
        # otherwise, we have to have a perfect match
        if target_arch != host_arch:
            print "[ failed ]"
            return 0
    
    
    def _check_deps_lib(self):
        """_check_deps_lib() -> 1 or 0
        checks to see if we have all the libraries listed in deps_lib
        retval: 1 = success, 0 = failure
        """
        sys.stdout.write(string.ljust("checking library dependencies...", 69))
        sys.stdout.flush()
        
        # use dl module if we're not using SRP_ROOT_PREFIX
        if not sr.SRP_ROOT_PREFIX:
            try:
                import dl
                libchecker = utils.check_for_lib_using_dl
            except:
                # dl is only importable if the following is true:
                #   sizeof(int) == sizeof(long) == sizeof(char *)
                # on systems where this isn't the case, we fall back to our
                # compat function (after catching the SystemError)
                libchecker = utils.check_for_lib_compat
        else:
            libchecker = utils.check_for_lib_compat
        
        missing = self.deps_lib[:]
        
        for i in self.deps_lib:
            if libchecker(i):
                missing.remove(i)
        
        if missing:
            print "[ failed ]"
            print "missing libraries:"
            for i in missing:
                print "  -> " + i
            return 0
        print "[ passed ]"
        return 1
    
    
    def _check_deps_prog(self):
        """_check_deps_prog() -> 1 or 0
        checks to see if we have the executables listed in deps_prog
        retval: 1 = success, 0 = failure
        """
        sys.stdout.write(string.ljust("checking program dependencies...", 69))
        sys.stdout.flush()
        
        missing = self.deps_prog[:]
        
        for i in self.deps_prog:
            for j in sr.exec_path:
                file = j + "/" + i
                utils.vprint("looking for %s in %s" % (i, j))
                if os.path.exists(file):
                    utils.vprint("found it!")
                    missing.remove(i)
                    break
        
        if missing:
            print "[ failed ]"
            print "missing executables:"
            for i in missing:
                print "  -> " + i
            return 0
        
        print "[ passed ]"
        return 1
    
    
    def _check_deps_srp(self):
        """_check_deps_srp() -> 1 or 0
        checks to see if we have the executables listed in deps_srp
        retval: 1 = success, 0 = failure
        """
        sys.stdout.write(string.ljust("checking package dependencies...", 69))
        sys.stdout.flush()
        
        missing = self.deps_srp[:]
        
        for i in self.deps_srp:
            if os.path.exists(sr.RUCKUS + "/installed/" + i):
                utils.vprint("found it!")
                missing.remove(i)
                break
        
        if missing:
            print "[ failed ]"
            print "missing packages:"
            for i in missing:
                print "  -> " + i
            return 0
        
        print "[ passed ]"
        return 1
    

    def _forge_srpblob(self):
        """_forge_srpblob()
        changes file ownerships inside srpblob as per self.ownerinfo.  files
        not listed in self.ownerinfo will become owned by the installing user.
        """
        # open the old srpblob
        oldblob = tarfile.open(os.path.join(sr.RUCKUS,
                                            "package",
                                            sr.BLOB2),
                               "r:bz2")
        # open the new srpblob
        newblob = tarfile.open(os.path.join(sr.RUCKUS,
                                            "package",
                                            sr.BLOB2 + ".new"),
                               "w:bz2")
        
        # create the new srpblob from the old one, forging ownership as we go
        for x in oldblob:
            #print x.name
            
            # grab the actual data block from the old tarfile
            f = None
            if not x.islnk() and not x.issym():
                f = oldblob.extractfile(x)
            #print f
            
            # forge the TarInfo object
            if "/%s" % x.name in self.ownerinfo:
                #print "OVERRIDE!"
                uid = self.ownerinfo["/%s" % x.name]
                gid = uid.split(":")[1]
                uid = uid.split(":")[0]
                x.uid = int(uid)
                x.gid = int(gid)
            else:
                x.uid = os.getuid()
                x.gid = os.getgid()
            x.uname = pwd.getpwuid(x.uid)[0]
            x.gname = grp.getgrgid(x.gid)[0]
            #print x
            #print x.uid
            #print x.uname
            #print x.gid
            #print x.gname

            # add TarInfo and data to newblob
            newblob.addfile(x, f)
            #print "added\n"

        # close the files
        oldblob.close()
        newblob.close()
        
        # delete the old srpblob
        os.remove(os.path.join(sr.RUCKUS,
                               "package",
                               sr.BLOB2))
        
        # rename the new srpblob
        os.rename(os.path.join(sr.RUCKUS,
                               "package",
                               sr.BLOB2 + ".new"),
                  os.path.join(sr.RUCKUS,
                               "package",
                               sr.BLOB2))


    def _forge_log(self):
        """_forge_log()
        changes values in log, depending on contents of flags
        """
        forged_log = []

        lines_per_file = 1
        # add one if we have checksum lines
        if utils.any_of_in(["SRP_MD5SUM",
                            "SRP_SHA1SUM",
                            "SRP_CHECKSUM"],
                           self.srp_flags):
            lines_per_file += 1
        # add one if we have perms lines
        if "SRP_PERMS" in self.srp_flags:
            lines_per_file += 1
        # add one if we have linktarget lines
        if "SRP_LINKTARGET" in self.srp_flags:
            lines_per_file += 1

        offset = 1
        # add one if we have checksum lines
        if utils.any_of_in(["SRP_MD5SUM",
                            "SRP_SHA1SUM",
                            "SRP_CHECKSUM"],
                           self.srp_flags):
            offset += 1

        i = 0
        while i < len(self.file_list):
            # make a tuple of the correct number of lines
            file = self.file_list[i:i+lines_per_file]
            #print "file: %s" % file
            # extract perms, forge new uid/gid
            perms = file[offset].split(":")
            #print "original perms: %s" % perms
            #if ("SRP_OWNEROVERRIDE" in self.srp_flags and
            #    file[0] in self.ownerinfo):
            #    perms[1] = self.ownerinfo[file[0]].split(":")[0]
            #    perms[2] = self.ownerinfo[file[0]].split(":")[1]
            #else:
            #    perms[1] = "%d" % os.getuid()
            #    perms[2] = "%d" % os.getgid()
            # ^^^^^ this is all taken care of in _dump(), just fill in the
            # actuall stat() results on the installed file
            #perms = string.join(perms, ":")
            perms = utils.file_perms(os.path.join("/",
                                                  sr.SRP_ROOT_PREFIX,
                                                  file[0][1:]))
            #print "new perms: %s" % perms
            # put forged perms back into the tuple
            file[offset] = perms
            # put each member of the tuple into our forged_log
            for item in file:
                forged_log.append(item)
            i += lines_per_file

        self.file_list = forged_log


    def info(self):
        """info()
        displays important info about the package.
        retval: none
        """
        print "package name: " + self.package_name
        print
        package.info(self)
        print
        print "+---------------+"
        print "| build details |"
        print "+---------------+"
        print "buildhost: " + self.buildhost
        print "hosttype: " + self.hosttype
        print "builddate: " + self.builddate
        print "buildtime: %.2f seconds" % float(self.buildtime)
        print "buildcontact: " + self.buildcontact
        print "file_list: "
        print self.file_list
        print "deps_lib: "
        print self.deps_lib
        print "deps_prog: "
        print self.deps_prog
        print "deps_srp: "
        print self.deps_srp
    
    
    def install(self, force=0, current=[], previous=[]):
        """install(force) -> status
        installs the package. 'force' should only bet passed in (as 1) if
        we're being called from upgrade().
        retval: 1 = success, 0 = failure, -1 = already installed
        """
        if "" != self.inplace and os.path.exists(os.path.join(self.inplace,
                                                              self.dirname)):
            # i almost let this be acceptable...  but if anything goes wrong,
            # the whole directory will get nuked (including any pre-existing
            # user files).  unless i fix this up, installing an inplace brp
            # into an existing directory will *NOT* be allowed
            print "ERROR: trying to install inplace in existing directory"
            return -1
        
        utils.vprint(self.deps_lib)
        
        # first, check our hosttype
        if not self._check_hosttype():
            return -1
        
        # second, check if we're already installed...
        if not force:
            status, current, previous = self._check_installed()
            if not status:
                return -1
        
        # third, check deps_lib
        if not self._check_deps_lib():
            if not sr.PERSISTENT:
                return -1
            else:
                print "installing anyway..."
        
        # fourth, check deps_prog
        if not self._check_deps_prog():
            if not sr.PERSISTENT:
                return -1
            else:
                print "installing anyway..."
        
        # fifth, check deps_srp
        if not self._check_deps_srp():
            if not sr.PERSISTENT:
                return -1
            else:
                print "installing anyway..."
                
        if "SRP_PREPOSTLIB" in self.srp_flags:
            sys.stdout.write("doing preinstall...".ljust(69))
            status = self.prepost.preinstall(self)
            if not status:
                print "[ failed ]"
                return -1
            else:
                print "[  done  ]"

        sys.stdout.write(string.ljust("preparing...", 69))
        sys.stdout.flush()
#        if "SRP_INPLACE" in self.srp_flags:
#            location = self.inplace
#        else:
#            location = sr.RUCKUS + "/tmp"
        location = sr.RUCKUS + "/tmp"

        # change file ownerships in the srpblob, if need be.
        if ("SRP_PERMS" in self.srp_flags and
            "SRP_OWNEROVERRIDE" in self.srp_flags):
            self._forge_srpblob()

        if not utils.bz2ball_extract(os.path.join(sr.RUCKUS,
                                                  "package",
                                                  sr.BLOB2),
                                     location):
            print "[ failed ]"
            self._failure("install", "failed while extracting.  not enough disk space in " + sr.RUCKUS + "...?")
            return 0
        print "[  done  ]"

#        if "SRP_INPLACE" in self.srp_flags:
#            newlist, deps_lib = self._dump(fake=1, inplace=1)
#        else:
#            newlist, deps_lib = self._dump()
        newlist, deps_lib = self._dump(previous, force)
        if not newlist:
            print "didn't install anything?"
            print newlist
            print deps_lib
            self._failure("install")
            return 0

        # before we do our integrity check, we have to do a few things:
        #  - if SRP_PERMS, we have to forge uid/gid to be the installing user
        #  - if SRP_OWNEROVERRIDE, we have to forge uid/gid to be what's
        #    provided in the ownership file
        if "SRP_PERMS" in self.srp_flags:
            self._forge_log()
        
        sys.stdout.write(string.ljust("integrity check...", 69))
        sys.stdout.flush()
        if newlist != self.file_list:
            print "[ failed ]"
            utils.vprint("")
            utils.vprint("documented files: %s" % self.file_list)
            utils.vprint("returned files: %s" % newlist)
            print 
            print "WARNING: actual installed content DOES NOT MATCH content specified by package!"
            print "         it is higly recommended that you immediately uninstall this package"
            print "         and contact the package builder, as this might indicate that someone"
            print "         has tampered with the package."
            print
            print "         maintainer: %s" % self.buildcontact
            print 
        else:
            print "[ passed ]"
        
        if not self._finalize(self.file_list):
            return 0

        if "SRP_PREPOSTLIB" in self.srp_flags:
            sys.stdout.write("doing postinstall...".ljust(69))
            status = self.prepost.postinstall(self)
            if not status:
                print "[ failed ]"
                # must actually uninstall now...
                print
                print "*** uninstalling package remains ***"
                print
                sr.PERSISTENT = 1
                self.uninstall()
                return -1
            else:
                print "[  done  ]"
        
        # let's have installations report tally status as well
        sr.TALLY=1
        if not self.check():
            return 0
        
        print "installation complete"
        return 1
    
    

#---------------------------------------------


def lookup_checksum(filename, log):
    """lookup_checksum(filename, log) -> checksum
    takes a filename and a logfile, returns the checksum for file listed in log
    """
    f = file(log, "r")
    srp_flags = f.readline().rstrip().split("srp_flags = ")[-1].split()
    if not utils.any_of_in(["SRP_MD5SUM",
                            "SRP_SHA1SUM",
                            "SRP_CHECKSUM"],
                           srp_flags):
        return ""
    
    i = f.readline()
    while i != '' and i.rstrip() != filename:
        i = f.readline()
    retval = f.readline().rstrip()
    f.close()
    return retval
