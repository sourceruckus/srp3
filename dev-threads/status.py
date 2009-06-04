"""status -
this module contains classes for displaying status.

classes:

spinner -- your typical spinning output display
line -- a progress bar
spinner_line -- a progress bar with a spinner
"""

import os, sys, string


class spinner:
    """spinner([head, spinner, cols, tail])
    your typical spinning output display
    
    optional arguments:
        head: a header for the line (default: \"working:\")
        spinner: list of chars depicting the spinner
                 default: ['|', '/', '-', '\\', '|', '/', '-', '\\']
        cols: how many columns on your terminal (default: 80)
        tail: footer for the line (default: \"[  done  ]\")
    
    available methods:
        update()
    """

    def __init__(self, head="working:", spinner=["|", "/", "-", "\\", "|", "/", "-", "\\"],
                 cols=80, tail="[  done  ]"):
        # note that spinner[] is defined to take our spinner through an *entire* loop,
        # even though the second half of the loop is a repeat.  this is so we can determine
        # spin rates based on the length of the spinner[] array
        self.head = head
        self.spinner = spinner
        self.state = 0
        self.maxstate = len(spinner) -1
        #head_s_tail_
        self.size = cols - len(head) - 3
        self.tail = tail

    def info(self):
        print "head:   %s" % (self.head)
        print "spinner:  %s" % (string.join(self.spinner))
        print "state:    %d" % (self.state)
        print "maxstate: %d" % (self.maxstate)
        print "tail:   %s" % (self.tail)

    def update(self, done=0):
        sys.stdout.write("\r")
        if not done:
            sys.stdout.write("%s %s" % (self.head,
                                        self.spinner[self.state]))
        else:
            sys.stdout.write("%s  %s\n" % (self.head,
                                           self.tail.rjust(self.size)))
                    
        sys.stdout.flush()
        self.state = (self.state + 1) % self.maxstate


class line:
    """line([head, full_char, empty_char, cols, tail])
    a progress bar
    
    optional arguments:
        head: a header for the line (default: \"working:\")
        full_char: character used for full spots (default: '#')
        empty_char: character used for empty spots (default: '-')
        cols: how many columns on your terminal (default: 80)
        tail: footer for the line (default: \"[  done  ]\")
    
    available methods:
        update()
    """

    def __init__(self, head="working:", full_char="#", empty_char="-",
                 cols=80, tail="[  done  ]"):
        self.head = head
        self.full_char = full_char
        self.empty_char = empty_char
        #head_[#################---------------]_100%_tail_
        self.size = cols - len(head) - 2 - 7 - len(tail) - 1
        self.tail = tail

    def info(self):
        print "head: %s" % (self.head)
        print "full_char:   %s" % (self.full_char)
        print "empty_char:  %s" % (self.empty_char)
        print "size:   %d" % (self.size)
        print "tail: %s" % (self.tail)

    def update(self, percent):
        hashsize = (percent/100.0) * self.size
        hashline = ""
        while len(hashline) < hashsize:
            hashline = hashline + self.full_char
        while len(hashline) < self.size:
            hashline = hashline + self.empty_char
        
        sys.stdout.write("\r")
        sys.stdout.write("%s [%s] %s%%" % (self.head,
                                           hashline,
                                           str(percent).rjust(3)))
        if percent == 100:
            sys.stdout.write(" %s\n" % (self.tail))
                        
        sys.stdout.flush()


class spinner_line:

    def __init__(self, head="working:", spinner=["|", "/", "-", "\\"],
                 full_char="#", empty_char="-", cols=80, tail="[  done  ]"):
        self.head = head
        self.spinner = spinner
        self.state = 0
        self.maxstate = len(spinner) -1
        self.full_char = full_char
        self.empty_char = empty_char
        #head_s_[#################---------------]_100%_tail_
        self.size = cols - len(head) - 4 - 7 - len(tail) - 1
        self.tail = tail

    def info(self):
        print "head:   %s" % (self.head)
        print "spinner:  %s" % (string.join(self.spinner))
        print "state:    %d" % (self.state)
        print "maxstate: %d" % (self.maxstate)
        print "full_char: %s" % (self.full_char)
        print "empty_char: %s" % (self.empty_char)
        print "size:       %d" % (self.size)
        print "tail:   %s" % (self.tail)

    def update(self, percent):
        hashsize = (percent/100.0) * self.size
        hashline = ""
        while len(hashline) < hashsize:
            hashline = hashline + self.full_char
        while len(hashline) < self.size:
            hashline = hashline + self.empty_char
        
        sys.stdout.write("\r")
        sys.stdout.write("%s %s [%s] %s%%" % (self.head,
                                              self.spinner[self.state],
                                              hashline,
                                              str(percent).rjust(3)))
        if percent == 100:
            sys.stdout.write(" %s\n" % (self.tail))
                        
        sys.stdout.flush()
        self.state = (self.state + 1) % self.maxstate
