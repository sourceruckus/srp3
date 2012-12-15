
data = {}

#def add_file(fname):
#    data[fname] = {"fname": fname}

def add_item(fname, k, v):
    if fname not in data:
        data[fname] = {}
    data[fname][k] = v
