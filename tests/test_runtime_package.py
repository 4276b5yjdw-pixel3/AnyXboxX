"""XPackage identity and installed-package queries, called through the runtime vtable."""
import ctypes

from test_runtime_cpp import GdkInterface, S_OK, anyxboxx_only

pytestmark = anyxboxx_only
PROVIDER = "AF406016-E850-4AA8-A88D-2F3DCB9DAC7E"
IID = "0B9D556E-AB70-43F4-BAA0-9999AC4CB040"
P = ctypes.c_void_p
E_INVALIDARG = 0x80070057
E_INSUFFICIENT_BUFFER = 0x8007007A


def test_package_identity_and_installed_state(runtime_dir, tmp_path, monkeypatch):
    name = "Synthetic.Package.?.For.Testing.Long"
    (tmp_path / "MicrosoftGame.config").write_text(f'<Game><Identity Name="{name}" /></Game>', encoding='utf-8')
    monkeypatch.setenv("ANYXBOXX_GAME_DIR", str(tmp_path))
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    identifier = api.method(3, ctypes.c_uint32, ctypes.c_size_t, P)
    buf = ctypes.create_string_buffer(33)
    assert identifier(32, buf) == E_INSUFFICIENT_BUFFER
    assert identifier(33, buf) == S_OK and buf.value == name.encode()[:32]
    assert api.method(4, ctypes.c_bool)() is True
    kind = ctypes.c_uint32(42)
    get_kind = api.method(41, ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32))
    assert get_kind(None, None) == E_INVALIDARG
    assert get_kind(None, ctypes.byref(kind)) == S_OK and kind.value == 0
    availability = ctypes.c_uint32(42)
    find = api.method(12, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, P, ctypes.POINTER(ctypes.c_uint32))
    assert find(None, 0, None, None) == E_INVALIDARG
    assert find(None, 0, None, ctypes.byref(availability)) == S_OK and availability.value == 0
    stats = (ctypes.c_uint64 * 4)()
    get_stats = api.method(30, ctypes.c_uint32, P)
    assert get_stats(None) == E_INVALIDARG
    assert get_stats(stats) == S_OK and list(stats) == [0, 2**64 - 1, 0, 0]


def test_package_identity_falls_back_when_missing(runtime_dir, tmp_path, monkeypatch):
    (tmp_path / "MicrosoftGame.config").write_text('<Game><Identity Name="unterminated', encoding='utf-8')
    monkeypatch.setenv("ANYXBOXX_GAME_DIR", str(tmp_path))
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    identifier = api.method(3, ctypes.c_uint32, ctypes.c_size_t, P)
    buf = ctypes.create_string_buffer(33)
    assert identifier(len(buf), buf) == S_OK and buf.value == b"AnyXboxX.Game"


class InstallationProgress(ctypes.Structure):
    _fields_ = [("total", ctypes.c_uint64), ("installed", ctypes.c_uint64),
                ("launch", ctypes.c_uint64), ("launchable", ctypes.c_bool), ("completed", ctypes.c_bool)]


def test_installed_package_monitor(runtime_dir):
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    create = api.method(5, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, P, ctypes.c_uint32, P,
                        ctypes.POINTER(P))
    assert create(None, 0, None, 0, None, None) == E_INVALIDARG
    monitor = P()
    assert create(None, 0, None, 0, None, ctypes.byref(monitor)) == S_OK and monitor.value
    try:
        progress = InstallationProgress()
        api.method(7, None, P, ctypes.POINTER(InstallationProgress))(monitor, ctypes.byref(progress))
        assert (progress.total, progress.installed, progress.launch, progress.launchable, progress.completed) == (
            1, 1, 1, True, True)
        assert api.method(8, ctypes.c_bool, P)(monitor) is False
    finally:
        api.method(6, None, P)(monitor)


