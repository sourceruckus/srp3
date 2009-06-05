"""owneroverride
"""


import config
import utils


@utils.tracedmethod("srp.owneroverride")
def init(file_p):
    """create owneroverride instance(s). we will attempt to use the latest
    and greatest, but fall back to the older deprecated class as a
    last resort
    """
    retval_p = None
    tried = []
    to_try = [v3, v2]
    for x in to_try:
        try:
            retval_p = x(file_p)
            break
        except Exception, e:
            tried.append("%s (%s)" % (x, e))
    if retval_p == None:
        err = "Failed to create OWNEROVERRIDE instace(s): %s" % ", ".join(tried)
        raise Exception(err)
    return retval_p



class v3(utils.base_obj, dict):
    def __init__(self, file_p):
        dict.__init__(self)

        if not file_p:
            return

        line = file_p.readline().strip()
        while line != "":
            temp1 = line.split(":")[0]
            temp2 = ":".join(line.split(":")[1:])
            self[temp1] = temp2
            line = file_p.readline().strip()
        file_p.close()


class v2(utils.base_obj, dict):
    def __init__(self, file_p):
        blarg
