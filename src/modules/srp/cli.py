"""The SRP Command Line Interface.
"""

import argparse
import sys

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

p.add_argument('--root', metavar='ROOTDIR',
               help="""Specifies that we should operate on a filesystem rooted at ROOTDIR.
               This is similar to automake's DESTDIR variable, or srp2's
               SRP_ROOT_PREFIX variable""")

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
    if args.root:
        srp.params.root = args.root
    srp.params.options = args.options

    # mutually-exclusive arguments/flags
    if args.build:
        # check for other required flags
        if not args.src:
            p.error("argument --build: requires --src")

        srp.params.build = srp.BuildParameters(args.build, args.src, args.extra)
        print(srp.params)
        srp.build()

    elif args.install:
        if not args.packages:
            p.error("argument --install: requires PACKAGE(s)")

        for x in args.packages:
            srp.params.install = srp.InstallParameters(x, not args.no_upgrade)
            print(srp.params)
            srp.install()

    elif args.uninstall:
        if not args.packages:
            p.error("argument --uninstall: requires PACKAGE(s)")

        for x in args.packages:
            print("do_uninstall(package={}, options={})".format(x, args.options))
            if not args.dry_run:
                do_uninstall(x, args.options)

    elif args.action:
        if not args.packages:
            p.error("argument --action: requires PACKAGE(s)")

        for x in args.packages:
            print("do_action(package={}, actions={})".format(x, args.action))
            if not args.dry_run:
                do_action(x, args.action)

    elif args.query:
        q_t = []
        q_c = {}
        for x in args.query.split(','):
            if '=' in x:
                x = x.split('=')
                q_c[x[0]] = x[1]
            else:
                q_t.append(x)
        srp.params.query = srp.QueryParameters(q_t, q_c)
        print(srp.params)
        srp.query()

    # NOTE: --list=FOO is just shorthand for --query name,pkg=FOO
    #
    elif args.list != None:
        if not args.list:
            args.list = "*"
        srp.params.query = srp.QueryParameters(["name"],
                                               {"pkg": args.list})
        print(srp.params)
        srp.query()

    elif args.init:
        print("do_init_metadata()")
        if not args.dry_run:
            pass

    elif args.features:
        m = srp.features.get_stage_map(srp.features.registered_features)
        pprint(m)
