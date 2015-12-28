"""The SRP Command Line Interface.
"""

# FIXME: waaaaay too much stuff has ended up in this cli module.  once it's
#        been moved to a different module, audit the import statements
#
#        probably move almost everything other than cli parsing into the
#        toplevel srp module (i.e., so we have srp.build instead of
#        srp.cli.do_build)
#
import argparse
import hashlib # do_install
import os # do_install, do_query
import stat # query
import sys
import tarfile # install, query
import time # query
import pickle # query, install
import fnmatch # FIXME: not used yet but should be

from pprint import pprint # FIXME: this was for debug...?

import srp


desc = """\
{}, version {}
(C) 2001-{} Michael D Labriola <michael.d.labriola@gmail.com>
""".format(srp.config.prog, srp.config.version, srp.config.build_year)

epi = """\
example: srp -v --build=foo.notes --src=/path/to/src --copysrc

example: srp --build=foo.notes --src=foo.tar.xz --extra=/path/to/extra/files

example: srp -i --options=strip_debug,strip_docs,strip_man -p foo.i686.brp

example: srp --query=info,size -p foo

example: srp -i foo.brp bar.brp baz.brp

example: srp -l "perl*" | srp --action=strip_debug,strip_docs,commit
"""


p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                            prog='srp',
                            description=desc.rstrip(),
                            epilog=epi.rstrip()
                            )

# one and only one of the following options is required
g = p.add_mutually_exclusive_group(required=True)

g.add_argument('-b', '--build', metavar="NOTES",
               help="""Build package specified by the supplied NOTES file.
                    Resulting binary package will be written to PWD.  Source
                    dir (or source tarball) must also be specified via
                    --src.""")

g.add_argument('-i', '--install', action='store_true',
               help="""Install the provided PACKAGE(s).  If a different
                    version of PACKAGE is already installed, it will be
                    upgraded unless --no-upgrade is set.  Note that upgrade
                    and downgrade are not differentiated (i.e., you can
                    upgrade from version 3 to version 2 of a package even
                    though you'd probably think of that as a downgrade
                    (unless version 3 is broken, of course)).""")

g.add_argument('-B', '--build-and-install', metavar="NOTES",
               help="""Build specified package and then install it.  If built brp already
                    exists and is newer than the NOTES file and the
                    specified sources, the previously built package is
                    installed w/out triggering a re-build.""")

g.add_argument('-u', '--uninstall', action='store_true',
               help="""Uninstall the provided PACKAGE(s).  If PACKAGE isn't
                    installed, this will quietly return successfully (well,
                    it DID get uninstalled at some point).""")

g.add_argument('-q', '--query', metavar="FIELDS", nargs='?',
               const=[],
               help="""Query PACKAGE(s).  Print all the information
                    associated with the specified PACKAGE(S).  Can
                    optionally be passed a comma-delimited list of FIELDS to
                    request only specific information (e.g.,
                    --query=size,date_installed).""")

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

g.add_argument('-l', '--list', metavar="PATTERN", nargs='?', const='*',
               help="""List installed packages matching Unix shell-style
                    wildcard PATTERN (or all packages if PATTERN not
                    supplied).""")

g.add_argument('-I', '--init', action='store_true',
               help="Initialize metadata.")

g.add_argument('-V', '--version', action='version',
               version="{} version {}".format(
                   srp.config.prog, srp.config.version))

g.add_argument('--features', action='store_true',
               help="""Display a summary of all registered features""")


# the following options are independent of the exclusive group (at least as
# far as the ArgumentParser is concerned).
p.add_argument('-v', '--verbose', action='count', default=0,
               help="""Be verbose.  Can be supplied multiple times for
                    increased levels of verbosity.""")

# FIXME: this doesn't force no_deps yet...  only same-version-upgrade...
#
p.add_argument('-F', '--force', action='store_true',
               help="""Do things anyway.  For example, this will allow you
                    to 'upgrade' to the same version of what's installed.
                    It can also be used to force installation even if
                    dependencies are not met.""")

