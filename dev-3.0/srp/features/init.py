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

example: srp -vvv --install something.i686.brp

example: srp --build something.srp

example: srp -q something -Q info size
"""


p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                            prog='srp',
                            description=desc.rstrip(),
                            epilog=epi.rstrip()
                            )

# one and only one of the following options is required
g = p.add_mutually_exclusive_group(required=True)

g.add_argument('-i', '--install', metavar="PACKAGE",
               help="""install the provided PACKAGE.  if a different version
                    of PACKAGE is already installed, it will be upgraded
                    unless --no-upgrade is set.  Note that upgrade and
                    downgrade are not differentiated (i.e., you can upgrade
                    from version 3 to version 2 of a package even though
                    you'd probably think of that as a downgrade (unless
                    version 3 is broken, of course))""")

g.add_argument('-u', '--uninstall', metavar="PACKAGE",
               help="""uninstall the provided PACKAGE.  if PACKAGE isn't
                    installed, this will quietly return with a successfully
                    (well, it DID get uninstalled at some point)""")

g.add_argument('-q', '--query', metavar="PACKAGE",
               help="""query PACKAGE.  print all the information associated with
                    the specified PACKAGE.  fields can be limited using the
                    --query-fields option.""")

g.add_argument('-b', '--build', metavar="PACKAGE",
               help="""build PACKAGE.  resulting binary package will be written
                    to PWD""")

g.add_argument('-l', '--list', metavar="PATTERN", nargs='?',
               help="""list installed packages matching regexp PATTERN (or all
                    packages if PATTERN not supplied)""")

g.add_argument('-I', '--init', action='store_true',
               help="initialize metadata")

g.add_argument('-V', '--version', action='version',
               version="%s version %s" % (prog, version))


# the following options are independent of the exclusive group (at least as
# far as the ArgumentParser is concerned).
p.add_argument('-N', '--no-upgrade', action='store_true',
               help="""tells installation processing to fail if different
                    version of PACKAGE is already installed (default behavior is
                    to silently upgrade/downgrade)""")

p.add_argument('-Q', '--query-fields', metavar="QUERY_FIELDS", nargs='+',
               help="""specify specific fields for a query.  if not specified
                    along with --query, all fields are selected.""")

p.add_argument('-v', '--verbose', action='count',
               help="""be verbose.  can be supplied multiple times for increased
                    levels of verbosity""")

p.add_argument('-F', '--force', action='store_true',
               help="""do things anyway.  for example, this will allow you to
                    'upgrade' to the same version of what's installed.  it can
                    also be used to force installation even if dependancies are
                    not met.""")

args = p.parse_args()

# extra argument handling
if args.query_fields and not args.query:
    p.error("--query-fields only valid when combined with --query")

if args.no_upgrade and not args.install:
    p.error("--no-upgrade only valid when combined with --install")

print(args)
