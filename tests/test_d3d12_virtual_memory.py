"""d3d12_xs.dll : D3D12ConfigureVirtualMemoryX, appelée par le titre avant la création du périphérique.

Sans cet export, le titre s'arrête sur « UNIMPLEMENTED d3d12_xs.dll!D3D12ConfigureVirtualMemoryX » (note de
premier démarrage, section 4, arrêt 1). Forme : une structure de 32 octets (quatre mots de 32 bits, puis deux
mots de 64 bits de sortie) ; un pointeur nul est refusé, un pointeur valide rend S_OK et remet les sorties à zéro,
comme TomBox.
"""
import ctypes
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="DLL Windows x64")

S_OK, E_INVALIDARG = 0, 0x8007_0057


class VirtualMemoryConfiguration(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_uint32), ("page_table_pages", ctypes.c_uint32),
                ("frame_buffer_preserve_bytes", ctypes.c_uint32), ("reserved", ctypes.c_uint32),
                ("output0", ctypes.c_uint64), ("output1", ctypes.c_uint64)]


@pytest.fixture
def d3d12_xs(runtime_dir):
    dll = ctypes.WinDLL(str(runtime_dir / "d3d12_xs.dll"))
    dll.D3D12ConfigureVirtualMemoryX.restype = ctypes.c_uint32
    dll.D3D12ConfigureVirtualMemoryX.argtypes = (ctypes.c_void_p,)
    return dll


def test_configure_virtual_memory_refuses_a_null_description(d3d12_xs):
    assert d3d12_xs.D3D12ConfigureVirtualMemoryX(None) == E_INVALIDARG


def test_configure_virtual_memory_accepts_a_description_and_clears_the_outputs(d3d12_xs):
    config = VirtualMemoryConfiguration(flags=1, page_table_pages=0x21, frame_buffer_preserve_bytes=0x30_0000,
                                        reserved=0, output0=9, output1=9)
    assert d3d12_xs.D3D12ConfigureVirtualMemoryX(ctypes.addressof(config)) == S_OK
    assert (config.output0, config.output1) == (0, 0)

