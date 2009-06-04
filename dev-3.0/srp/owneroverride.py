"""owneroverride
"""


import config
import utils


class v3(utils.base_obj, dict):
    def __init__(self, package_p, filename):
        dict.__init__(self)

        file_p = package_p.extractfile(filename)
        
        line = file_p.readline().strip()
        while line != "":
            temp1 = line.split(":")[0]
            temp2 = ":".join(line.split(":")[1:])
            self[temp1] = temp2
            line = file_p.readline().strip()
        file_p.close()