# FIXME: how deep should the dry-run go?  cli parsing?  toplevel mode
#        function?  each individual feature func for each file being acted
#        upon?
#
p.add_argument('-n', '--dry-run', action='store_true',
               help="""Don't actualy do anything, just print what would have
                    been done.""")

p.add_argument('packages', metavar='PACKAGE', nargs='*',
               help="""Specifies the PACKAGE(s) for --install, --uninstall,
               --query, and --action.  Note that PACKAGE can be a Unix
               shell-style wildcard for modes that act on previously
               installed packages (e.g., --uninstall, --query, --action).
               If a specified PACKAGE is '-', additional PACKAGEs are read
               from stdin.""")

p.add_argument('--src', metavar='SRC',
               help="""Specifies the source dir or source tarball to be
               used for --build.""")

p.add_argument('--extra', metavar='DIR',
               help="""Specified an alternate basedir for paths referenced
               in the NOTES file (e.g., extra_content).""")

p.add_argument('--copysrc', action='store_true',
               help="""Used in conjunction with --build and --src w/ an external
               source tree.  By default, external source trees are used as-is
               for out-of-tree building, unless the build_script makes a copy
               explicitly.""")

p.add_argument('--no-upgrade', action='store_true',
               help="""Changes default logic of --install to NOT install if any
               version of the package is already installed.""")

p.add_argument('--options', metavar='OPTIONS', default=[],
               help="""Comma delimited list of extra options to pass into
               --build, --install, or --uninstall.""")


# once we parse our command line arguments, we'll store the results globally
# here
#
# FIXME: might want to put this in some obvious globally available spot so
#        that we car reference our run-time params from within other
#        modules (e.g., deps feature mod for --force)
#
# FIXME: some of the cli flags are currently getting stored in the
#        NotesFile instance, some are getting passed down into
#        functions...  using the NotesFile makes sense, but does also
#        cause the cli flags to get stored in the InstalledPackage
#        instance in the db... which could be helpful I guess.
#
args = None



def parse_package_list():
    # nothing to do unless - was specified
    if '-' not in args.packages:
        return

    # append stdin to supplied package list, after removing the '-'
    args.packages.remove('-')
    args.packages.extend(sys.stdin.read().split())


def parse_options():
    # nothing to do unless we actually got options
    #
    # FIXME: do i need to compare exlictly against [] here to diferentiate
    #        between [] and None?
    if not args.options:
        return

    # parse --options into a list
    args.options = args.options.split(',')


def main():
    global args
    args = p.parse_args()

    print(args)

    # FIXME: actually do something with this verbosity level...
    #
    print("do_init_output(level={})".format(args.verbose))

    parse_package_list()
    parse_options()

    # set global params
    srp.params.verbosity = args.verbose
    srp.params.dry_run = args.dry_run
    srp.params.options = args.options

    # mutually-exclusive arguments/flags
    if args.install:
        if not args.packages:
            p.error("argument --install: requires PACKAGE(s)")

        for x in args.packages:
            print("do_install(package={}, options={})".format(x, args.options))
            if not args.dry_run:
                do_install(x, args.options, not args.no_upgrade, args.force)

    elif args.uninstall:
        if not args.packages:
            p.error("argument --uninstall: requires PACKAGE(s)")

        for x in args.packages:
            print("do_uninstall(package={}, options={})".format(x, args.options))
            if not args.dry_run:
                do_uninstall(x, args.options)

    elif args.build:
        # check for other required flags
        if not args.src:
            p.error("argument --build: requires --src")

        srp.params.build = srp.BuildParameters(args.build, args.src, args.extra)
        print(srp.params)
        srp.build()

    elif args.action:
        if not args.packages:
            p.error("argument --action: requires PACKAGE(s)")

        for x in args.packages:
            print("do_action(package={}, actions={})".format(x, args.action))
            if not args.dry_run:
                do_action(x, args.action)

    elif args.query:
        q_t = []
        q_c = []
        for x in args.query.split(','):
            if '=' in x:
                q_c.append(x)
            else:
                q_t.append(x)
        print("do_query(types={}, criteria={})".format(q_t, q_c))
        if not args.dry_run:
            do_query(q_t, q_c)

    # FIXME: should we just get rid of --list?  or keep it around as a
    #        shortcut to list installed packages by name...?
    elif args.list != None:
        if not args.list:
            args.list = "*"
        print("do_query(types=['name'], criteria=['pkg={}'])".format(args.list))
        if not args.dry_run:
            do_query(types=['name'], criteria=['pkg={}'.format(args.list)])

    elif args.init:
        print("do_init_metadata()")
        if not args.dry_run:
            pass

    elif args.features:
        m = srp.features.get_stage_map(srp.features.registered_features)
        pprint(m)



