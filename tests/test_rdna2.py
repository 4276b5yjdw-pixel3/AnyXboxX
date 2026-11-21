"""Décodeur des encodages RDNA 2 (GPU de la Xbox Series X), d'après la documentation publique d'AMD."""
import struct

import pytest

from emu import rdna2, rdna2_operands, rdna2_swizzle


def words(*values):
    return struct.pack(f"<{len(values)}I", *values)


def test_scalar_encodings_are_recognised():
    assert rdna2.classify(words(0xBF810000)) == ("SOPP", 1, 1)       # s_endpgm
    assert rdna2.classify(words(0xBF800000)) == ("SOPP", 0, 1)       # s_nop 0
    assert rdna2.classify(words(0xBE800301)) == ("SOP1", 3, 1)       # s_mov_b32 s0, s1


def test_literal_constant_adds_a_dword():
    assert rdna2.classify(words(0xBE8003FF, 0x12345678)) == ("SOP1", 3, 2)   # s_mov_b32 s0, 0x12345678


def test_vector_encodings_are_recognised():
    assert rdna2.classify(words(0x7E000301)) == ("VOP1", 1, 1)       # v_mov_b32 v0, v1
    assert rdna2.classify(words(0x06000101)) == ("VOP2", 3, 1)       # v_add_f32 v0, v1, v0
    assert rdna2.classify(words(0xD5030000, 0x00000000))[0::2] == ("VOP3", 2)


def test_memory_encodings_are_64_bits():
    assert rdna2.classify(words(0xF4000000, 0))[0::2] == ("SMEM", 2)
    assert rdna2.classify(words(0xD8000000, 0))[0::2] == ("DS", 2)
    assert rdna2.classify(words(0xE0000000, 0))[0::2] == ("MUBUF", 2)
    assert rdna2.classify(words(0xF8000000, 0))[0::2] == ("EXP", 2)


def test_program_is_split_and_counted():
    program = words(0x7E000301, 0xBE8003FF, 0x12345678, 0xF4000000, 0, 0xBF810000)
    instructions = rdna2.decode(program)
    assert [i.family for i in instructions] == ["VOP1", "SOP1", "SMEM", "SOPP"]
    assert [i.offset for i in instructions] == [0, 4, 12, 20]
    assert rdna2.histogram(instructions) == {"SMEM": 1, "SOP1": 1, "SOPP": 1, "VOP1": 1}


def test_unknown_or_truncated_words_are_reported():
    instructions = rdna2.decode(words(0xF4000000))                   # SMEM coupée à 32 bits
    assert instructions[-1].family == "tronquée"


def llvm(*hex_bytes):
    """Octets d'une ligne « encoding: [...] » des tests publics de LLVM (gfx10/gfx1030)."""
    return bytes(hex_bytes)


def test_sdwa_and_dpp_add_a_control_dword():
    assert rdna2.classify(llvm(0xF9, 0x02, 0x0A, 0x7E, 0x01, 0x06, 0x06, 0x00)) == ("VOP1", 1, 2)  # v_mov_b32_sdwa
    assert rdna2.classify(words(0x060A04FA, 0x000000E4))[0::2] == ("VOP2", 2)                       # v_add_f32_dpp


def test_vop2_inline_literal_opcodes_follow_gfx10_numbering():
    fmamk = llvm(0x01, 0x07, 0x0A, 0x58, 0x41, 0x31, 0x21, 0x11)       # v_fmamk_f32 v5, v1, 0x11213141, v3
    assert rdna2.classify(fmamk) == ("VOP2", 0x2C, 2)
    assert rdna2.classify(llvm(0x01, 0x05, 0x0A, 0x30)) == ("VOP2", 0x18, 1)   # v_ashrrev_i32 : pas de littéral


def test_opm_bit_extends_mimg_and_mubuf_opcodes():
    msaa = llvm(0x3B, 0x01, 0x00, 0xF0, 0xCC, 0x0E, 0x0A, 0x00, 0x0B, 0x0E, 0x13, 0x00)   # image_msaa_load (NSA)
    assert rdna2.classify(msaa) == ("MIMG", 0x80, 3)
    d16 = llvm(0x00, 0x00, 0x00, 0xE2, 0x00, 0x01, 0x01, 0x01)          # buffer_load_format_d16_x
    assert rdna2.classify(d16) == ("MUBUF", 0x80, 2)


def test_mnemonics_come_from_the_rdna2_table():
    assert rdna2.mnemonic("SOPP", 1) == "s_endpgm"
    assert rdna2.mnemonic("SOP1", 3) == "s_mov_b32"
    assert rdna2.mnemonic("MIMG", 0x80) == "image_msaa_load"
    assert rdna2.mnemonic("MUBUF", 0x80) == "buffer_load_format_d16_x"
    assert rdna2.mnemonic("VOP3", 0x140) == "v_fma_legacy_f32"         # nom RDNA 2, pas v_mad_legacy_f32
    assert rdna2.mnemonic("VOP3", 0x103) == "v_add_f32"                # VOP2 vu en VOP3
    assert rdna2.mnemonic("GLOBAL", 0x0C) == "global_load_dword"       # même opcode, segment différent
    assert rdna2.mnemonic("FLAT", 0x0C) == "flat_load_dword"
    assert rdna2.mnemonic("inconnue", 0) is None


