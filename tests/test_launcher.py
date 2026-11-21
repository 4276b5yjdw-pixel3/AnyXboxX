"""anyxboxx.exe : le lanceur natif en C++, sans Python dans le processus du jeu."""
import subprocess
import sys

import pytest

from pe_builder import Asm, build_pe
from test_native_tls import CALLBACKS, DIRECTORY, INDEX, TEMPLATE, VALUE, tls_reader

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="exécution native sous Windows")


def launch(runtime_dir, target):
    return subprocess.run([str(runtime_dir / "anyxboxx.exe"), str(target)], capture_output=True, text=True,
                          timeout=30)


def test_entry_point_result_is_the_exit_code(tmp_path, runtime_dir):
    exe = build_pe(tmp_path / "answer.exe", lambda iat: Asm().mov_eax(42).ret().build(), dll=False)
    assert launch(runtime_dir, exe).returncode == 42


def test_console_memory_import_is_served_by_the_runtime(tmp_path, runtime_dir):
    def code(iat):
        return Asm().frame().mov_ecx(64).zero_rdx().call_iat(iat[("xmem.dll", "XMemAlloc")]).unframe().ret().build()

    exe = build_pe(tmp_path / "mem.exe", code, imports=[("xmem.dll", "XMemAlloc")], dll=False)
    pointer = launch(runtime_dir, exe).returncode & 0xFFFF_FFFF
    assert pointer != 0 and pointer % 64 == 0


def test_thread_local_works_without_python(tmp_path, runtime_dir):
    pointers = {DIRECTORY: TEMPLATE, DIRECTORY + 8: TEMPLATE + 4, DIRECTORY + 16: INDEX, DIRECTORY + 24: CALLBACKS}
    exe = build_pe(tmp_path / "tls.exe", lambda iat: tls_reader(), dll=False, pointers=pointers, tls=DIRECTORY)
    assert launch(runtime_dir, exe).returncode & 0xFFFF_FFFF == VALUE


def test_package_folder_launches_its_declared_executable(tmp_path, runtime_dir):
    build_pe(tmp_path / "game.exe", lambda iat: Asm().mov_eax(7).ret().build(), dll=False)
    (tmp_path / "MicrosoftGame.config").write_text(
        '<Game><ExecutableList><Executable Name="game.exe" TargetDeviceFamily="Scarlett" /></ExecutableList></Game>',
        encoding="utf-8")
    assert launch(runtime_dir, tmp_path).returncode == 7


def test_missing_imports_are_named(tmp_path, runtime_dir):
    exe = build_pe(tmp_path / "todo.exe", lambda iat: Asm().mov_eax(1).ret().build(),
                   imports=[("d3d12_xs.dll", "D3D12XboxCreateDevice")], dll=False)
    result = launch(runtime_dir, exe)
    assert result.returncode == 1 and "d3d12_xs.dll!D3D12XboxCreateDevice" in result.stderr
