"""Traducteur RDNA 2 → SPIR-V de Leonida (third_party/leonida), appelé sur notre désassemblage."""
import pytest

from emu import rdna2_operands, rdna2_spirv
from emu.rdna2_hlsl_ops import Untranslatable
from test_rdna2_exec import program, vop1
from test_rdna2_graphics import PIXEL_SHADER, exp, vintrp

VERTEX_SHADER = program(vop1("v_cvt_f32_u32", 1, 256), vop1("v_mov_b32", 2, 0xF0), vop1("v_mov_b32", 3, 128),
                        vop1("v_mov_b32", 4, 0xF2), *exp(12, (1, 2, 3, 4), done=True), *exp(32, (2, 2, 3, 4)))
needs_tools = pytest.mark.skipif(rdna2_spirv.tools() is None, reason="spirv-as / spirv-val absents (SDK Vulkan)")


def test_vintrp_text_matches_llvm():
    assert rdna2_operands.text(bytes((0x00, 0x00, 0x04, 0xC8))) == "v_interp_p1_f32_e32 v1, v0, attr0.x"
    assert rdna2_operands.text(bytes((0x00, 0x00, 0x02, 0xC8))) == "v_interp_mov_f32_e32 v0, p10, attr0.x"
    assert rdna2_operands.text(bytes(vintrp("v_interp_p2_f32", 3, 1, 2, 3)[0].to_bytes(4, "little"))) == \
        "v_interp_p2_f32_e32 v3, v1, attr2.w"


def test_disassembly_is_the_llvm_listing_leonida_reads():
    listing = rdna2_spirv.disassembly(PIXEL_SHADER).splitlines()
    assert listing[0] == "\tv_interp_p1_f32_e32 v2, v0, attr0.x ; encoding: [0x00,0x00,0x08,0xc8]"
    assert listing[-1] == "\ts_endpgm ; encoding: [0x00,0x00,0x81,0xbf]"


@pytest.mark.parametrize("data, stage, entry, interface", [
    (PIXEL_SHADER, "ps", "OpEntryPoint Fragment", ("%out_mrt0", "%in_attr0")),
    (VERTEX_SHADER, "vs", "OpEntryPoint Vertex", ("%out_pos", "%out_param0", "%vertex_index")),
])
def test_leonida_translates_our_shaders(data, stage, entry, interface):
    asm = rdna2_spirv.translate(data, stage)
    line = next(text for text in asm.splitlines() if entry in text)
    assert all(name in line for name in interface)


def test_refusals_are_named():
    with pytest.raises(Untranslatable, match="pas de texte LLVM"):
        rdna2_spirv.disassembly(program(0x7E0A02F9, 0x00060606))         # SDWA : contrôle non décodé
    with pytest.raises(ValueError, match="étage inconnu"):
        rdna2_spirv.translate(PIXEL_SHADER, "hs")


@needs_tools
@pytest.mark.parametrize("data, stage", [(PIXEL_SHADER, "ps"), (VERTEX_SHADER, "vs")])
def test_spirv_is_valid(data, stage):
    assert rdna2_spirv.validate(rdna2_spirv.translate(data, stage))[:4] == b"\x03\x02\x23\x07"
