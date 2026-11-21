"""Fonctions qu'AnyXboxX substitue aux vraies DLL en exécution native.

Deux familles :
- le chargeur de modules (LoadLibrary, GetProcAddress, GetModuleHandle,
  GetModuleFileName) : le jeu chargé à la main doit se voir lui-même, et
  `xgameruntime.dll` doit être servi par AnyXboxX et non par Windows ;
- le runtime GDK (`xgameruntime.dll`) : identité Xbox Series X.
"""
import ctypes
from ctypes import c_uint32, c_void_p
import os

from . import win32

S_OK, E_NOTIMPL, E_NOINTERFACE = 0, 0x80004001, 0x80004002
XBOX_SERIES_X = 7
GAME_RUNTIME = "xgameruntime"
HRESULT4 = ctypes.WINFUNCTYPE(c_uint32, c_void_p, c_void_p, c_void_p, c_void_p)
VOID2 = ctypes.WINFUNCTYPE(None, c_void_p, c_void_p)
LOAD_W = ctypes.WINFUNCTYPE(c_void_p, c_void_p, c_void_p, c_uint32)
LOAD_W1 = ctypes.WINFUNCTYPE(c_void_p, c_void_p)
PROC = ctypes.WINFUNCTYPE(c_void_p, c_void_p, c_void_p)
HANDLE = ctypes.WINFUNCTYPE(c_void_p, c_void_p)
FILENAME = ctypes.WINFUNCTYPE(c_uint32, c_void_p, c_void_p, c_uint32)
LOADER_FUNCTIONS = frozenset({
    "LoadLibraryExW", "LoadLibraryW", "LoadLibraryExA", "LoadLibraryA", "GetProcAddress",
    "GetModuleHandleW", "GetModuleHandleA", "GetModuleFileNameW", "GetModuleFileNameA",
})


def _guid(pointer):
    if not pointer:
        return "{null}"
    import uuid

    return "{" + str(uuid.UUID(bytes_le=ctypes.string_at(pointer, 16))).upper() + "}"


def _is_runtime(name):
    return name.replace("/", "\\").rsplit("\\", 1)[-1].lower().startswith(GAME_RUNTIME)


