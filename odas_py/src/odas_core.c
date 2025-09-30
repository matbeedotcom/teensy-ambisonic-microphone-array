#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>
#include "odas_wrapper.h"

// Python object wrapper for ODAS processor
typedef struct {
    PyObject_HEAD
    odas_processor_t *processor;
} PyOdasProcessor;

// Deallocator
static void PyOdasProcessor_dealloc(PyOdasProcessor *self) {
    if (self->processor) {
        odas_processor_destroy(self->processor);
        self->processor = NULL;
    }
    Py_TYPE(self)->tp_free((PyObject *)self);
}

// Constructor
static PyObject* PyOdasProcessor_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    PyOdasProcessor *self;
    self = (PyOdasProcessor *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->processor = NULL;
    }
    return (PyObject *)self;
}

// Initialize method
static int PyOdasProcessor_init(PyOdasProcessor *self, PyObject *args, PyObject *kwds) {
    const char *config_file;
    static char *kwlist[] = {"config_file", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &config_file)) {
        return -1;
    }

    self->processor = odas_processor_create(config_file);
    if (!self->processor) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to create ODAS processor");
        return -1;
    }

    return 0;
}

// Start method
static PyObject* PyOdasProcessor_start(PyOdasProcessor *self, PyObject *Py_UNUSED(ignored)) {
    if (!self->processor) {
        PyErr_SetString(PyExc_RuntimeError, "Processor not initialized");
        return NULL;
    }

    if (odas_processor_start(self->processor) != 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to start processor");
        return NULL;
    }

    Py_RETURN_NONE;
}

// Stop method
static PyObject* PyOdasProcessor_stop(PyOdasProcessor *self, PyObject *Py_UNUSED(ignored)) {
    if (!self->processor) {
        PyErr_SetString(PyExc_RuntimeError, "Processor not initialized");
        return NULL;
    }

    if (odas_processor_stop(self->processor) != 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to stop processor");
        return NULL;
    }

    Py_RETURN_NONE;
}

// Is running method
static PyObject* PyOdasProcessor_is_running(PyOdasProcessor *self, PyObject *Py_UNUSED(ignored)) {
    if (!self->processor) {
        PyErr_SetString(PyExc_RuntimeError, "Processor not initialized");
        return NULL;
    }

    if (odas_processor_is_running(self->processor)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

// Method definitions
static PyMethodDef PyOdasProcessor_methods[] = {
    {"start", (PyCFunction)PyOdasProcessor_start, METH_NOARGS,
     "Start ODAS processing threads"},
    {"stop", (PyCFunction)PyOdasProcessor_stop, METH_NOARGS,
     "Stop ODAS processing threads"},
    {"is_running", (PyCFunction)PyOdasProcessor_is_running, METH_NOARGS,
     "Check if processor is running"},
    {NULL}
};

// Type definition
static PyTypeObject PyOdasProcessorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "odas_py._odas_core.OdasProcessor",
    .tp_doc = "ODAS audio processor",
    .tp_basicsize = sizeof(PyOdasProcessor),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = PyOdasProcessor_new,
    .tp_init = (initproc)PyOdasProcessor_init,
    .tp_dealloc = (destructor)PyOdasProcessor_dealloc,
    .tp_methods = PyOdasProcessor_methods,
};

// Module methods
static PyMethodDef module_methods[] = {
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef odas_core_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_odas_core",
    .m_doc = "Native ODAS processing module",
    .m_size = -1,
    .m_methods = module_methods
};

// Module initialization
PyMODINIT_FUNC PyInit__odas_core(void) {
    PyObject *m;

    // Import NumPy
    import_array();

    if (PyType_Ready(&PyOdasProcessorType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&odas_core_module);
    if (m == NULL) {
        return NULL;
    }

    Py_INCREF(&PyOdasProcessorType);
    if (PyModule_AddObject(m, "OdasProcessor", (PyObject *)&PyOdasProcessorType) < 0) {
        Py_DECREF(&PyOdasProcessorType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}