# /usr/bin/srp (import srp.cli; srp.cli.main(sys.argv))
#
# python-x.y/site/srp/__init__.py
#                    .core/__init__.py (highlevel methods (e.g., install, uninstall)
#                    .cli.py
#                    .package/__init__.py (guts of package types)
#                    .features.py
#                    .features/somefeature.py


def verify_sha(tar):
    sha = hashlib.new("sha1")
    for f in tar:
        if f.name != "SHA":
            sha.update(tar.extractfile(f).read())
    x = sha.hexdigest().encode()
    y = tar.extractfile("SHA").read()
    if x != y:
        raise Exception("SHA doesn't match.  Corrupted archive?")
    return x


def do_install(fname, options, allow_upgrade=True, force=False):
    # create ruckus dir in tmp
    #
    # FIXME: we need to standardize who make the tmp dir... i think the
    #        core build_func makes it during build...
    work = {}
    work['dir'] = srp.features.core.create_tmp_ruckus()

    # extract package contents
    #
    # NOTE: This is needed so that build scripts can access other misc files
    #       they've included in the srp (e.g., apply a patch, install an
    #       externally maintained init script)
    #
    # FIXME: is this still needed now that we've nixed the whole concept
    #        of a source package?
    #
    with tarfile.open(fname) as p:
        # verify SHA
        from_sha = verify_sha(p)
        # verify that requirements are met
        n_fobj = p.extractfile("NOTES")
        n = pickle.load(n_fobj)
        # extract into work dir
        p.extractall(work['dir'] + "/package")

    # check for previously installed version
    #
    # NOTE: The db lookup method(s) return a list of matches to 1) support
    #        fnmatch queries and 2) support having multiple versions of a
    #        package installed.  We don't need to wory about the 1st case
    #        here, because we're passing in an exact package name, but we
    #        do have to wory about the 2nd case.
    #
    #        Why?  We like to be able to have multiple kernel packages
    #        installed, as they generally don't overlap files (except
    #        firmware, possibly) and it's nice to have multiple kernels
    #        managed via the package manager.
    #
    #        This means we need to iterate over a list of possibly more
    #        than 1 installed version.
    #
    prevs = srp.db.lookup_by_name(n.header.name)
    # make sure upgrading is allowed if needed
    if prevs and not allow_upgrade:
        raise Exception("Package {} already installed".format(n.header.name))

    # check for upgrading to identical version (requires --force)
    for prev in prevs:
        if prev.notes.header.fullname == n.header.fullname and not force:
            raise Exception("Package {} already installed, use --force to"
                            " forcefully reinstall or --uninstall and then"
                            " --install".format(n.header.fullname))

    if prevs:
        print("Upgrading to {}".format(n.header.fullname))

    # add installed section to NOTES instance
    n.installed = srp.notes.NotesInstalled(from_sha)

    # update NotesFile with host defaults
    n.update_features(srp.features.default_features)

    # update notes fields with optional command line flags
    n.update_features(options)
    print(n)

    blob = srp.blob.blob(work['dir']+"/package/BLOB")

    # prep our shared work namespace
    #
    # NOTE: This dict gets passed into all the stage funcs (i.e., it's
    #       how they can all share data)
    work['fname'] = fname
    work['notes'] = n
    work['manifest'] = blob.manifest
    work['prevs'] = prevs

    # NOTE: In order to test this (and later on, to test new packages) as an
    #       unprivileged, we need to have to have some sort of fake root
    #       option (e.g., the old SRP_ROOT_PREFIX trick).
    #
    #       I'm waffling between using a DESTDIR environment variable
    #       (because that's what autotools and tons of other Makefiles use)
    #       and adding a --root command line arg (because that's what RPM
    #       does and it's easier to document)
    #
    # FIXME: For now, it's DESTDIR.  Perhaps revisit this later...
    try:
        work["DESTDIR"] = os.environ["DESTDIR"]
    except:
        work["DESTDIR"] = "/"

    # run through install funcs
    stages = srp.features.get_stage_map(n.header.features)
    print("features:", n.header.features)
    print("install funcs:", stages['install'])
    for f in stages['install']:
        # check for notes section class and create if needed
        section = getattr(getattr(srp.features, f.name),
                          "Notes"+f.name.capitalize(), False)
        if section and not getattr(n, f.name, False):
            print("creating notes section:", f.name)
            setattr(n, f.name, section())

        print("executing:", f)
        try:
            f.func(work)
        except:
            print("ERROR: failed feature stage function:", f)
            raise

    # now run through all queued up stage funcs for install_iter
    #
    # FIXME: multiprocessing
    print("install_iter funcs:", stages['install_iter'])
    flist = list(work['manifest'].keys())
    flist.sort()
    for x in flist:
        for f in stages['install_iter']:
            # check for notes section class and create if needed
            section = getattr(getattr(srp.features, f.name),
                              "Notes"+f.name.capitalize(), False)
            if section and not getattr(n, f.name, False):
                print("creating notes section:", f.name)
                setattr(n, f.name, section())

            print("executing:", f, x)
            try:
                f.func(work, x)
            except:
                print("ERROR: failed feature stage function:", f)
                raise

    # commit NOTES to disk in srp db
    #
    # NOTE: We need to refresh our copy of n because feature funcs may have
    #       modified the copy in work[].
    n = work["notes"]

    # commit MANIFEST to disk in srp db
    #
    # NOTE: We need to refresh our copy because feature funcs may have
    #       modified it
    m = work["manifest"]

    # register w/ srp db
    inst = srp.db.InstalledPackage(n, m)
    srp.db.register(inst)

    # commit db to disk
    #
    # FIXME: is there a better place for this?
    srp.db.commit()



