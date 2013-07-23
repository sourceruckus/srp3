#include <Python.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>


static PyObject *blob_extract(PyObject *self, PyObject *args)
{
	const char *bname, *fname;
	unsigned int offset, size;
	char *buf;
	int b, f;

	//printf("parsing args\n");
	if (!PyArg_ParseTuple(args, "ssII", &bname, &fname, &offset, &size))
		return NULL;

	b = open(bname, O_RDONLY);
	if (b == -1) {
		/* FIXME: I should set an appropriate exception */
		return NULL;
	}

	if (lseek(b, offset, SEEK_SET) == -1) {
		/* FIXME: exception */
		return NULL;
	}

	f = open(fname, O_WRONLY | O_CREAT | O_TRUNC);
	if (f == -1) {
		/* FIXME */
		return NULL;
	}

	/* FIXME: I'm sure we could do this more efficiently... Maybe
	 *        read/write 4K at a time or something?
	 */
	buf = malloc(size);
	read(b, buf, size);
	write(f, buf, size);

	close(f);
	close(b);

	Py_RETURN_NONE;
}


static PyMethodDef BlobMethods[] = {
	{"extract",  blob_extract, METH_VARARGS,
	 "Extract a file."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};


static struct PyModuleDef blobmodule = {
	PyModuleDef_HEAD_INIT,
	"blob",   /* name of module */
	"some blob docs", /* module documentation, may be NULL */
	-1,       /* size of per-interpreter state of the module,
		     or -1 if the module keeps state in global variables. */
	BlobMethods
};


PyMODINIT_FUNC
PyInit__blob(void)
{
	return PyModule_Create(&blobmodule);
}
