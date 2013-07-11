#!/usr/bin/env python3

import multiprocessing
import os
import sys
import tarfile
import tempfile
import time

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
# let's measure RAM utilization by running this as a user that has no other
# processes running, then doing top -u thedude -d1 in another terminal

def foo(work):
    print(work)
    pkg = tarfile.open(fileobj=work["pkg_fobj"])
    print(pkg)
    time.sleep(30)


if __name__ == "__main__":
    print("hello")

    # this time, let's try to create the fobj in RAM in main but free it up
    # after the copy has been made in the manager proc

    # NOTE: we have to create the manager 1st because it dupes mem that then
    #       cannot be garbage collected in the mamager's interpreter
    m = multiprocessing.Manager()
    work = m.dict()

    # 2 procs, 7M (main) and 6M (manager), 1074M free

    # load the entire brp into RAM
    pkg_fobj = tempfile.SpooledTemporaryFile()
    with open(sys.argv[1], "rb") as f:
        pkg_fobj.write(f.read())
    pkg_fobj.seek(0)

    # 2 procs, 84M (main) and 6M (manager), 997M free

    work["pkg_fobj"] = pkg_fobj

    # 2 procs, 84M (main) and 83M (manager), 918M free

    del pkg_fobj

    # 2 procs, 7M (main) and 83M (manager), 996M free

    # get a TarFile object
    #pkg = tarfile.open(fileobj=work["pkg_fobj"])

    # 2 procs, 84M (main) and 83M (manager), 930M free
    #
    # NOTE: i could see one of the python procs ram jump to around 128M for a
    #       second.  and i swear it was 915-ish free the first time i looked at
    #       gkrellm

    # get fobj and TarFile instance for blob
    #blob_fobj = pkg.extractfile("srpblob.tar.bz2")
    #blob = tarfile.open(fileobj=blob_fobj)

    # 2 procs, 90M (main) and 83M (manager), 926M free

    # walked away, came back, 898M free :-/

    # now lets try passing that to a subproc
    #
    # NOTE: if the worker function DOES NOT access the work["pkg_fobj"], the
    #       ammount of RAM free DOES NOT change, even though there's now a 3rd
    #       proc using 84M
    #
    # NOTE: however, if the proc DOES access the fobj (which would be the
    #       point, after all), it consumes an extra 80M of RAM.
    plist=[]
    for x in range(4):
        plist.append(multiprocessing.Process(target=foo, args=(work,)))
        plist[-1].start()
    for p in plist:
        p.join()


# So here's a run-down.  If I have 4 subprocs all accessing a RAM backed fobj
# via manager instance, here's what I get:
#
# main:    10M
# manager: 80M
# sub1:    80M
# sub2:    80M
# sub3:    80M
# sub4:    80M
#--------------
# total:  410M

# test run:
# 1064M free, expect to have 654M free while running

# verfied, 660M free.
