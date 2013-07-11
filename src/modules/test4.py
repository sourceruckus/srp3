#!/usr/bin/env python3

import multiprocessing
import os
import sys
import tarfile
import tempfile
import time
import io
import pickle

import srp

# lets see if we can measure any speedup by untarring from multiple procs.
# there will be tradeoffs...
#
# if each proc has to access the tarfile on disk to seek to it's list of files,
# then we're duplicating disk i/o.
#
# if each proc has a copy of the tarball in RAM, that will use quite a bit of
# RAM, but then the seeking inside the TarFile instansce should be much
# quicker.
#
# we need to quantify how much speed benefit (if any) would be acheived by
# holding the tarball in RAM.
#

# wtf, the in-mem version using SpooledTemporaryFile takes almost 3 times
# longer to extract from! (just using single subproc)
#
# it's just as bad using io.BytesIO... and both methods use a TON more RAM than
# i had expected...
def extractor_mem(tinfo, filename):
    # load the entire tar into RAM
    #pkg_fobj = tempfile.SpooledTemporaryFile()
    pkg_fobj = io.BytesIO()
    with open(filename, "rb") as f:
        pkg_fobj.write(f.read())
    pkg_fobj.seek(0)

    pkg = tarfile.open(fileobj=pkg_fobj)
    for x in tinfo:
        pkg.extract(x)


# hmm... it looks like using a single subproc is slighly faster than 2 (on a
# dual core), even though we're using more CPU... we're talking 54 vs 55
# seconds, so they're practically even... but i was hoping for an
# improvement...
#
# at least iterating over tinfo calling extract isn't slower than extractall...
def extractor_file(tinfo, filename):
    pkg = tarfile.open(filename)
    for x in tinfo:
        #print(multiprocessing.current_process().name, x)
        pkg.extract(x)


if __name__ == "__main__":
    print("hello")

    # NOTE: we have to create the manager 1st because it dupes mem that then
    #       cannot be garbage collected in the mamager's interpreter
    #m = multiprocessing.Manager()
    #work = m.dict()

    pkgfile = sys.argv[1]

    biglist = pickle.load(open("FILES", "rb"))
    sublists = srp.features.core.partition_list(biglist,
                                                multiprocessing.cpu_count())
    print("made", len(sublists), "sublists")

    plist=[]
    for sublist in sublists:
        plist.append(
            multiprocessing.Process(target=extractor_file,
                                    args=(sublist, pkgfile)))
        plist[-1].start()
    for p in plist:
        print("joining:", p)
        p.join()
