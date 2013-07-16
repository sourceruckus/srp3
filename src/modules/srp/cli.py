"""The SRP Command Line Interface.
"""

# FIXME: waaaaay too much stuff has ended up in this cli module.  once it's
#        been moved to a different module, audit the import statements
import argparse
import hashlib
import os
import platform
import stat
import sys
import tarfile
import tempfile
import pickle

import srp
from pprint import pprint

desc = """\
{}, version {}
(C) 2001-{} Michael D Labriola <michael.d.labriola@gmail.com>
""".format(srp.config.prog, srp.config.version, srp.config.build_year)

epi = """\
example: srp -v --create=foo.notes

example: srp -vvv --build -p foo.srp

example: srp --install=strip_debug,strip_docs,strip_man -p foo.i686.brp

example: srp --query=info,size -p foo

example: srp -l "perl*" | srp --action=strip_debug,strip_docs,commit
"""


p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                            prog='srp',
                            description=desc.rstrip(),
                            epilog=epi.rstrip()
                            )

# one and only one of the following options is required
g = p.add_mutually_exclusive_group(required=True)

g.add_argument('-c', '--create', metavar="NOTES",
               help="""Create a source package from an SRP NOTES file.""")

g.add_argument('-i', '--install', metavar="OPTIONS", nargs='?',
               const=[],
               help="""Install the provided PACKAGE(s).  If a different
                    version of PACKAGE is already installed, it will be
                    upgraded unless --no-upgrade is set.  Note that upgrade
                    and downgrade are not differentiated (i.e., you can
                    upgrade from version 3 to version 2 of a package even
                    though you'd probably think of that as a downgrade
                    (unless version 3 is broken, of course)).  Can
                    optionally be passed a comma-delimited list of OPTIONS
                    to tailor the install processing (e.g.,
                    --install=no_upgrade,strip_debug).""")

g.add_argument('-u', '--uninstall', metavar="OPTIONS", nargs='?',
               const=[],
               help="""Uninstall the provided PACKAGE(s).  If PACKAGE isn't
                    installed, this will quietly return successfully (well,
                    it DID get uninstalled at some point).  Can optionally
                    be passed a comma-delimited list of OPTIONS to tailor
                    the uninstall processing (e.g.,
                    --uninstall=no_leftovers).""")

g.add_argument('-q', '--query', metavar="FIELDS", nargs='?',
               const=[],
               help="""Query PACKAGE(s).  Print all the information
                    associated with the specified PACKAGE(S).  Can
                    optionally be passed a comma-delimited list of FIELDS to
                    request only specific information (e.g.,
                    --query=size,date_installed).""")

g.add_argument('-b', '--build', metavar="OPTIONS", nargs='?',
               const=[],
               help="""Build PACKAGE.  Resulting binary package will be
                    written to PWD.  Can optionally be passed a
                    comma-delimited list of FIELDS to tailor the build
                    process (e.g.,
                    --build=author=somebody@somewhere,write_dir=/scrap/my_packages).""")

g.add_argument('-a', '--action', metavar="ACTIONS",
               help="""Perform some sort of action on an installed PACKAGE.
                    ACTIONS is a comma-delimited list of actions to be
                    performed (e.g.,
                    --action=strip_debug,strip_docs,commit).""")

# FIXME: need to document supported actions somewhere.  here's a list of the
#        planned ones for now:
#
#        strip_debug - run strip --strip-unneeded on all installed files
#
#        strip_doc - remove installed files in PREFIX/share/doc
#
#        strip_man - remove installed manpages (PREFIX/share/man/)
#
#        strip_info - remove installed info pages (PREFIX/share/info/)
#
#        strip_locale - remove all internationalization translation files
#        (PREFIX/share/locale)
#
#        strip_all - alias to list of all supported strip_* actions
#
#        repair - revert any modified files back to their installed state
#
#        add_file=file - add the specified file to the package's file list
#
#        rm_file=file - remove the specified file from the package's file
#        list
#
#        add_dep_prog=file
#        rm_dep_prog=file
#
#        update_dep_libs - recalculate package library deps by scanning the
#        (potentially updated) list of installed files.
#
#        commit - re-checksum and record package changes

g.add_argument('-l', '--list', metavar="PATTERN", nargs='*',
               help="""List installed packages matching Unix shell-style
                    wildcard PATTERN (or all packages if PATTERN not
                    supplied).""")

g.add_argument('-I', '--init', action='store_true',
               help="Initialize metadata.")

g.add_argument('-V', '--version', action='version',
               version="{} version {}".format(srp.config.prog, srp.config.version))


