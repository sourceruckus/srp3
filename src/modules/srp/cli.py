"""The SRP Command Line Interface.
"""

import argparse
import sys
import tarfile

import srp


prog = "The Source Ruckus Packager"
version = "3.0.0-alpha1"
version_major = 3
version_minor = 0
version_bugfix = 0
build_year = "2013"

# FIXME: should move some of this to config

desc = """\
%s, version %s
(C) 2001-%s Michael D Labriola <michael.d.labriola@gmail.com>
""" % (prog, version, build_year)

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
               const="defaults",
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
               const="defaults",
               help="""Uninstall the provided PACKAGE(s).  If PACKAGE isn't
                    installed, this will quietly return successfully (well,
                    it DID get uninstalled at some point).  Can optionally
                    be passed a comma-delimited list of OPTIONS to tailor
                    the uninstall processing (e.g.,
                    --uninstall=no_leftovers).""")

g.add_argument('-q', '--query', metavar="FIELDS", nargs='?',
               const="defaults",
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
               version="%s version %s" % (prog, version))


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

    print("do_init_output(level=%d)" % args.verbose)

    if args.install:
        for x in get_package_list():
            print("do_install(package=%s, flags=%s)" % (x, args.install.split(',')))

    elif args.uninstall:
        for x in get_package_list():
            print("do_uninstall(package=%s, flags=%s)" % (x, args.uninstall.split(',')))

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
            print("do_action(package=%s, actions=%s)" % (x, args.action.split(',')))

    elif args.query:
        for x in get_package_list():
            print("do_query(package=%s, fields=%s)" % (x, args.query.split(',')))

    elif args.create:
        print("do_create(notes={})".format(args.create))
        do_create(args.create)

    elif args.list != None:
        if not args.list:
            args.list = ["*"]
        print("do_list(pattern='%s')" % (args.list))

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
    print(n)
    
    # FIXME: should we roll up the following check routines into a
    #        notes.check_reqs method?  probably... seems like something we'll
    #        want to do for pretty much every mode...

    # check for required version
    if version_major < n.prereqs.version_major:
        raise Exception("package requires srp >= {}".format(n.prereqs.version))
    elif version_minor < n.prereqs.version_minor:
        raise Exception("package requires srp >= {}".format(n.prereqs.version))
    elif version_bugfix < n.prereqs.version_bugfix:
        raise Exception("package requires srp >= {}".format(n.prereqs.version))

    # check for required features
    missing = n.options.features[:]
    for x in srp.features.registered_features:
        try:
            missing.remove(x)
        except:
            pass
    if missing:
        raise Exception("package requires missing features: {}".format(missing))

    # run through all queued up stage funcs for create
    m = srp.features.get_stage_map(n.options.features)
    print("create funcs:", m['create'])
    for f in m['create']:
        print("executing:", f)
        try:
            f.func(n)
        except:
            print("ERROR: failed feature stage function:", f)
            raise




def do_build(fname, options):
    with tarfile.open(fname) as p:
        # verify that requirements are met
        fobj = p.extractfile("NOTES")
        print(fobj)
        n = srp.notes.notes(fobj)
        print(n)

        # run through all queued up stage funcs for build
        m = srp.features.get_stage_map(n.options.features)
        work = {}
        print("build funcs:", m['build'])
        for f in m['build']:
            print("executing:", f)
            try:
                f.func(n, work)
            except:
                print("ERROR: failed feature stage function:", f)
                raise

        # finalize the built brp
        #
        # NOTE: This is where we actually add TarInfo objs and their associated
        #       fobjs to the BLOB, then add the BLOB to the brp archive.
