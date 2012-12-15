
data = {}

#def add_file(fname):
#    data[fname] = {"fname": fname}

def add_item(fname, k=None, v=None):
    if fname not in data:
        data[fname] = {}
    if k:
        data[fname][k] = v