class Shims:
    def __init__(self, image):
        self.image = image
        self.log = image.log
        self.trace = os.environ.get("ANYXBOXX_TRACE") == "1"
        self._runtime_tag = ctypes.create_string_buffer(16)   # adresse unique = « handle » du runtime
        self.runtime_handle = ctypes.addressof(self._runtime_tag)
        self._keep = []
        self.loader = {name: self._make(name) for name in LOADER_FUNCTIONS}
        self.runtime = self._runtime_functions()

    def _keepalive(self, callback):
        self._keep.append(callback)   # sans référence, ctypes libérerait le trampoline
        return win32.callback_address(callback)

    # --- Chargeur de modules ----------------------------------------------

    def _make(self, name):
        return self._keepalive(getattr(self, f"_{name}")())

    def _load(self, name, real):
        if self.trace:
            self.log(f"[trace] LoadLibrary {name}")
        if _is_runtime(name):
            self.log(f"[natif] {name} → runtime GDK d'AnyXboxX (Xbox Series X)")
            return self.runtime_handle
        return real()

    def _LoadLibraryExW(self):
        return LOAD_W(lambda p, f, flags: self._load(ctypes.wstring_at(p), lambda: win32.LoadLibraryExW(p, f, flags)))

    def _LoadLibraryW(self):
        return LOAD_W1(lambda p: self._load(ctypes.wstring_at(p), lambda: win32.LoadLibraryExW(p, None, 0)))

    def _LoadLibraryExA(self):
        return LOAD_W(lambda p, f, flags: self._load(ctypes.string_at(p).decode(errors="replace"),
                                                      lambda: win32.LoadLibraryExA(p, f, flags)))

    def _LoadLibraryA(self):
        return LOAD_W1(lambda p: self._load(ctypes.string_at(p).decode(errors="replace"),
                                            lambda: win32.LoadLibraryExA(p, None, 0)))

    def _GetProcAddress(self):
        def get_proc(module, name):
            name = name or 0
            label = f"#{name}" if name <= 0xFFFF else ctypes.string_at(name).decode(errors="replace")
            if self.trace:
                self.log(f"[trace] GetProcAddress {module or 0:#x} {label}")
            if module == self.runtime_handle:
                address = self.runtime_address(label)
                if not address:
                    win32.SetLastError(win32.ERROR_PROC_NOT_FOUND)
                return address
            return win32.GetProcAddress(module, name)
        return PROC(get_proc)

    def _module_handle(self, pointer, decode, real):
        if not pointer:
            return self.image.base
        return self.runtime_handle if _is_runtime(decode(pointer)) else real(pointer)

    def _GetModuleHandleW(self):
        return HANDLE(lambda p: self._module_handle(p, ctypes.wstring_at, win32.GetModuleHandleW))

    def _GetModuleHandleA(self):
        return HANDLE(lambda p: self._module_handle(
            p, lambda q: ctypes.string_at(q).decode(errors="replace"), win32.GetModuleHandleA))

    def _file_name(self, module, buffer, size, wide, real):
        if module and module != self.image.base:
            return real(module, buffer, size)
        if not buffer or size == 0:
            return 0
        path = str(self.image.path)[:size - 1]
        data = path.encode("utf-16-le") + b"\0\0" if wide else path.encode("mbcs", errors="replace") + b"\0"
        ctypes.memmove(buffer, data, len(data))
        return len(path)

    def _GetModuleFileNameW(self):
        return FILENAME(lambda m, b, s: self._file_name(m, b, s, True, win32.GetModuleFileNameW))

    def _GetModuleFileNameA(self):
        return FILENAME(lambda m, b, s: self._file_name(m, b, s, False, win32.GetModuleFileNameA))

    # --- Runtime GDK ---------------------------------------------------------

    def _runtime_functions(self):
        def ok(*_):
            return S_OK

        def query_api(provider, interface, out, _):
            if self.trace:
                self.log(f"[trace] QueryApiImpl {_guid(provider)} {_guid(interface)}")
            if out:
                win32.write_u64(out, 0)
            return E_NOINTERFACE

        def error_report(code, message):
            text = ctypes.string_at(message).decode(errors="replace") if message else ""
            self.log(f"[XErrorReport] {(code or 0) & 0xFFFF_FFFF:#x} {text}")

        functions = {
            "InitializeApiImpl": HRESULT4(ok), "InitializeApiImplEx": HRESULT4(ok),
            "InitializeApiImplEx2": HRESULT4(ok), "UninitializeApiImpl": HRESULT4(ok),
            "QueryApiImpl": HRESULT4(query_api), "XErrorReport": VOID2(error_report),
            "XGameRuntimeInitialize": HRESULT4(ok), "XGameRuntimeUninitialize": HRESULT4(ok),
            "XSystemGetDeviceType": HRESULT4(lambda *_: XBOX_SERIES_X),
        }
        return {name: self._keepalive(callback) for name, callback in functions.items()}

    def runtime_address(self, name):
        address = self.runtime.get(name)
        if address is None:
            self.log(f"[natif] xgameruntime!{name} non fourni par AnyXboxX")
        return address or 0


def _overwrite(pointer, data, capacity):
    if not pointer or len(data) > capacity:
        return False
    ctypes.memmove(pointer, data, len(data))
    return True


def adopt_command_line(exe_path):
    """Le processus prend la ligne de commande du jeu, comme sous Wine.

    GetCommandLineW/A renvoient des tampons propres au processus, que le CRT et
    toutes les DLL (même chargées par Windows, comme SDL3.dll) relisent. On les
    réécrit sur place : la ligne du jeu, `"chemin"`, est plus courte que celle de
    python qui le contient déjà. Renvoie False si un tampon est trop petit.
    """
    line = f'"{exe_path}"'
    wide, narrow = win32.GetCommandLineW(), win32.GetCommandLineA()
    wide_ok = _overwrite(wide, line.encode("utf-16-le") + b"\0\0",
                         2 * len(ctypes.wstring_at(wide)) + 2 if wide else 0)
    narrow_ok = _overwrite(narrow, line.encode("mbcs", errors="replace") + b"\0",
                           len(ctypes.string_at(narrow)) + 1 if narrow else 0)
    return wide_ok and narrow_ok
