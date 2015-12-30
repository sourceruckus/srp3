// -*- c-file-style: "k&r"; indent-tabs-mode: nil -*-
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <stdio.h>
#include <string.h>

#include "config.h"
#include "breadcrust.h"


int main(int argc, char **argv)
{
     printf("%s %s with %s crust: hello, world\n", basename(argv[0]), VERSION,
            crustiness);
     return 0;
}