def test_install_chunks_returns_completed_monitor(runtime_dir):
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    install = api.method(15, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, P, ctypes.c_uint32,
                         ctypes.c_bool, P, ctypes.POINTER(P))
    monitor = P()
    assert install(None, 0, None, 0, False, None, ctypes.byref(monitor)) == S_OK and monitor.value
    progress = InstallationProgress()
    api.method(7, None, P, ctypes.POINTER(InstallationProgress))(monitor, ctypes.byref(progress))
    assert progress.completed and progress.launchable
    api.method(6, None, P)(monitor)


def test_install_chunks_async_returns_monitor(runtime_dir):
    from test_runtime_cpp import AsyncBlock, TaskQueueApi, THREAD_POOL
    tasks = TaskQueueApi(runtime_dir)
    queue = P()
    assert tasks.method(12, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(P))(
        THREAD_POOL, THREAD_POOL, ctypes.byref(queue)) == S_OK
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    block = AsyncBlock(queue=queue)
    begin = api.method(16, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, P, ctypes.c_uint32,
                       ctypes.c_bool, ctypes.POINTER(AsyncBlock))
    try:
        assert begin(None, 0, None, 0, False, ctypes.byref(block)) == S_OK
        assert tasks.method(3, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ctypes.c_bool)(
            ctypes.byref(block), True) == S_OK
        monitor = P()
        assert api.method(17, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ctypes.POINTER(P))(
            ctypes.byref(block), ctypes.byref(monitor)) == S_OK and monitor.value
        progress = InstallationProgress()
        api.method(7, None, P, ctypes.POINTER(InstallationProgress))(monitor, ctypes.byref(progress))
        assert progress.completed
        api.method(6, None, P)(monitor)
    finally:
        tasks.method(17, None, P)(queue)


def test_package_mount_returns_game_directory(runtime_dir, tmp_path, monkeypatch):
    from test_runtime_cpp import AsyncBlock, TaskQueueApi, THREAD_POOL
    monkeypatch.setenv("ANYXBOXX_GAME_DIR", str(tmp_path))
    tasks = TaskQueueApi(runtime_dir)
    queue = P()
    assert tasks.method(12, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(P))(
        THREAD_POOL, THREAD_POOL, ctypes.byref(queue)) == S_OK
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    block = AsyncBlock(queue=queue)
    try:
        assert api.method(37, ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(AsyncBlock))(
            b"Test.Package", ctypes.byref(block)) == S_OK
        assert tasks.method(3, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ctypes.c_bool)(
            ctypes.byref(block), True) == S_OK
        mount = P()
        assert api.method(38, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ctypes.POINTER(P))(
            ctypes.byref(block), ctypes.byref(mount)) == S_OK and mount.value
        length = ctypes.c_size_t()
        assert api.method(24, ctypes.c_uint32, P, ctypes.POINTER(ctypes.c_size_t))(
            mount, ctypes.byref(length)) == S_OK
        buf = ctypes.create_string_buffer(length.value)
        path = api.method(25, ctypes.c_uint32, P, ctypes.c_size_t, P)
        assert path(mount, length.value - 1, buf) == E_INSUFFICIENT_BUFFER
        assert path(mount, length.value, buf) == S_OK and buf.value.decode("utf-8") == str(tmp_path)
        api.method(26, None, P)(mount)
    finally:
        tasks.method(17, None, P)(queue)


def test_package_mount_without_game_directory_fails(runtime_dir, monkeypatch):
    from test_runtime_cpp import AsyncBlock, TaskQueueApi, THREAD_POOL
    monkeypatch.delenv("ANYXBOXX_GAME_DIR", raising=False)
    tasks = TaskQueueApi(runtime_dir)
    queue = P()
    assert tasks.method(12, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(P))(
        THREAD_POOL, THREAD_POOL, ctypes.byref(queue)) == S_OK
    api = GdkInterface(runtime_dir, PROVIDER, IID)
    block = AsyncBlock(queue=queue)
    try:
        assert api.method(37, ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(AsyncBlock))(
            b"Test.Package", ctypes.byref(block)) == S_OK
        assert tasks.method(3, ctypes.c_uint32, ctypes.POINTER(AsyncBlock), ctypes.c_bool)(
            ctypes.byref(block), True) == 0x80070003
    finally:
        tasks.method(17, None, P)(queue)
