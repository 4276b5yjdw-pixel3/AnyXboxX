"""Décodeur des encodages RDNA 2 (GPU de la Xbox Series X), d'après la documentation publique d'AMD."""
import struct

from emu import rdna2, rdna2_operands


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
