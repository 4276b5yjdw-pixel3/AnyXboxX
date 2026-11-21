"""Runtime C++ (runtime/) : les DLL qui remplacent xgameruntime, xmem et d3d12_xs."""
import ctypes
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="DLL Windows x64")

S_OK, E_NOINTERFACE = 0, 0x80004002
XBOX_SCARLETT_ANACONDA = 7
MEM_COMMIT = 0x1000
ROOT_SIGNATURE_VERSION_1_0 = 1


def load(runtime_dir, name):
    return ctypes.WinDLL(str(runtime_dir / name))


def test_runtime_answers_like_a_series_x(runtime_dir):
    runtime = load(runtime_dir, "xgameruntime.dll")
    runtime.QueryApiImpl.restype = ctypes.c_uint32
    assert runtime.QueryApiImpl(None, None, None, None) == E_NOINTERFACE
    assert runtime.XSystemGetDeviceType() == XBOX_SCARLETT_ANACONDA
    assert runtime.XGameRuntimeInitialize() == S_OK


def test_xmem_alloc_is_aligned_and_queryable(runtime_dir):
    xmem = load(runtime_dir, "xmem.dll")
    xmem.XMemAlloc.restype = ctypes.c_void_p
    xmem.XMemAlloc.argtypes = (ctypes.c_size_t, ctypes.c_uint64)
    xmem.XMemFree.argtypes = (ctypes.c_void_p, ctypes.c_uint64)
    small, large = xmem.XMemAlloc(100, 0), xmem.XMemAlloc(8192, 0)
    try:
        assert small and small % 64 == 0
        assert large and large % 4096 == 0
        ctypes.memset(large, 0xAB, 8192)

        class MemoryInfo(ctypes.Structure):
            _fields_ = [("base", ctypes.c_void_p), ("allocation_base", ctypes.c_void_p),
                        ("allocation_protect", ctypes.c_uint32), ("partition", ctypes.c_uint16),
                        ("region_size", ctypes.c_size_t), ("state", ctypes.c_uint32),
                        ("protect", ctypes.c_uint32), ("type", ctypes.c_uint32)]

        info = MemoryInfo()
        xmem.XMemVirtualQuery.restype = ctypes.c_size_t
        xmem.XMemVirtualQuery.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
        assert xmem.XMemVirtualQuery(large, ctypes.byref(info), ctypes.sizeof(info)) == ctypes.sizeof(info)
        assert info.state == MEM_COMMIT
    finally:
        xmem.XMemFree(small, 0)
        xmem.XMemFree(large, 0)


def test_xmem_working_set_statistics_report_unavailable(runtime_dir):
    xmem = load(runtime_dir, "xmem.dll")
    assert xmem.XMemGetWorkingSetStatistics(0, ctypes.create_string_buffer(256)) == 0


def test_d3d12_xs_serializes_root_signature_through_pc_d3d12(runtime_dir):
    d3d12_xs = load(runtime_dir, "d3d12_xs.dll")
    serialize = d3d12_xs.D3D12SerializeVersionedRootSignature
    serialize.restype = ctypes.c_uint32
    serialize.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p))
    desc = (ctypes.c_uint32 * 16)()          # D3D12_VERSIONED_ROOT_SIGNATURE_DESC vide
    desc[0] = ROOT_SIGNATURE_VERSION_1_0
    blob, error = ctypes.c_void_p(), ctypes.c_void_p()
    assert serialize(desc, ctypes.byref(blob), ctypes.byref(error)) == S_OK
    vtable = ctypes.cast(ctypes.cast(blob, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vtable[4])(blob)   # ID3DBlob::GetBufferSize
    ctypes.WINFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p)(vtable[2])(blob)           # Release
    assert size > 0


def test_xmem_frees_each_block_with_the_allocator_that_made_it(runtime_dir):
    """Un bloc alloué avant XMemSetAllocationHooks ne doit jamais partir dans le crochet du jeu."""
    xmem = load(runtime_dir, "xmem.dll")
    alloc_type = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint64)
    free_type = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint64)
    pool = ctypes.create_string_buffer(256)
    freed = []
    hook_alloc = alloc_type(lambda size, attributes: ctypes.addressof(pool))
    hook_free = free_type(lambda address, attributes: freed.append(address))
    xmem.XMemAlloc.restype = ctypes.c_void_p
    xmem.XMemAlloc.argtypes = (ctypes.c_size_t, ctypes.c_uint64)
    xmem.XMemFree.argtypes = (ctypes.c_void_p, ctypes.c_uint64)
    xmem.XMemSetAllocationHooks.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    before = xmem.XMemAlloc(64, 0)
    xmem.XMemSetAllocationHooks(ctypes.cast(hook_alloc, ctypes.c_void_p), ctypes.cast(hook_free, ctypes.c_void_p))
    try:
        hooked = xmem.XMemAlloc(32, 0)
        assert hooked == ctypes.addressof(pool)
        xmem.XMemFree(before, 0)            # bloc par défaut : libéré par AnyXboxX
        assert freed == []
        xmem.XMemFree(hooked, 0)            # bloc du jeu : rendu à son crochet
        assert freed == [hooked]
    finally:
        xmem.XMemSetAllocationHooks(None, None)


