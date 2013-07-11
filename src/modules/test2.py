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
    time.sleep(10)


if __name__ == "__main__":
    print("hello")

    # load the entire brp into RAM
    pkg_fobj = tempfile.SpooledTemporaryFile()
    with open(sys.argv[1], "rb") as f:
        pkg_fobj.write(f.read())
    pkg_fobj.seek(0)

    # get a TarFile object
    pkg = tarfile.open(fileobj=pkg_fobj)

    # get fobj and TarFile instance for blob
    blob_fobj = pkg.extractfile("srpblob.tar.bz2")
    blob = tarfile.open(fileobj=blob_fobj)

    # at this point, we have the entire BRP resident in RAM once (i verified
    # that extracting blob_fobj and creating blob doesn't cause the RAM to
    # duplicated).  the largest package we currently install is libreoffice,
    # which weighs in at around 80M.  that plus interpreter and data structure
    # overhead puts us around 90M at this point.

    # now we want to see how badly RAM usage gets if we make that availalbe to
    # a subproc
    m = multiprocessing.Manager()
    # that spawned another proc using about 90M of RAM, but gkrellm didn't
    # report any increase.  i assume that's because this is shared mem.
    work = m.dict()

    # does adding blob to the shared dict increase usage?
    work["blob"] = blob

    # yes.  one proc just jumped to 170M

    # now lets try passing that to a subproc
    p = multiprocessing.Process(target=foo, args=(work,))
    p.start()
    p.join()

    # ok, at this point we have our original proc at 90M, our manager proc at
    # 170M (half of which is shared?), and our child proc at 90M.  but gkrellm
    # didn't notice any difference in available RAM, so the child proc is
    # sharing with the manager proc.

    # 1080M free before
    # 909M free while child executes
    # roughly 170M total usage

    # as expected, that's roughly 2 copies of the libreoffice brp plus about
    # 10M of interpreter and other data stuctures
    
