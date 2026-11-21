"""Décodeur des encodages RDNA 2 (GPU de la Xbox Series X), d'après la documentation publique d'AMD."""
import struct

from emu import rdna2


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
