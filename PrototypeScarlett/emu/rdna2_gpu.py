"""Exécution sur le GPU du PC d'un programme RDNA 2 recompilé : HLSL → DXIL (dxc) → D3D12.

    hlsl = rdna2_hlsl.translate(programme, sgprs)
    mémoire_finale = rdna2_gpu.run(hlsl, mémoire_initiale)

dxc vient du SDK Windows (ou de ANYXBOXX_DXC) ; anyxboxx_gpu_run.exe est compilé avec le runtime
C++ (dossier ANYXBOXX_RUNTIME, sinon runtime/build/bin). Sans GPU, WARP est utilisé.
"""
import os
import subprocess
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
KITS = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "bin"
SHADER_MODEL = "cs_6_0"
TIMEOUT = 120


class GpuUnavailable(RuntimeError):
    """dxc ou le lanceur GPU est introuvable."""


def find_dxc():
    configured = os.environ.get("ANYXBOXX_DXC")
    if configured:
        return Path(configured) if Path(configured).is_file() else None
    found = sorted(KITS.glob("10.*/x64/dxc.exe"), reverse=True)
    return found[0] if found else None


def find_runner():
    folder = Path(os.environ.get("ANYXBOXX_RUNTIME") or REPOSITORY / "runtime" / "build" / "bin")
    runner = folder / "anyxboxx_gpu_run.exe"
    return runner if runner.is_file() else None


def available():
    return find_dxc() is not None and find_runner() is not None


def compile_hlsl(hlsl, folder):
    dxc = find_dxc()
    if dxc is None:
        raise GpuUnavailable("dxc introuvable : installez le SDK Windows ou définissez ANYXBOXX_DXC")
    source, output = Path(folder) / "shader.hlsl", Path(folder) / "shader.dxil"
    source.write_text(hlsl, encoding="utf-8")
    result = subprocess.run([str(dxc), "-nologo", "-T", SHADER_MODEL, "-E", "main", "-Fo", str(output), str(source)],
                            capture_output=True, text=True, timeout=TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"dxc a refusé le HLSL généré :\n{result.stderr}")
    return output


def run(hlsl, memory, groups=1):
    """Compile `hlsl`, l'exécute avec `memory` (bytes) en u0 et renvoie la mémoire finale."""
    runner = find_runner()
    if runner is None:
        raise GpuUnavailable("anyxboxx_gpu_run.exe introuvable : compilez runtime/ avec CMake")
    with tempfile.TemporaryDirectory(prefix="anyxboxx-gpu-") as folder:
        shader = compile_hlsl(hlsl, folder)
        image = Path(folder) / "memory.bin"
        image.write_bytes(memory)
        result = subprocess.run([str(runner), str(shader), str(image), str(groups)],
                                capture_output=True, text=True, timeout=TIMEOUT)
        if result.returncode != 0:
            raise RuntimeError(f"exécution GPU impossible :\n{result.stderr}")
        return image.read_bytes()