# FIXME: what should srp -l output look like?  maybe just like v2's
#        output?  but --raw gives a SHA?


# FIXME: Need to document these query type and criteria ramblings
#        somewhere user-visible...
#
# -q type[,type,...],criteria[,criteria]
#
# valid types:
#   - name (package name w/ version)
#   - info (summary)
#   - files (filenames)
#   - stats (stats for each file)
#   - size (total size of installed package)
#   - raw (super debug all)
#
# valid criteria:
#   - pkg (glob pkgname or path to brp)
#   - file (glob name of installed file)
#   - date_installed (-/+ for before/after)
#   - date_built (-/+ for before/after)
#   - size (-/+ for smaller/larger)
#   - grep (find string in info)
#   - built_by (glob builder name)
#   - built_on (glob built on host)
#
#
# What package installed the specified file:
#   srp -q name,file=/usr/lib/libcrust.so
#
# Show description of installed package
#   srp -q info,pkg=srp-example
#
# List all files installed by package
#   srp -q files,pkg=srp-example
#
# List info,files for package on disk
#   srp -q info,files,pkg=./foo.brp
#
# List packages installed after specified date:
#   srp -q name,date_installed=2015-11-01+
#
#   srp -q name,date_built=2015-11-01+
#
#   srp -q name,size=1M+
#
#   srp -q name,built_by=mike
#
# Search through descriptions for any packages that match a pattern:
#   srp -q name,grep="tools for flabbergasting"
#
# Everything, and I mean everything, about a package:
#   srp -q all,pkg=srp-example
#
def do_query(types, criteria):
    print(types, criteria)
    matches = []
    for c in criteria:
        k,v = c.split("=")
        print("k={}, v={}".format(k, v))
        if k == "pkg":
            # glob pkgname or path to brp
            matches.extend(do_query_pkg(v))
        elif k == "file":
            # glob name of installed file
            matches.extend(do_query_file(v))
        else:
            raise Exception("Unsupported criteria '{}'".format(k))

    print("fetching for all matches: {}".format(types))
    for m in matches:
        for t in types:
            if t == "name":
                print(format_results_name(m))
            elif t == "info":
                print(format_results_info(m))
            elif t == "files":
                print(format_results_files(m))
            elif t == "stats":
                print(format_results_stats(m))
            elif t == "raw":
                print(format_results_raw(m))
            else:
                raise Exception("Unsupported query type '{}'".format(t))


