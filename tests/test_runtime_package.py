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
