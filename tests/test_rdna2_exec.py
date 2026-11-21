"""Interpréteur de référence RDNA 2 (wave32) : vrais petits programmes GPU exécutés ligne par ligne."""
import struct

import pytest

from emu import rdna2_exec
from emu.rdna2_exec_ops import BRANCHES, SCALAR, VECTOR, VECTOR_COMPARE, bits_float
from emu.rdna2_ops import MNEMONICS

OPCODES = {(family, name): opcode for (family, opcode), name in MNEMONICS.items()}
V = 256                         # v0 en opérande source 9 bits
VCC_LO, EXEC_LO, LITERAL = 106, 126, 255
ONE, TWO = 242, 244             # constantes flottantes en ligne 1.0 et 2.0


def const(n):
    return 128 + n              # constante entière en ligne 0..64


def sop2(name, sdst, ssrc0, ssrc1):
    return 0b10 << 30 | OPCODES["SOP2", name] << 23 | sdst << 16 | ssrc1 << 8 | ssrc0


def sop1(name, sdst, ssrc0):
    return 0x17D << 23 | sdst << 16 | OPCODES["SOP1", name] << 8 | ssrc0


def sopc(name, ssrc0, ssrc1):
    return 0x17E << 23 | OPCODES["SOPC", name] << 16 | ssrc1 << 8 | ssrc0


def sopp(name, simm16=0):
    return 0x17F << 23 | OPCODES["SOPP", name] << 16 | simm16 & 0xFFFF


def vop1(name, vdst, src0):
    return 0x3F << 25 | vdst << 17 | OPCODES["VOP1", name] << 9 | src0


def vop2(name, vdst, src0, vsrc1):
    return OPCODES["VOP2", name] << 25 | vdst << 17 | vsrc1 << 9 | src0


def vopc(name, src0, vsrc1):
    return 0x3E << 25 | OPCODES["VOPC", name] << 17 | vsrc1 << 9 | src0


def program(*words):
    """Programme terminé par s_endpgm."""
    return struct.pack(f"<{len(words) + 1}I", *words, sopp("s_endpgm"))


def test_vector_math_runs_on_every_lane():
    wave = rdna2_exec.run(program(
        vop1("v_cvt_f32_u32", 1, V + 0),        # v1 = float(numéro de ligne)
        vop2("v_mul_f32", 1, TWO, 1),           # v1 = 2.0 * v1
        vop2("v_add_f32", 1, ONE, 1)))          # v1 = 1.0 + v1
    assert [bits_float(x) for x in wave.v[1]] == [2.0 * lane + 1 for lane in range(32)]


def test_scalar_loop_with_branch():
    # s0 = 0 ; s1 = 5 ; faire { s0 += s1 ; s1 -= 1 } tant que s1 != 0  →  s0 = 15
    wave = rdna2_exec.run(program(
        sop1("s_mov_b32", 0, const(0)),
        sop1("s_mov_b32", 1, const(5)),
        sop2("s_add_u32", 0, 0, 1),             # pc 8 : début de la boucle
        sop2("s_sub_u32", 1, 1, const(1)),
        sopc("s_cmp_lg_u32", 1, const(0)),
        sopp("s_cbranch_scc1", -4)))            # pc 20 : retour à 8 = 20 + 4 - 4 × 4
    assert wave.s[0] == 15 and wave.s[1] == 0


def test_divergent_lanes_follow_exec():
    wave = rdna2_exec.run(program(
        vopc("v_cmp_gt_u32", const(16), 0),         # vcc = lignes où 16 > v0 (numéro de ligne)
        sop1("s_and_saveexec_b32", 2, VCC_LO),      # s2 = exec ; exec &= vcc
        vop1("v_mov_b32", 1, ONE),                  # seules les lignes 0 à 15 écrivent
        sop1("s_mov_b32", EXEC_LO, 2)))             # exec restauré
    assert wave.v[1] == [0x3F80_0000] * 16 + [0] * 16
    assert wave.exec == 0xFFFF_FFFF and wave.s[2] == 0xFFFF_FFFF and wave.vcc == 0xFFFF


def test_literal_and_fused_multiply_add():
    pi = 0x4049_0FDB
    data = struct.pack("<4I", vop1("v_mov_b32", 3, LITERAL), pi, vop2("v_fmac_f32", 3, TWO, 3),
                       sopp("s_endpgm"))
    wave = rdna2_exec.run(data)                  # v3 = 2.0 × v3 + v3 = 3π
    assert bits_float(wave.v[3][7]) == pytest.approx(3 * 3.14159265, rel=1e-6)


def test_untranslated_instruction_is_named():
    data = struct.pack("<3I", 0xD800_0000, 0, sopp("s_endpgm"))     # instruction LDS (famille DS)
    with pytest.raises(rdna2_exec.Untranslated, match="instruction non traduite : ds_"):
        rdna2_exec.run(data)


def test_semantics_only_name_real_rdna2_instructions():
    known = set(MNEMONICS.values())
    named = set(SCALAR) | set(VECTOR) | set(VECTOR_COMPARE) | set(BRANCHES)
    assert sorted(named - known) == []
    done, total = rdna2_exec.coverage()
    assert 150 <= done < total
