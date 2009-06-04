"""srp.installer -
This module defines classes responsible for installing packages.
"""


import config
import utils


class v3(utils.base_obj):
    def __init__(self):
        self.__p = None


    def install(self, package_p):
        self.__p = package_p
        try:
            self.__p.prepost.preinstall()
            self.__check_deps()
            self.__install_files()
            self.__p.prepost.postinstall()
            self.__commit()
        finally:
            self.__p = None
