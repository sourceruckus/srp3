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
example: srp -v --build foo.notes,src=/path/to/src,copysrc=True

example: srp --build foo.notes,src=foo.tar.xz,extradir=/path/to/extra/files

example: srp -i foo.brp --options=strip_debug,strip_docs,strip_man

example: srp --query=info,size,pkg=foo

example: srp -i foo.brp -i bar.brp -i baz.brp

example: srp --action=strip_debug,strip_docs,commit,pkg=perl*

Note that more than one operational mode can be chained together to create
super-huge-awesome invocations of srp.

example of doom:
    srp -vvv --root $PWD/FOO \\
        -b examples/foo-3.0/srp-example-foo.notes,extradir=examples/foo-3.0 \\
        -b examples/foo-3.0/srp-example-foo-functions.notes,copysrc=True \\
        -b examples/foo-3.0/srp-example-foo-functions-multi.notes \\
        -i srp-example-foo-*-3.*.brp \\
        -B examples/bar-3.0/srp-example-bar.notes,src=examples/bar-3.0 \\
        -q info,stats,pkg=srp-example*

"""


p = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                            prog='srp',
                            description=desc.rstrip(),
                            epilog=epi.rstrip()
                            )

class OrderedMode(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        # record order of the --flag
        try:
            order = getattr(namespace, "OrderedMode")
        except:
            order = []
            setattr(namespace, "OrderedMode", order)
        order.append((option_string, values))

        # append values to the option's attribute
        #
        # NOTE: This is exactly what the "append" action would have done,
        #       and may or may not be needed here.  I'm thinking it may be
        #       handy for resoving deps later on if we have an ordered
        #       list of packages to be installed already generated...
        try:
            val = getattr(namespace, self.dest)
            if val == None:
                raise Excption("boink")
        except:
            val = []
            setattr(namespace, self.dest, val)
        val.append(values)


# one and only one of the following options is required
g = p.add_argument_group("MODE", "Operational Modes of Doom")

g.add_argument('-b', '--build', metavar="NOTES[,key=val,...]",
               action=OrderedMode,
               help="""Build package specified by the supplied NOTES file (and
               optional keyword arguments).  Resulting binary package will be
               written to PWD.""")

g.add_argument('-i', '--install', metavar="PKG[,key=val,...]",
               action=OrderedMode,
               help="""Install package specified by the supplied PKG file (and
               optional keyword arguments).  If a different version of
               PACKAGE is already installed, it will be upgraded unless
               upgrade=False is set.  Note that upgrade and downgrade are
               not differentiated (i.e., you can upgrade from version 3 to
               version 2 of a package even though you'd probably think of
               that as a downgrade (unless version 3 is broken, of
               course)).""")

g.add_argument('-B', '--build-and-install', metavar="NOTES[,key=val,...]",
               action=OrderedMode,
               help="""Build and install the package specified by the supplied
               NOTES file (and optional keyword arguments).
               If the package already exists in PWD and is newer than the
               NOTES file, the previously built package is installed w/out
               triggering a re-build.""")

g.add_argument('-u', '--uninstall', metavar="PKG[,key=val,...]",
               action=OrderedMode,
               help="""Uninstall the provided PACKAGE(s).  If PACKAGE isn't
                    installed, this will quietly return successfully (well,
                    it DID get uninstalled at some point).""")

# FIXME: some way to display all registered query types and criteria?
#
g.add_argument('-q', '--query', metavar="QUERY",
               action=OrderedMode,
               help="""Perform a QUERY.  Format of QUERY is
               type[,type,..],criteria[,criteria,...].  For example,
               info,files,pkg=foo would display info and list of files for
               all packages named "foo".""")

g.add_argument('-a', '--action', metavar="ACTIONS",
               action=OrderedMode,
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

# FIXME: this isn't needed, is it?
#
#g.add_argument('-I', '--init', action='store_true',
#               help="Initialize metadata.")

p.add_argument("--help-build", action="store_true",
               help="""Extra help for --build""")
p.add_argument("--help-install", action="store_true",
               help="""Extra help for --install""")
p.add_argument("--help-uninstall", action="store_true",
               help="""Extra help for --uninstall""")
p.add_argument("--help-query", action="store_true",
               help="""Extra help for --query""")

p.add_argument('-V', '--version', action='version',
               version="{} version {}".format(
                   srp.config.prog, srp.config.version))

# the following options are independent of the exclusive group (at least as
# far as the ArgumentParser is concerned).
p.add_argument('-v', '--verbose', action='count', default=0,
               help="""Be verbose.  Can be supplied multiple times for
                    increased levels of verbosity.""")

# FIXME: this doesn't force no_deps yet...  only same-version-upgrade...
#
# FIXME: i think this is getting replaced w/ specifie kwargs for whatever
#        we would be forcing... wouldn't want to accidentally force the
#        wrong thing, now would we?
#
#p.add_argument('-F', '--force', action='store_true',
#               help="""Do things anyway.  For example, this will allow you
#                    to 'upgrade' to the same version of what's installed.
#                    It can also be used to force installation even if
#                    dependencies are not met.""")

