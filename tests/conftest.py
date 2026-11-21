import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "PrototypeScarlett"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

import pytest  # noqa: E402

RUNTIME_DIR = Path(os.environ.get("ANYXBOXX_RUNTIME")
                   or Path(__file__).resolve().parents[1] / "runtime" / "build" / "bin")
RUNTIME_DLLS = ("xgameruntime.dll", "xmem.dll", "d3d12_xs.dll")


def runtime_built():
    return all((RUNTIME_DIR / name).is_file() for name in RUNTIME_DLLS)


@pytest.fixture
def runtime_dir():
    """Dossier du runtime C++ ; absent : test ignoré, sauf en CI (ANYXBOXX_REQUIRE_RUNTIME=1)."""
    if not runtime_built():
        if os.environ.get("ANYXBOXX_REQUIRE_RUNTIME") == "1":
            pytest.fail(f"Runtime C++ absent de {RUNTIME_DIR} : compilez runtime/ avec CMake.")
        pytest.skip("runtime C++ non compilé (cmake -S runtime -B runtime/build)")
    return RUNTIME_DIR