def test_listing_names_each_instruction():
    program = words(0x7E000301, 0xBE8003FF, 0x12345678, 0xBF810000, 0xFFFFFFFF)
    lines = rdna2.listing(program)
    assert [line[36:] for line in lines] == ["v_mov_b32 v0, v1", "s_mov_b32 s0, 0x12345678", "s_endpgm",
                                             "inconnue_op_0x0"]
    assert lines[1].split()[1:3] == ["BE8003FF", "12345678"]


def test_operands_follow_llvm_syntax():
    text = rdna2_operands.text
    assert text(words(0xBE800301)) == "s_mov_b32 s0, s1"
    assert text(words(0xBE8004FF, 0x12345678)) == "s_mov_b64 s[0:1], 0x12345678"
    assert text(llvm(0x01, 0x02, 0x7F, 0x80)) == "s_add_u32 exec_hi, s1, s2"
    assert text(llvm(0xC1, 0x02, 0x00, 0x80)) == "s_add_u32 s0, -1, s2"            # constante entière en ligne
    assert text(llvm(0xF0, 0x02, 0x0A, 0x7E)) == "v_mov_b32 v5, 0.5"               # constante flottante en ligne
    assert text(llvm(0x01, 0x05, 0x0A, 0x30)) == "v_ashrrev_i32 v5, v1, v2"
    assert text(llvm(0x01, 0x07, 0x0A, 0x58, 0x41, 0x31, 0x21, 0x11)) == "v_fmamk_f32 v5, v1, 0x11213141, v3"
    assert text(words(0x7C040501)) == "v_cmp_eq_f32 vcc_lo, v1, v2"            # VOPC, vcc implicite


@pytest.mark.parametrize("encoding, expected", [                 # encodages des tests MC de LLVM (gfx10)
    ((0x41, 0x01, 0x00, 0xF4, 0x45, 0x23, 0x01, 0x00), "s_load_dword s5, s[2:3], s0 offset:0x12345"),
    ((0x01, 0x05, 0x08, 0xF4, 0x00, 0x00, 0x00, 0xFA), "s_load_dwordx4 s[20:23], s[2:3], 0x0"),
    ((0x35, 0x05, 0x10, 0xF4, 0x00, 0x00, 0x00, 0x00), "s_load_dwordx16 s[20:35], vcc, s0"),
    ((0x44, 0x40, 0x61, 0xF4, 0x34, 0x12, 0x00, 0xFA), "s_buffer_store_dword s1, s[8:11], 0x1234 glc dlc"),
    ((0x41, 0x41, 0x10, 0xF6, 0x00, 0x00, 0x00, 0xCA), "s_atomic_smin s5, s[2:3], s101 dlc"),
    ((0xC2, 0x01, 0x98, 0xF4, 0x64, 0x00, 0x00, 0xFA), "s_atc_probe 7, s[4:5], 0x64"),
    ((0x00, 0x19, 0x90, 0xF4, 0x00, 0x00, 0x00, 0x00), "s_memtime s[100:101]"),
    ((0x00, 0x00, 0x80, 0xF4, 0x00, 0x00, 0x00, 0x00), "s_dcache_inv"),
])
def test_smem_operands_follow_llvm_syntax(encoding, expected):
    assert rdna2_operands.text(bytes(encoding)) == expected


def test_smem_offset_is_signed_21_bits():
    word = 0xF4000141 | (0x7D << 57) | (0x1FFFFF << 32)              # s_load_dword, offset -1, soffset null
    assert rdna2_operands.text(word.to_bytes(8, "little")) == "s_load_dword s5, s[2:3], -0x1"


