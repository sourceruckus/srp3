// -*- c-file-style: "k&r"; indent-tabs-mode: nil -*-
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <cstring>
#include <iostream>
using namespace std;

#include "config.h"


int main(int argc, char **argv)
{
    cout << basename(argv[0]) << " " << VERSION << ": hello, world" << endl;
    return 0;
}

