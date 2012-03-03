"""main program"""

import argparse


prog = "The Source Ruckus Packager"
version = "3.0.0-alpha1"
build_year = "2012"

desc = """\
%s, version %s
(C) 2001 - %s Michael D Labriola <michael.d.labriola@gmail.com>
""" % (prog, version, build_year)

epi = """\
NOTE: passing in '-' instead of a package name will cause srp to read missing
      arguments from stdin.

example: srp -vvv --install=strip_debug,strip_docs,strip_man something.i686.brp

example: srp --build something.srp

example: srp --query=info,size something

example: srp -l "perl*" | srp --action=strip_debug,strip_docs
"""


p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                            prog='srp',
                            description=desc.rstrip(),
                            epilog=epi.rstrip()
                            )

# one and only one of the following options is required
g = p.add_mutually_exclusive_group(required=True)

g.add_argument('-i', '--install', metavar="OPTIONS", nargs='?',
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
               help="""Uninstall the provided PACKAGE(s).  If PACKAGE isn't
                    installed, this will quietly return successfully (well,
                    it DID get uninstalled at some point).  Can optionally
                    be passed a comma-delimited list of OPTIONS to tailor
                    the uninstall processing (e.g.,
                    --uninstall=no_leftovers).""")

g.add_argument('-q', '--query', metavar="FIELDS", nargs='?',
               help="""Query PACKAGE(s).  Print all the information
                    associated with the specified PACKAGE(S).  Can
                    optionally be passed a comma-delimited list of FIELDS to
                    request only specific information (e.g.,
                    --query=size,date_installed).""")

g.add_argument('-b', '--build', metavar="OPTIONS", nargs='?',
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

g.add_argument('-l', '--list', metavar="PATTERN", nargs='?',
               help="""List installed packages matching regexp PATTERN (or
                    all packages if PATTERN not supplied).""")

g.add_argument('-I', '--init', action='store_true',
               help="Initialize metadata.")

g.add_argument('-V', '--version', action='version',
               version="%s version %s" % (prog, version))


# the following options are independent of the exclusive group (at least as
# far as the ArgumentParser is concerned).
p.add_argument('-v', '--verbose', action='count',
               help="""Be verbose.  Can be supplied multiple times for
                    increased levels of verbosity.""")

p.add_argument('-F', '--force', action='store_true',
               help="""Do things anyway.  For example, this will allow you
                    to 'upgrade' to the same version of what's installed.
                    It can also be used to force installation even if
                    dependencies are not met.""")

p.add_argument('-p', '--package', metavar='PACKAGE', nargs='+',
               help="""Specifies the PACKAGE(s) for --install, --uninstall,
                    --query, --action, and --build.  If left out, packages are
                    expected on stdin.""")

args = p.parse_args()


print(args)
