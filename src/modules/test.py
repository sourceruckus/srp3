#!/usr/bin/env python3

import multiprocessing
import os
import sys
import tarfile
import tempfile

from pprint import pprint

import srp

def f_dict(work):
    pprint(work)
    pprint(dict(work))

    # modify string
    work["name"] += "bar"

    # modify list
    #work["tinfo"].append("boo")
    #work["tinfo"].append("barf")
    #work["tinfo"].extend(["boo", "barf"])
    # NOTE: .append and extend do not work directly, either use +=
    #work["tinfo"] += ["boo"]
    #work["tinfo"] += ["barf"]
    # or copy, tweak, and reassign back to proxy
    tinfo = work["tinfo"]
    tinfo.append("boo")
    tinfo.append("barfoo")
    work["tinfo"] = tinfo

    # modify dict
    #work["work"]["silly"] = "bear"
    m = work["work"]
    m["silly"] = "bear"
    work["work"] = m

    # add new items
    work["flubber"] = "blubber"

    pprint(work)
    pprint(dict(work))


def f_ns(work):
    print(work)

    # modify string
    work.name += "bar"

    # modify list
    #work.tinfo.append("boo")
    #work.tinfo.append("barf")
    #work.tinfo.extend(["boo", "barf"])
    # NOTE: .append and .extend do not work directly, either use +=
    #work.tinfo += ["boo"]
    #work.tinfo += ["barf"]
    # or copy, tweak, and reassign back to proxy
    tinfo = work.tinfo
    tinfo.append("boo")
    tinfo.append("barfoo")
    work.tinfo = tinfo

    # modify dict
    #work.work["silly"] = "bear"
    m = work.work
    m["silly"] = "bear"
    work.work = m

    # add new items
    work.flubber = "blubber"

    print(work)


# TarInfo seems to be ok

# TarFile is ok when backed by tempfile, but not normal file

# open files are not ok


if __name__ == "__main__":
    print("hello")

    m = multiprocessing.Manager()
    doom = m.dict()

    doom['name'] = "foo"
    doom['tinfo'] = ["elem1", "elem2"]
    doom['work'] = {"x": "foo"}
    pprint(doom)
    pprint(dict(doom))


    #doom = m.Namespace()
    #doom.name = "foo"
    #doom.tinfo = ["elem1", "elem2"]
    #doom.work = {'x': "foo"}
    #print(doom)

    p = multiprocessing.Process(target=f_dict, args=(doom,))
    p.start()
    p.join()

    pprint(doom)
    pprint(dict(doom))
    #print(doom)

    #pprint(doom)
    #pprint(dict(doom))

    #doom["tar"] = tarfile.open(fileobj=doom["pkg"], mode="r")
    #print(doom["tar"].getmembers())
    #f = doom["tar"].extractfile("test.py")
    #print(f)
    #buf = f.read()
    #print("--------------------------------------------------------------------------------")
    #print(buf)

    #tar = doom["tar"]
    #pkg = doom["pkg"]
    #print(tar.getmembers())
    #print(tar.list())
    #doom["tar"].close()
    #doom["pkg"].seek(0)
    #with open("blarg.tar", "wb") as f:
    #    f.write(doom["pkg"].read())

    #tar.close()
    #pkg.seek(0)
    #with open("blarg.tar", "wb") as f:
    #    f.write(pkg.read())

    #doom["pkg"].close()
    #pkg.close()
