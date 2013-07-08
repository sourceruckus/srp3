#!/usr/bin/env python3

import multiprocessing
import os
import sys
import tarfile
import tempfile

from pprint import pprint

import srp

def f(work):
    pprint(work)
    pprint(dict(work))

    # modify string
    work["name"] += "bar"

    # modify list
    # NOTE: .append does not work directly, either use +=
    #work["tinfo"] += ["boo"]
    #work["tinfo"] += ["barf"]
    # or copy, tweak, and reassign back to proxy
    tinfo = work["tinfo"]
    tinfo.append("boo")
    tinfo.append("barfoo")
    work["tinfo"] = tinfo

    # modify tarfile
    # .add should not work directly
    #work["tar"].addfile("test.py")
    tar = work["tar"]
    tar.add("test.py")
    work["tar"] = tar

    pprint(work)
    pprint(dict(work))


# TarInfo seems to be ok

# TarFile is ok when backed by tempfile, but not normal file

# open files are not ok


if __name__ == "__main__":
    print("hello")

    m = multiprocessing.Manager()
    doom = m.dict()

    doom['name'] = "foo"
    doom["pkg"] = tempfile.SpooledTemporaryFile()
    #doom["tar"] = tarfile.TarFile("../test.tar")
    doom["tar"] = tarfile.open(fileobj=doom["pkg"], mode="w")
    doom["tinfo"] = doom["tar"].getmembers()
    pprint(doom)
    pprint(dict(doom))

    tar = doom["tar"]
    tar.add("../../README-3.0")
    print(tar.getmembers())
    print(tar.list())
    doom["tar"] = tar
    print(doom["tar"].getmembers())
    print(doom["tar"].list())

    p = multiprocessing.Process(target=f, args=(doom,))
    p.start()
    p.join()
    pprint(doom)
    pprint(dict(doom))

    #doom["tar"] = tarfile.open(fileobj=doom["pkg"], mode="r")
    print(doom["tar"].getmembers())
    #f = doom["tar"].extractfile("test.py")
    #print(f)
    #buf = f.read()
    #print("--------------------------------------------------------------------------------")
    #print(buf)

    tar = doom["tar"]
    pkg = doom["pkg"]
    print(tar.getmembers())
    print(tar.list())
    #doom["tar"].close()
    #doom["pkg"].seek(0)
    #with open("blarg.tar", "wb") as f:
    #    f.write(doom["pkg"].read())

    tar.close()
    pkg.seek(0)
    with open("blarg.tar", "wb") as f:
        f.write(pkg.read())

    #doom["pkg"].close()
    pkg.close()
