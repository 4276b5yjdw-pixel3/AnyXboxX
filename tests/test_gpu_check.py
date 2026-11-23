"""Banc GPU par carte (issue #70) : adaptateur choisi par son nom, --adaptateur et Run-GpuCheck.ps1."""
import os
import re
import subprocess

import pytest

from emu import rdna2_gpu

UNKNOWN = "aucune-carte-de-ce-nom-70"
MINIMAL_HLSL = "RWByteAddressBuffer memory : register(u0);\n[numthreads(1, 1, 1)] void main() { memory.Store(0, 1u); }\n"
gpu = pytest.mark.skipif(not rdna2_gpu.available(), reason="dxc ou anyxboxx_gpu_run.exe absent")


def describe(runtime_dir, value):
    """Sortie de `anyxboxx_gpu_run.exe --adaptateur` avec ANYXBOXX_GPU=value (None : variable absente)."""
    environment = {key: item for key, item in os.environ.items() if key != "ANYXBOXX_GPU"}
    if value is not None:
        environment["ANYXBOXX_GPU"] = value
    return subprocess.run([str(runtime_dir / "anyxboxx_gpu_run.exe"), "--adaptateur"], capture_output=True,
                          encoding="utf-8", errors="replace", env=environment, timeout=60)


@gpu
def test_a_name_that_matches_no_adapter_is_refused(runtime_dir, monkeypatch):
    monkeypatch.setenv("ANYXBOXX_GPU", UNKNOWN)
    with pytest.raises(RuntimeError, match=UNKNOWN):
        rdna2_gpu.run(MINIMAL_HLSL, bytes(16))


def test_adapter_flag_describes_warp(runtime_dir):
    result = describe(runtime_dir, "warp")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert re.fullmatch(r"adapter=Microsoft Basic Render Driver vendor=1414 device=[0-9a-f]{4}", lines[0])
    assert re.fullmatch(r"driver=(\d+\.\d+\.\d+\.\d+|inconnu)", lines[1])
    assert lines[2] == "backend=warp"
    assert re.fullmatch(r"native_lane_range=\d+-\d+", lines[3])
    assert re.fullmatch(r"raytracing_tier=(\d\.\d|aucun)", lines[4])


def test_part_of_a_name_in_any_case_picks_that_adapter(runtime_dir):
    default = describe(runtime_dir, None)
    assert default.returncode == 0, default.stderr
    if "backend=hardware" not in default.stdout:
        pytest.skip("pas d'adaptateur matériel par défaut (CI : rendu logiciel)")
    name = re.match(r"adapter=(.+) vendor=", default.stdout).group(1)
    chosen = describe(runtime_dir, name[len(name) // 3:].lower().strip())
    assert chosen.returncode == 0, chosen.stderr
    assert chosen.stdout.splitlines()[0] == default.stdout.splitlines()[0]
