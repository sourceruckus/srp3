#!/usr/bin/env python3

import configparser
import re
import base64

def encodescript(m):
    return "buf = {}".format(base64.b64encode(m.group(1).encode()).decode())

#def bufferfixer(buf):
#    return re.sub("^[\s]*script[[\s]]*[=:][[\s]]*\"\"\".*(#!.*)\"\"\"", encodescript, buf, flags=re.DOTALL|re.MULTILINE)

def bufferfixer2(buf):
    return re.sub("^%%BUFFER_BEGIN%%\n(.*?)\n%%BUFFER_END%%\n", encodescript, buf, flags=re.DOTALL|re.MULTILINE)

with open("NOTES") as f:
    buf = f.read()

buf = bufferfixer2(buf)

c = configparser.ConfigParser()
c.read_string(buf)

#script = base64.b64decode(c['go-dev']['script'].encode()).decode()
