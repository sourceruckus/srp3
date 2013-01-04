"""Feature module for the core functionality of SRP.

This feature module implements the core functionality of the package manager
(i.e., creating, building, installing packages).
"""

from srp.features import *

def create_func():
    """create tar of NOTES, source, SHA"""
    pass

def build_func():
    """run build script to create tar of payload"""
    pass

def install_func():
    """untar payload, install tarinfo in ruckus/installed/pkgname/sha"""
    pass

def uninstall_func():
    """remove files listed in pkg manifest"""
    pass

def commit_func():
    """update pkg manifest"""
    pass

register_feature(feature_struct("core",
                                __doc__,
                                create = stage_struct("core", create_func, [], []),
                                build = stage_struct("core", build_func, [], []),
                                install = stage_struct("core", install_func, [], []),
                                uninstall = stage_struct("core", uninstall_func, [], []),
                                action = [("commit", stage_struct("core", commit_func, [], []))]))
