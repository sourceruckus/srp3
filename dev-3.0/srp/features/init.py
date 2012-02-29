"""main program"""

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
"""


import argparse

p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                            prog='srp',
                            description=desc.rstrip(),
                            epilog=epi.rstrip()
                            )

g = p.add_mutually_exclusive_group(required=True)

g.add_argument('-i', '--install', metavar="PACKAGE",
               help="""install the provided PACKAGE.  if PACKAGE is already
                    installed, it will be upgraded unless --no-upgrade is set""")

g.add_argument('-u', '--uninstall', metavar="PACKAGE",
               help="""uninstall the provided PACKAGE.  if PACKAGE isn't
                    installed, this will quietly return with a successfully
                    (well, it DID get uninstalled at some point)""")

g.add_argument('-q', '--query', metavar="PACKAGE", nargs='+',
               help="""query PACKAGE.  optionally, specific fields can be
                    requested (e.g., --query=size somepackage)""")

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

p.add_argument('--no-upgrade', action='store_true')
p.add_argument('-v', '--verbose', action='count')
p.add_argument('-F', '--force', action='store_true')

args = p.parse_args()
print(args)