p.add_argument('-n', '--dry-run', action='store_true',
               help="""Don't actualy do anything, just print what would have
               been done.  Go
               through the motions, but Feature stage funcs are not
               executed.""")

p.add_argument('--root', metavar='ROOTDIR',
               help="""Specifies that we should operate on a filesystem rooted
               at ROOTDIR.
               This is similar to automake's DESTDIR variable, or srp2's
               SRP_ROOT_PREFIX variable""")

# FIXME: this might be going away now, too...
#
#p.add_argument('packages', metavar='PACKAGE', nargs='*',
#               help="""Specifies the PACKAGE(s) for --install, --uninstall,
#               --query, and --action.  Note that PACKAGE can be a Unix
#               shell-style wildcard for modes that act on previously
#               installed packages (e.g., --uninstall, --query, --action).
#               If a specified PACKAGE is '-', additional PACKAGEs are read
#               from stdin.""")

# FIXME: rename this to --show-features if we change --options as
#        mentioned...
#
p.add_argument('--features', action='store_true',
               help="""Display a summary of all registered features and exit""")

p.add_argument('-l', '--list', metavar="PATTERN", nargs='?', const='*',
               help="""List installed packages matching Unix shell-style
               wildcard PATTERN (or
               all packages if PATTERN not supplied).  This is really just
               shorthand for --query name,pkg=PATTERN.""")

# FIXME: i think this is going to end up as a list of features to
#        enable/disable at run-time... and if so, it should get renamed to
#        --features... and the old --features flag should end up as
#        --show-features or something like that...
#
p.add_argument('--options', metavar='OPTIONS', default=[],
               help="""Comma delimited list of extra options to pass into
               --build, --install, or --uninstall.""")


# once we parse our command line arguments, we'll store the results globally
# here
#
args = None


# FIXME: this might be dead code... but we might want to be able to read
#        ARGS from stdin?  maybe?
#
#def parse_package_list():
#    # nothing to do unless - was specified
#    if '-' not in args.packages:
#        return
#
#    # append stdin to supplied package list, after removing the '-'
#    args.packages.remove('-')
#    args.packages.extend(sys.stdin.read().split())
#

def parse_options():
    # nothing to do unless we actually got options
    #
    # FIXME: do i need to compare exlictly against [] here to diferentiate
    #        between [] and None?
    if not args.options:
        return

    # parse --options into a list
    args.options = args.options.split(',')


def format_extra_help(mode):
    """Generates extra help message for specified mode, returns it as a
    string.

    """
    # fetch the registered Action for the specified mode from the global
    # ArgumentParser instance
    action = p._option_string_actions[mode]

    # fetch the constructor's doctstring
    thingy = getattr(srp, mode.lstrip('-').capitalize()+"Parameters")
    lines = thingy.__init__.__doc__.split('\n')

    # format it better for cli output
    #
    # NOTE: Find 1st line with leading whitespace (should be 2nd),
    #       calculate the indent level (should be number of leading
    #       spaces), remove that much leading whitespace from each line.
    #
    for line in lines:
        if not line.startswith(' '):
            continue
    lvl = 0
    for x in line:
        if x == ' ':
            lvl += 1
        else:
            break
    out = []
    out.append("srp {} {}".format(mode, action.metavar))
    out.append("")
    out.append(srp.utils.wrap_text(action.help))
    out.append("")
    out.append(lines[0])
    for line in lines[1:]:
        out.append(line[lvl:])

    return "\n".join(out).strip()