def do_query_pkg(name):
    if os.path.exists(name):
        # query package file on disk
        #
        # FIXME: shouldn't there be a helper func for basic brp-on-disk
        #        access?
        #
        with tarfile.open(name) as p:
            n_fobj = p.extractfile("NOTES")
            n = pickle.load(n_fobj)
            blob_fobj = p.extractfile("BLOB")
            blob = srp.blob.blob(fobj=blob_fobj)
            m = blob.manifest

        return [srp.db.InstalledPackage(n, m)]

    else:
        # query installed package via db
        return srp.db.lookup_by_name(name)


def format_results_name(p):
    return "-".join((p.notes.header.name,
                     p.notes.header.version,
                     p.notes.header.pkg_rev))


def format_results_info(p):
    # FIXME: make this a nice multi-collumn summary of the NOTES file,
    #        excluding build_script, perms, etc
    #
    # FIXME: wrap text according to terminal size for description
    #
    # FIXME: calculate total installed size
    #
    # FIXME: show deps list? or use raw for that?
    #
    info = []
    info.append("Package: {}".format(format_results_name(p)))
    info.append("Description: {}".format(p.notes.header.description))
    
    for f in srp.features.registered_features:
        info_func = srp.features.registered_features[f].info
        if info_func:
            info.append(info_func(p))

    return "\n".join(info)


# FIXME: this seems inefficient
def format_results_files(p):
    m = list(p.manifest)
    m.sort()
    return "\n".join(m)


# NOTE: To test this quickly in interpreter...
#
# import tempfile
# import tarfile
# import stat
# import time
# __tmp = tempfile.TemporaryFile()
# tar = tarfile.open(fileobj=__tmp, mode="w|")
# x = tar.gettarinfo("/etc/fstab")
# y = tar.gettarinfo("/dev/console")
# z = tar.gettarinfo("/dev/stdout")
#
def format_tinfo(t):
    fmt = "{mode} {uid:8} {gid:8} {size:>8} {date} {name}{link}"
    mode = stat.filemode(t.mode)
    uid = t.uname or t.uid
    gid = t.gname or t.gid
    if t.ischr() or t.isblk():
        size = "{},{}".format(t.devmajor, t.devminor)
    else:
        size = t.size
    date = "{}-{:02}-{:02} {:02}:{:02}:{:02}".format(
        *time.localtime(t.mtime)[:6])
    name = t.name + ("/" if t.isdir() else "")
    if t.issym():
        link = " -> " + t.linkname
    elif t.islnk():
        link = " link to " + t.linkname
    else:
        link = ""
    return fmt.format(**locals())


# FIXME: this seems really inefficient
def format_results_stats(p):
    m = list(p.manifest)
    m.sort()
    retval = []
    for f in m:
        tinfo = p.manifest[f]["tinfo"]
        retval.append(format_tinfo(tinfo))
    return "\n".join(retval)


def format_results_raw(p):
    return "{}\n{}".format(
        p.notes,
        p.manifest)
