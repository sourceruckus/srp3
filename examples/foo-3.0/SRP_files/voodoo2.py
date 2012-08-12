def preinstall():
    try:
        print "hello from the other prepostlib"
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)

def postinstall():
    try:
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)

def preuninstall():
    try:
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)

def postuninstall():
    try:
        pass
    except Exception, e:
        raise Exception("failed to do some stuff: %s" % e)
