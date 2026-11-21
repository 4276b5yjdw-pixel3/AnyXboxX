"""anyxboxx.exe : le lanceur natif en C++, sans Python dans le processus du jeu."""
import os
import subprocess
import sys
from pathlib import Path

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


def test_package_without_its_executable_says_so(tmp_path, runtime_dir):
    (tmp_path / "MicrosoftGame.config").write_text(
        '<Game><ExecutableList><Executable Name="game_scarlett_master.exe" /></ExecutableList></Game>',
        encoding="utf-8")
    result = subprocess.run([str(runtime_dir / "anyxboxx.exe"), str(tmp_path)], capture_output=True, timeout=30)
    stderr = result.stderr.decode("utf-8", errors="replace") + result.stderr.decode("mbcs", errors="replace")
    assert result.returncode == 1 and "game_scarlett_master.exe" in stderr


TOMBOX_D3D12 = Path(__file__).resolve().parents[1] / "third_party" / "tombox" / "target" / "release" / "d3d12_xs.dll"


@pytest.mark.skipif(not TOMBOX_D3D12.is_file(), reason="d3d12_xs de TomBox non compilée (tools/build_tombox.py d3d12_xs)")
def test_tombox_d3d12_serves_console_device_creation(tmp_path, runtime_dir):
    exe = build_pe(tmp_path / "d3d.exe", lambda iat: Asm().mov_eax(7).ret().build(),
                   imports=[("d3d12_xs.dll", "D3D12XboxCreateDevice"), ("d3d12_xs.dll", "DXGIXPresentArray")], dll=False)
    assert launch(runtime_dir, exe).returncode == 1                  # absent de notre d3d12_xs
    environment = {**os.environ, "ANYXBOXX_D3D12_XS": str(TOMBOX_D3D12)}
    result = subprocess.run([str(runtime_dir / "anyxboxx.exe"), str(exe)], capture_output=True, text=True,
                            timeout=60, env=environment)
    assert result.returncode == 7, result.stderr


TOMBOX_DIR = TOMBOX_D3D12.parent


@pytest.mark.skipif(not (TOMBOX_DIR / "xg_xs.dll").is_file() or not (TOMBOX_DIR / "xmem.dll").is_file(),
                    reason="DLL de TomBox non compilées (tools/build_tombox.py xg_xs xmem)")
def test_tombox_dir_serves_missing_console_libraries(tmp_path, runtime_dir):
    def code(iat):
        return Asm().frame().mov_ecx(64).zero_rdx().call_iat(iat[("xmem.dll", "XMemAlloc")]).unframe().ret().build()

    imports = [("xmem.dll", "XMemAlloc"), ("xmem.dll", "XMemGetAllocationStatistics"),
               ("xg_xs.dll", "XGComputeTexture2DLayout")]
    exe = build_pe(tmp_path / "xg.exe", code, imports=imports, dll=False)
    assert launch(runtime_dir, exe).returncode == 1                  # xg_xs absent d'AnyXboxX
    environment = {**os.environ, "ANYXBOXX_TOMBOX_DIR": str(TOMBOX_DIR)}
    result = subprocess.run([str(runtime_dir / "anyxboxx.exe"), str(exe)], capture_output=True, text=True,
                            timeout=60, env=environment)
    pointer = result.returncode & 0xFFFF_FFFF                        # XMemAlloc de TomBox : alignement par défaut 16
    assert pointer not in (0, 1) and pointer % 16 == 0, result.stderr