@pytest.mark.parametrize("encoding, expected", [                 # encodages des tests MC de LLVM (gfx10)
    ((0xFF, 0xFF, 0x82, 0xD9, 0x01, 0x02, 0x00, 0x05), "ds_add_rtn_u64 v[5:6], v1, v[2:3] offset:65535 gds"),
    ((0x7F, 0xFF, 0x38, 0xD9, 0x01, 0xFE, 0x03, 0x00), "ds_write2_b64 v1, v[254:255], v[3:4] offset0:127 offset1:255"),
    ((0xFF, 0xFF, 0xD8, 0xD8, 0x01, 0x00, 0x00, 0xFF), "ds_read_b32 v255, v1 offset:65535"),
    ((0x00, 0x00, 0x34, 0xD8, 0x00, 0x01, 0x00, 0x00), "ds_write_b32 v0, v1"),
    ((0x04, 0x00, 0xD4, 0xD8, 0x01, 0x00, 0x00, 0x05), 'ds_swizzle_b32 v5, v1 offset:swizzle(BITMASK_PERM,"00p00")'),
    ((0xFF, 0xFF, 0xD6, 0xD8, 0x01, 0x00, 0x00, 0x05), "ds_swizzle_b32 v5, v1 offset:swizzle(FFT,31) gds"),
    ((0x00, 0x00, 0x72, 0xD8, 0x00, 0x00, 0x00, 0x00), "ds_gws_sema_p gds"),
    ((0x00, 0x00, 0x50, 0xD8, 0x00, 0x00, 0x00, 0x00), "ds_nop"),
])
def test_ds_operands_follow_llvm_syntax(encoding, expected):
    assert rdna2_operands.text(bytes(encoding)) == expected


@pytest.mark.parametrize("offset, expected", [                   # AMDGPUInstPrinter::printSwizzle de LLVM
    (0x0000, ""),
    (0x80E4, "swizzle(QUAD_PERM,0,1,2,3)"),
    (0x041F, "swizzle(SWAP,1)"),
    (0x0C1F, "swizzle(REVERSE,4)"),
    (0x005C, "swizzle(BROADCAST,4,2)"),
    (0x0004, 'swizzle(BITMASK_PERM,"00p00")'),
    (0xC4A0, "swizzle(ROTATE,1,5)"),
    (0xFFFF, "swizzle(FFT,31)"),
    (0x8100, "33024"),                                           # ni quad_perm ni bitmask : décimal
])
def test_swizzle_offsets(offset, expected):
    assert rdna2_swizzle.text(offset) == expected


def exp_bytes(target, enable=0xF, sources=(0, 0, 0, 0), compr=False, done=False, vm=False):
    word = enable | target << 4 | compr << 10 | done << 11 | vm << 12 | 0x3E << 26
    word |= sum(register << (32 + 8 * index) for index, register in enumerate(sources))
    return word.to_bytes(8, "little")


@pytest.mark.parametrize("encoding, expected", [                 # encodages des tests MC de LLVM (gfx10)
    ((0x0F, 0x08, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00), "exp mrt0, v0, v0, v0, v0 done"),
    ((0x8F, 0x04, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00), "exp mrtz, v0, v0, v0, v0 compr"),
    ((0x9F, 0x10, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00), "exp null, v0, v0, v0, v0 vm"),
    ((0xCF, 0x00, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00), "exp pos0, v0, v0, v0, v0"),
    ((0x4F, 0x01, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00), "exp prim, v0, v0, v0, v0"),
    ((0x0F, 0x02, 0x00, 0xF8, 0x00, 0x00, 0x00, 0x00), "exp param0, v0, v0, v0, v0"),
])
def test_exp_follows_llvm_syntax(encoding, expected):
    assert rdna2_operands.text(bytes(encoding)) == expected


def test_exp_sources_targets_and_flags():                       # AMDGPUInstPrinter::printExpSrcN/printExpTgt
    text = rdna2_operands.text
    assert text(exp_bytes(3, 0b0101, (1, 2, 3, 4))) == "exp mrt3, v1, off, v3, off"
    assert text(exp_bytes(16, 0b0011, (5, 6, 7, 8), compr=True, done=True, vm=True)) == \
        "exp pos4, v5, v5, off, off done compr vm"                # compr : src0, src0, src1, src1
    assert text(exp_bytes(63, 0b1100, (5, 6, 7, 8), compr=True)) == "exp param31, off, off, v6, v6 compr"
    assert text(exp_bytes(21)) == "exp invalid_target_21, v0, v0, v0, v0"   # dual_src_blend : gfx11+


def test_symbolic_immediates():
    assert rdna2_operands.waitcnt(0x1234) == "vmcnt(4) expcnt(3) lgkmcnt(18)"
    assert rdna2_operands.waitcnt(0x0000) == "vmcnt(0) expcnt(0) lgkmcnt(0)"
    assert rdna2_operands.hwreg(0x1234) == "hwreg(52, 8, 3)"
    assert rdna2_operands.hwreg(0xF81D) == "hwreg(HW_REG_SHADER_CYCLES)"
    assert rdna2_operands.immediate(64, "auto") == "64" and rdna2_operands.immediate(65, "auto") == "0x41"


def test_implicit_vcc_and_scalar_destination():
    text = rdna2_operands.text
    assert text(llvm(0x01, 0x05, 0x0A, 0x02)) == "v_cndmask_b32 v5, v1, v2, vcc_lo"    # vcc implicite (wave32)
    assert text(llvm(0x01, 0x05, 0x0A, 0x7E)) == "v_readfirstlane_b32 s5, v1"          # sdst dans le champ vdst
