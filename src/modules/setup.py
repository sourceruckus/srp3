from distutils.core import setup, Extension

setup (name = 'blob',
       version = '1.0',
       description = 'C implementation for faster BLOB access',
       ext_modules = [Extension("blob._blob", ["blob.c"])])