# the following options are independent of the exclusive group (at least as
# far as the ArgumentParser is concerned).
p.add_argument('-v', '--verbose', action='count', default=0,
               help="""Be verbose.  Can be supplied multiple times for
                    increased levels of verbosity.""")

p.add_argument('-F', '--force', action='store_true',
               help="""Do things anyway.  For example, this will allow you
                    to 'upgrade' to the same version of what's installed.
                    It can also be used to force installation even if
                    dependencies are not met.""")

# FIXME: should -p support fnmatch globbing directly or force users to pass
#        output of srp -l PATTERN in via a pipe...?
#
# FIXME: actually, maybe the other modes should do the matching...  for
#        example, you might want uninstall to double-check that the
#        fnmatch.filter results are actually what the user was expecting
#        before uninstalling them... but a double-check prompt would be
#        silly for --query.
p.add_argument('-p', '--package', metavar='PACKAGE', nargs='+',
               help="""Specifies the PACKAGE(s) for --install, --uninstall,
               --query, --action, and --build.  Note that PACKAGE can be a
               Unix shell-style wildcard for modes that act on previously
               installed packages (e.g., --uninstall, --query, --action).
               If a specified PACKAGE is '-', additional PACKAGEs are read
               from stdin.  If --package is left out entirely, packages are
               expected on stdin.""")


# once we parse our command line arguments, we'll store the results globally
# here
args = None


# FIXME: should i be able to augment package list via stdin? I.e., use
#        --package AND also read more package from stdin.
def get_package_list():
    retval = []

    if args.package:
        retval.extend(args.package)
        if '-' not in retval:
            return retval
        else:
            retval.remove('-')

    # FIXME: for now, we assume that stdin is set up as a pipe if no
    #        packages were specified or if one of the specified pacakges is
    #        '-'.  would be nice if we could tell if this was going to
    #        block...
    retval.extend(sys.stdin.read().split())
    return retval


def main():
    global args
    args = p.parse_args()

    print(args)

    # FIXME: should i just add force as a per-method option instead of a
    #        global option? i.e., --install=strip_debug,force instead of
    #        --install=strip_debug --force.
    #
    # FIXME: kinda undecided, but I think i like --force better. feels a
    #        little strange in some cases (e.g., --action's argument is
    #        called ACTIONS and force would not be an action... it's an
    #        option)
    #
    # FIXME: but maybe we don't want to allow --force for --action...?  just
    #        say that --action is for fixing things that would otherwise
    #        require you to add --force to other comands?

    #force = args.force
    #verbose = args.verbose
    #init = args.init

    # FIXME: we should error out if metadata has not yet been initialized
    #        (unless args.init is set, obviously)

    print("do_init_output(level={})".format(args.verbose))

    if args.install != None:
        if args.install != []:
            args.install = args.install.split(',')
        for x in get_package_list():
            print("do_install(package={}, flags={})".format(x, args.install))
            do_install(x, args.install)

    elif args.uninstall != None:
        if args.uninstall != []:
            args.uninstall = args.uninstall.split(',')
        for x in get_package_list():
            print("do_uninstall(package={}, flags={})".format(x, args.uninstall))

    elif args.build != None:
        if args.build != []:
            args.build = args.build.split(',')
        # NOTE: I'm not sure why you would end up specifying packages to
        #       build on stdin... but we might as well support it
        for x in get_package_list():
            print("do_build(package={}, flags={})".format(x, args.build))
            do_build(x, args.build)

    elif args.action:
        for x in get_package_list():
            print("do_action(package={}, actions={})".format(x, args.action))

    elif args.query != None:
        if args.query != []:
            args.query = args.query.split(',')
        for x in get_package_list():
            print("do_query(package={}, fields={})".format(x, args.query))

    elif args.create:
        print("do_create(notes={})".format(args.create))
        do_create(args.create)

    elif args.list != None:
        if not args.list:
            args.list = ["*"]
        print("do_list(pattern='{}')".format(args.list))

    elif args.init:
        print("do_init_metadata()")


# /usr/bin/srp (import srp.cli; srp.cli.main(sys.argv))
#
# python-x.y/site/srp/__init__.py
#                    .core/__init__.py (highlevel methods (e.g., install, uninstall)
#                    .cli.py
#                    .package/__init__.py (guts of package types)
#                    .features.py
#                    .features/somefeature.py