def main():
    global args
    args = p.parse_args()

    print(args)

    #parse_package_list()
    parse_options()

    # set global params
    srp.params.verbosity = args.verbose
    srp.params.dry_run = args.dry_run
    if args.root:
        srp.params.root = args.root
    srp.params.options = args.options

    # check for any information-and-exit type flags
    if args.help_build:
        print(format_extra_help("--build"))
        return

    if args.help_install:
        print(format_extra_help("--install"))
        return

    if args.help_uninstall:
        print(format_extra_help("--uninstall"))
        return

    if args.help_query:
        print(format_extra_help("--query"))
        return

    if args.features:
        m = srp.features.get_stage_map(srp.features.registered_features)
        pprint(m)
        return

    if args.list != None:
        if not args.list:
            args.list = "*"
        srp.params.query = srp.QueryParameters(["name"],
                                               {"pkg": args.list})
        print(srp.params)
        srp.query()
        return

    # now iterate over our generated list of operational modes
    for mode in args.OrderedMode:
        mode, arg = mode
        
        if mode == "--build" or mode == "-b":
            arg = arg.split(',')
            kwargs = {"notes": arg[0]}
            for x in arg[1:]:
                k,v = x.split('=')
                kwargs[k] = v
            srp.params.build = srp.BuildParameters(**kwargs)
            print(srp.params)
            srp.build()
            srp.params.build = None

        elif mode == "--install" or mode == "-i":
            arg = arg.split(',')
            kwargs = {"pkg": arg[0]}
            for x in arg[1:]:
                k,v = x.split('=')
                kwargs[k] = v
            srp.params.install = srp.InstallParameters(**kwargs)
            print(srp.params)
            srp.install()
            srp.params.install = None

        elif mode == "--build-and-install" or mode == "-B":
            # we need to do a little extra work here weeding out kwargs
            # for build vs install vs invalid.
            arg = arg.split(',')
            kwargs_b = {"notes": arg[0]}
            kwargs_i = {}
            for x in arg[1:]:
                k,v = x.split('=')
                if k in srp.BuildParameters.__slots__:
                    kwargs_b[k] = v
                elif k in srp.InstallParameters.__slots__:
                    kwargs_i[k] = v
                else:
                    raise Exception("invalid keyword argument: {}".format(k))
            # FIXME: we need to check to see if the package already exists
            #        on disk and is newer then NOTES file... and skip the
            #        actual build if so
            #
            #        if we want to use any of srp.work.build (e.g., to get
            #        at notes to figure out pname below) for the install
            #        part of this, we cannot just SKIP the build...
            #
            srp.params.build = srp.BuildParameters(**kwargs_b)
            print(srp.params)
            srp.build()
            
            # do the install
            #
            # FIXME: if build was --dry-run, the package file won't have
            #        been built... and InstallParameters constructor will
            #        go boom...
            #
            kwargs_i["pkg"] = srp.work.build.notes.brp.pname
            srp.params.install = srp.InstallParameters(**kwargs_i)
            print(srp.params)
            srp.install()
            srp.params.build = None
            psr.params.install = None

        elif mode == "--uninstall" or mode == "-u":
            arg = arg.split(',')
            kwargs = {"pkg": arg[0]}
            for x in arg[1:]:
                k,v = x.split('=')
                kwargs[k] = v
            srp.params.uninstall = srp.UninstallParameters(**kwargs)
            print(srp.params)
            srp.uninstall()
            srp.params.uninstall = None

        elif mode == "--query" or mode == "-q":
            q_t = []
            q_c = {}
            for x in arg.split(','):
                if '=' in x:
                    x = x.split('=')
                    q_c[x[0]] = x[1]
                else:
                    q_t.append(x)
            srp.params.query = srp.QueryParameters(q_t, q_c)
            print(srp.params)
            srp.query()
            srp.params.query = None

        elif mode == "--action" or mode == "-a":
            # FIXME: not implemented
            pass

        else:
            # shouldn't happen?
            raise Exception("invalid usage")

    return
