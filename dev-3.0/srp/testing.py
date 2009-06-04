
import utils

class foo(utils.base_obj):

    def __init__(self):
        self.__x = 0
        self.__y = 0

    def init_protected(self):
        print "blah"
        setattr(self, '__z', 0)
        #self.__z = 0


class baz(foo):

    def __init__(self):
        pass


class bar(foo):

    def __init__(self):
        print "bar"
        self.__x = 0
        self.__y = 0
        print "foo"
        #self.init_protected(self)
        print "baz"
