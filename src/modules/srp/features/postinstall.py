"""Feature module for running postinstall script

This feature allows package maintainers to provide an extra scriptlet to
be executed after package installation (e.g., to update some sort of
external database).

"""

import srp.notes
from srp.features import *

import stat
import subprocess


# FIXME: need to document the failure policies somewhere...
#
# error - Package installation continues, further feature funcs are
# attempted, etc, but evenetual retcode will be FAILURE (non-zero).
#
# warning - Warning is printed, everything else continues on its merry
# way.  Eventual retcode is unaffected.
#
# critical - Package installation stops dead?
#
#
# FIXME: well, that's actually not very trivial to implemenent...  for
#        now, "warning" is just a simple warning and "error" is actually
#        what i describes as "criticial".
#
#        if we really want that middle-road error that keeps on going,
#        we'll have to add something to the Features API to let features
#        specify a failure policy for their stage_funcs...
#
class NotesPostinstall(srp.notes.NotesBuffer):
    def __init__(self, config):
        srp.notes.NotesBuffer.__init__(self, config)

        try:
            self.failure_policy = config["failure_policy"].lower()
            if self.failure_policy not in ["error", "warning"]:
                print("invalid postinstall failure_policy:",
                      config["failure_policy"])
                raise Exception("invalid")
        except:
            self.failure_policy = "warning"
            if srp.params.verbosity:
                print("using default postinstall failure_policy:",
                      self.failure_policy)


# NOTE: We need to stick our notes section definition class in the notes
#       module's namespace so that it can be located dynamically in the
#       NotesFile constructor.
#
# FIXME: Need to document this requirement somewhere more obvious...  By the
#        way, this is ONLY needed because we expect stuff for this feature
#        to be parsed from the initial notes file (i.e., if we only add
#        things during build it's not needed).
#
srp.notes.NotesPostinstall = NotesPostinstall


def postinstall():
    """run postinstall script"""
    n = srp.work.install.notes

    script = srp.work.topdir + "/srp_postinstall"

    # create the postinstall script
    with open(script, 'w') as f:
        f.write(n.postinstall.buffer)
        os.chmod(f.name, stat.S_IMODE(os.stat(f.name).st_mode) | stat.S_IXUSR)

    # do it
    try:
        subprocess.call([script], cwd=srp.work.topdir)
    except Exception as ex:
        if n.postinstall.failure_policy == "warning":
            print("WARNING: postinstall failed:", ex)
        elif n.postinstall.failure_policy == "error":
            raise


register_feature(
    feature_struct("postinstall",
                   __doc__,
                   install_final = stage_struct("postinstall", postinstall,
                                                [], ["core"])))