SYSTEM_RUNTIME = __import__("pathlib").Path(__import__("os").environ.get("SystemRoot", r"C:\Windows")) / "System32" / "xgameruntime.dll"


def _runtime_in_subprocess(runtime_dir, system_runtime):
    """QueryApiImpl et InitializeApiImplEx2 dans un processus neuf (l'option est lue une fois)."""
    import os
    import subprocess

    script = (
        "import ctypes, sys; r = ctypes.WinDLL(sys.argv[1]); r.QueryApiImpl.restype = ctypes.c_uint32;"
        "r.InitializeApiImplEx2.restype = ctypes.c_uint32; g = (ctypes.c_ubyte * 16)(*range(16));"
        "o = ctypes.c_void_p(); print(r.QueryApiImpl(g, g, ctypes.byref(o), None), o.value)")
    env = {**os.environ, "ANYXBOXX_SYSTEM_RUNTIME": system_runtime}
    out = subprocess.run([sys.executable, "-c", script, str(runtime_dir / "xgameruntime.dll")],
                         capture_output=True, text=True, env=env, check=True).stdout.split()
    return int(out[0]), out[1]


def test_without_windows_runtime_unknown_interfaces_are_refused(runtime_dir):
    assert _runtime_in_subprocess(runtime_dir, "0") == (E_NOINTERFACE, "None")


@pytest.mark.skipif(not SYSTEM_RUNTIME.is_file(), reason="runtime GDK de Windows absent")
def test_unknown_interface_delegated_to_windows_fails_cleanly(runtime_dir):
    code, pointer = _runtime_in_subprocess(runtime_dir, "1")
    assert code & 0x8000_0000 and pointer == "None"


TASK_QUEUE_GUID = bytes.fromhex("cb7d3b07cf1f304094bee3c9eb623428")   # {073B7DCB-…} en mémoire
MANUAL, THREAD_POOL = 0, 1
WORK_PORT = 0
CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_bool)
ASYNC_WORK = ctypes.WINFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p)


class AsyncBlock(ctypes.Structure):
    _fields_ = [("queue", ctypes.c_void_p), ("context", ctypes.c_void_p),
                ("callback", ctypes.c_void_p), ("internal", ctypes.c_ubyte * 32)]


class TaskQueueApi:
    """L'interface vue comme le jeu la voit : méthode n° k de l'objet rendu par QueryApiImpl."""

    def __init__(self, runtime_dir):
        runtime = load(runtime_dir, "xgameruntime.dll")
        runtime.QueryApiImpl.restype = ctypes.c_uint32
        guid = (ctypes.c_ubyte * 16).from_buffer_copy(TASK_QUEUE_GUID)
        self.object = ctypes.c_void_p()
        assert runtime.QueryApiImpl(guid, guid, ctypes.byref(self.object), None) == S_OK
        self.vtable = ctypes.cast(ctypes.cast(self.object, ctypes.POINTER(ctypes.c_void_p))[0],
                                  ctypes.POINTER(ctypes.c_void_p))

    def method(self, index, restype, *argtypes):
        function = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(self.vtable[index])
        return lambda *args: function(self.object, *args)


def test_task_queue_is_served_by_anyxboxx_and_dispatches_callbacks(runtime_dir):
    api = TaskQueueApi(runtime_dir)
    create = api.method(12, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
    submit = api.method(18, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, CALLBACK)
    dispatch = api.method(16, ctypes.c_bool, ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32)
    close = api.method(17, None, ctypes.c_void_p)
    queue = ctypes.c_void_p()
    assert create(MANUAL, MANUAL, ctypes.byref(queue)) == S_OK
    calls = []
    callback = CALLBACK(lambda context, canceled: calls.append((context, canceled)))
    assert submit(queue, WORK_PORT, 42, callback) == S_OK
    assert calls == []                              # file manuelle : rien avant Dispatch
    assert dispatch(queue, WORK_PORT, 0)
    assert calls == [(42, False)]
    close(queue)


def test_async_run_completes_on_thread_pool_queue(runtime_dir):
    api = TaskQueueApi(runtime_dir)
    create = api.method(12, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
    run = api.method(6, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ASYNC_WORK)
    status = api.method(3, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ctypes.c_bool)
    close = api.method(17, None, ctypes.c_void_p)
    queue = ctypes.c_void_p()
    assert create(THREAD_POOL, THREAD_POOL, ctypes.byref(queue)) == S_OK
    block = AsyncBlock(queue=queue)
    work = ASYNC_WORK(lambda pointer: 0x1234)
    assert run(ctypes.byref(block), work) == S_OK
    assert status(ctypes.byref(block), True) == 0x1234   # attend la fin du travail
    close(queue)


def test_thread_time_sensitivity_is_per_thread(runtime_dir):
    api = TaskQueueApi(runtime_dir)
    set_sensitive = api.method(27, ctypes.c_uint32, ctypes.c_bool)
    is_sensitive = api.method(30, ctypes.c_bool)
    assert set_sensitive(True) == S_OK and is_sensitive()
    assert set_sensitive(False) == S_OK and not is_sensitive()
