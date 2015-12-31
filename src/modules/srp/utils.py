"""random utility functions
"""

import glob
import os

def wrap_text(buf, cols=80, indent=0):
    """Simple formatter that eats up internal line breaks and whitespace, then
    re-line-wraps the text based at `cols' columns with a per-line indent
    of `indent'.

    """
    # create one giant string
    tmp = []
    for line in buf.split("\n"):
        tmp.append(line.strip())
    tmp = " ".join(tmp)
    
    # create an indent string
    indent = "".ljust(indent)
    
    # create lines word-by-word
    out = []
    line = indent
    for word in tmp.split():
        if len(line) + len(word) + 1 < cols:
            if line != indent:
                line += " "
            line += word
        else:
            out.append(line)
            line = indent + word
    out.append(line)
    
    return "\n".join(out)


def expand_path(path):
    """Returns a single, expanded, absolute path.  `path' arg can be shell
    glob, but must result in only a single match.  An exception is raised
    on any globbing errors (e.g., not found, multiple matches) or if the
    resulting path doesn't exist.

    """
    rv = glob.glob(path)
    if not rv:
        raise Exception("no such file - {}".format(path))

    if len(rv) != 1:
        raise Exception("glob had multiple matches - {}".format(path))

    rv = os.path.abspath(rv[0])
    return rv
