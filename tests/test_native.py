"""Exécution native façon Wine : le code tourne sur le vrai processeur.

Les PE de test sont fabriqués par pe_builder : leur contenu est connu octet par octet.
"""
import os
import sys

import pytest

from pe_builder import Asm, build_pe

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="exécution native sous Windows")

E_NOINTERFACE = 0x80004002
WIDE_XGR = 0x200     # L"xgameruntime.dll"
NAME_QUERY = 0x240   # "QueryApiImpl"


def run(path):
    from emu.native import NativeImage

    image = NativeImage(path)
    try:
        return image.call_entry() & 0xFFFF_FFFF, image.base
    finally:
        image.close()


def test_entry_point_runs_on_real_cpu(tmp_path):
    exe = build_pe(tmp_path / "answer.exe", lambda iat: Asm().mov_eax(42).ret().build(), dll=False)
    assert run(exe)[0] == 42


def test_import_is_bound_to_real_windows_function(tmp_path):
    def code(iat):
        return Asm().frame().call_iat(iat[("kernel32.dll", "GetCurrentProcessId")]).unframe().ret().build()

    exe = build_pe(tmp_path / "pid.exe", code, imports=[("kernel32.dll", "GetCurrentProcessId")], dll=False)
    assert run(exe)[0] == os.getpid()


def test_module_handle_of_game_is_its_own_base(tmp_path):
    def code(iat):
        return (Asm().frame().zero_rcx()
                .call_iat(iat[("kernel32.dll", "GetModuleHandleW")]).unframe().ret().build())

    exe = build_pe(tmp_path / "self.exe", code, imports=[("kernel32.dll", "GetModuleHandleW")], dll=False)
    code_value, base = run(exe)
    assert code_value == base & 0xFFFF_FFFF


def test_xgameruntime_is_served_by_anyxboxx(tmp_path):
    """LoadLibraryExW("xgameruntime.dll") puis GetProcAddress("QueryApiImpl") puis appel."""
    def code(iat):
        asm = (Asm().frame()
               .lea_rcx(WIDE_XGR).zero_rdx().zero_r8()
               .call_iat(iat[("kernel32.dll", "LoadLibraryExW")])
               .mov_rcx_rax().lea_rdx(NAME_QUERY)
               .call_iat(iat[("kernel32.dll", "GetProcAddress")])
               .zero_rcx().zero_rdx().zero_r8().call_rax()
               .unframe().ret())
        asm.at(WIDE_XGR).raw("xgameruntime.dll".encode("utf-16-le") + b"\0\0")
        asm.at(NAME_QUERY).raw(b"QueryApiImpl\0")
        return asm.build()

    imports = [("kernel32.dll", "LoadLibraryExW"), ("kernel32.dll", "GetProcAddress")]
    exe = build_pe(tmp_path / "gdk.exe", code, imports=imports, dll=False)
    assert run(exe)[0] == E_NOINTERFACE


def test_relocated_when_preferred_base_is_taken(tmp_path):
    from emu.native import NativeImage

    first = build_pe(tmp_path / "a.exe", lambda iat: Asm().mov_eax(1).ret().build(), dll=False)
    second = build_pe(tmp_path / "b.exe", lambda iat: Asm().mov_eax(2).ret().at(0x80).build(),
                      dll=False, pointers={0x80: 0})
    a = NativeImage(first)
    try:
        b = NativeImage(second)
        try:
            assert b.base != a.base and b.call_entry() == 2
        finally:
            b.close()
    finally:
        a.close()