def do_create(fname):
    with open(fname, 'rb') as fobj:
        n = srp.notes.notes(fobj)

    work = {}
    work["pname"] = "{}-{}-{}.srp".format(n.info.name, n.info.version,
                                          n.info.revision)
    work["notes"] = n

    # run through all queued up stage funcs for create
    m = srp.features.get_stage_map(n.options.features.split())
    print("create funcs:", m['create'])
    for f in m['create']:
        print("executing:", f)
        try:
            f.func(work)
        except:
            print("ERROR: failed feature stage function:", f)
            try:
                os.remove(work["pname"])
            except:
                pass
            raise


def verify_sha(tar):
    sha = hashlib.new("sha1")
    for f in tar:
        if f.name != "SHA":
            sha.update(tar.extractfile(f).read())
    x = sha.hexdigest().encode()
    y = tar.extractfile("SHA").read()
    if x != y:
        raise Exception("SHA doesn't match.  Corrupted archive?")


def do_build(fname, options):
    with tarfile.open(fname) as p:
        # verify SHA
        verify_sha(p)
        # verify that requirements are met
        fobj = p.extractfile("NOTES")
        n = srp.notes.notes(fobj)
        #print(n)

    # FIXME: should the core feature func untar the srp in a tmp dir? or
    #        should we do that here and pass tmpdir in via our work
    #        map...?  i think that's the only reason any of the build
    #        funcs would need the tarfile instance...  might just boil
    #        down to how determined i am to make the feature funcs do as
    #        much of the work as possible...
    #
    #        it might also come down to duplicating code all over the
    #        place... chances are, there's a bunch of places where we'll
    #        need to create the tmpdir and extract a package's
    #        files... in which case we'll rip that out of the core
    #        feature's build_func and put it somewhere else.

    # prep our shared work namespace
    #
    # NOTE: This dict gets passed into all the stage funcs (i.e., it's
    #       how they can all share data)
    work = {}
    work['fname'] = fname

    # NOTE: We do not pass the TarFile instance along because it doesn't
    # play nicely with subproc access...
    #work['srp'] = p

    # append brp section header to NOTES file
    n.additions['brp'] = {}
    work['notes'] = n

    # run through all queued up stage funcs for build
    m = srp.features.get_stage_map(n.options.features.split())
    print("features", n.options.features)
    print("build funcs:", m['build'])
    for f in m['build']:
        print("executing:", f)
        try:
            f.func(work)
        except:
            print("ERROR: failed feature stage function:", f)
            raise

    # now run through all queued up stage funcs for build_iter
    #
    # FIXME: multiprocessing
    print("build_iter funcs:", m['build_iter'])
    flist = list(work['tinfo'].keys())
    flist.sort()
    for x in flist:
        for f in m['build_iter']:
            print("executing:", f, x)
            try:
                f.func(work, x)
            except:
                print("ERROR: failed feature stage function:", f)
                raise

    # create the toplevel brp archive
    #
    # FIXME: compression should be configurable globally and also via
    #        the command line when building.
    mach = platform.machine()
    if not mach:
        mach = "unknown"
    pname = "{}-{}-{}.{}.brp".format(n.info.name, n.info.version,
                                     n.info.revision, mach)
    comp = 'bz2'
    # FIXME: we should remove this file if we fail...
    brp = tarfile.open(pname, mode="w:"+comp)
    sha = hashlib.new("sha1")

    # populate the BLOB archive
    #
    # NOTE: This is where we actually add TarInfo objs and their associated
    #       fobjs to the BLOB, then add the BLOB to the brp archive.
    #
    # NOTE: This is implemented using a temporary file as the fileobj for a
    #       tarfile.  When the fobj is closed it's contents are lost, but
    #       that's fine because we will have already added it to the toplevel
    #       brp archive.
    blob_fobj = tempfile.TemporaryFile()
    blob = tarfile.open("blob", fileobj=blob_fobj, mode="w")

    # FIXME: MULTI: is there any benefit to doing this in parallel?  we would
    #        have to create a bunch of small TarFiles and then concatenate them
    #        at the end...  re-iterating over the sub-tarfiles to create a full
    #        tarfile would probably take way more time than we would have
    #        saved... but we could try it and see.
    #
    # FIXME: Well, if there's no speedup benefit, doing it in parallel would
    #        mean we could do this processing as a build_iter stage...
    #
    # NOTE: We're going to install a cached TarInfo list in the BRP as well.
    #       This will speed up package instantiation come install time.  We're
    #       using the TarInfo objects that have been doctored during our build
    #       stage(s) though so that we retain any extra data that stage funcs
    #       may have stored in the TarInfo objects' dicts.
    files = []
    for x in flist:
        realname = work['dir']+'/tmp/'+x
        tinfo = work['tinfo'][x]
        # NOTE: The fileobj gets x.size bytes read from it, which means we can
        #       blindly pass fobj for file types that don't get any real data
        #       (i.e., because size is 0).
        try:
            fobj = open(realname, 'rb')
        except:
            fobj = None
        blob.addfile(tinfo, fobj)
        files.append(tinfo)

    blob.close()

    # add NOTES file to toplevel pkg archive (the brp)
    n_fobj = tempfile.TemporaryFile()
    n.write(n_fobj)
    n_fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="NOTES", fileobj=n_fobj),
                fileobj=n_fobj)
    # rewind and generate a SHA entry
    n_fobj.seek(0)
    sha.update(n_fobj.read())
    n_fobj.close()

    # add FILES file to toplevel pkg archive
    #
    # NOTE: This cached TarInfo list means that our install processing won't
    #       have to parse to the end of BLOB in order to figure out what files
    #       to install.
    print(files)
    pprint(files)
    files_fobj = tempfile.TemporaryFile()
    for x in files:
        print(x)
        print(dir(x))
        print("type x:", type(x))
        print("type files_fobj:", type(files_fobj))
        print(pickle.dumps(x))
        pickle.dump(obj=x, file=files_fobj)
    files_fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="FILES", fileobj=files_fobj),
                fileobj=files_fobj)
    # rewind and generate a SHA entry
    files_fobj.seek(0)
    sha.update(files_fobj.read())
    files_fobj.close()

    # add BLOB file to toplevel pkg archive
    blob_fobj.seek(0)
    brp.addfile(brp.gettarinfo(arcname="BLOB", fileobj=blob_fobj),
                fileobj=blob_fobj)
    # rewind and generate a SHA entry
    blob_fobj.seek(0)
    sha.update(blob_fobj.read())
    blob_fobj.close()

    # create the SHA file and add it to the pkg
    with tempfile.TemporaryFile() as f:
        f.write(sha.hexdigest().encode())
        f.seek(0)
        brp.addfile(brp.gettarinfo(arcname="SHA", fileobj=f),
                    fileobj=f)

    # close the toplevel brp archive
    brp.close()


