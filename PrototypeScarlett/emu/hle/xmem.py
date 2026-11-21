"""xmem.dll en mode isolé : allocateur mémoire de la console sur le tas émulé.

Même règle d'alignement que le runtime C++ (runtime/xmem/xmem.cpp).
"""
from .core import hle

SMALL_ALIGNMENT = 64
PAGE_ALIGNMENT = 4096
ERROR_NOT_SUPPORTED = 50


@hle("xmem", "XMemAlloc", "XMemAllocDefault")
def xmem_alloc(c):
    size = c.arg(0) or 1
    return c.heap.alloc(size, PAGE_ALIGNMENT if size >= PAGE_ALIGNMENT else SMALL_ALIGNMENT)


@hle("xmem", "XMemFree", "XMemFreeDefault")
def xmem_free(c):
    if c.arg(0):
        c.heap.free(c.arg(0))


@hle("xmem")
def XMemGetWorkingSetStatistics(c):
    """Structure non publique : échec signalé, comme dans le runtime C++."""
    c.machine.last_error = ERROR_NOT_SUPPORTED
    return 0