def do_install(fname, options):
    with tarfile.open(fname) as p:
        # verify SHA
        verify_sha(p)
        # verify that requirements are met
        fobj = p.extractfile("NOTES")
        n = srp.notes.notes(fobj)

        # update notes fields with optional command line flags
        n.update(options)
        print(n)

        # prep our shared work namespace
        #
        # NOTE: This dict gets passed into all the stage funcs (i.e., it's
        #       how they can all share data)
        work = {}
        work['brp'] = p

        work['notes'] = n

        # this is a map of fobjs to be stored for this package
        #
        # NOTE: it's a map instead of a list so that we can make sure we
        #       have sane file names
        #
        # FIXME: if we're going to allow feature funcs to modify NOTES (as
        #        we do during build), we'll need to do this at the very end.
        #        for now, i'm just using the original NOTES fobj from the
        #        brp.
        work['manifest'] = {"NOTES": fobj}

        # run through install funcs
        m = srp.features.get_stage_map(n.options.features.split())
 
        print("install funcs:", m['install'])
        for f in m['install']:
            print("executing:", f)
            try:
                f.func(work)
            except:
                print("ERROR: failed feature stage function:", f)
                raise

        # commit manifest to disk in srp db
        #
        # FIXME: missing upgrade logic
        #
        # FIXME: should we keep using the SHA from the brp? or should the
        #        SHA for the db entry reflect its actual contents (i.e., if
        #        we change pkg content after install via an action, should
        #        the db SHA change)?  If the latter, perhaps we should add
        #        an "installed_from = SHA" entry to the NOTES file so that
        #        we can trace what exact brp we installed from?
        print("manifest:", work['manifest'])
        path="/var/lib/srp/"+n.info.name+"/"+p.extractfile("SHA").read().decode()
        # FIXME: DESTDIR or --root.  see FIXME in core.install_func...
        try:
            path = os.environ["DESTDIR"] + path
        except:
            pass
        print("path:", path)
        # FIXME: if sha already installed, this will throw OSError
        os.makedirs(path)
        for x in work["manifest"]:
            with open(path+"/"+x, "wb") as f:
                work["manifest"][x].seek(0)
                f.write(work["manifest"][x].read())






# FIXME: what should srp -l output look like?  maybe just like v2's output?  but --raw gives a SHA?

