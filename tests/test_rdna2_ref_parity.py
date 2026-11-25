"""Parité de l'interpréteur de référence Rust (crates/anyxboxx-rdna2-ref) avec emu/rdna2_exec.py.

Les mêmes programmes passent par les deux interpréteurs ; l'état final (pc, scc, registres
scalaires et vectoriels, nombre d'instructions exécutées) doit être identique, ligne par ligne.
Les programmes aléatoires (graine fixe) couvrent les familles scalaires SOP1, SOP2, SOPC, SOPK et
SOPP, en wave32 comme en wave64. Une différence est un bug de l'un des deux interpréteurs.

Le binaire est `target/release/anyxboxx-rdna2-ref(.exe)` (ou `target/debug`) ; absent, le test est
sauté, sauf en CI (ANYXBOXX_REQUIRE_RUNTIME=1).
"""
import os
import random
import re
import struct
import subprocess
from pathlib import Path

import pytest

from emu import rdna2_exec
from emu.rdna2_exec import VOP2_CARRY, Wave
from emu.rdna2_exec_cmp64 import COMPARE64
from emu.rdna2_exec_dot import OPERATIONS as DOT_OPERATIONS
from emu.rdna2_exec_memory import PAGE
from emu.rdna2_exec_movrel import SCALAR as MOVREL_SCALAR, VECTOR as MOVREL_VECTOR
from emu.rdna2_exec_wide import OPERATIONS as WIDE_OPERATIONS
from emu.rdna2_exec_vop3 import VECTOR3
from emu.rdna2_exec_ops import BRANCHES, NO_OPERATION, SCALAR, VECTOR, VECTOR_COMPARE, VECTOR_NO_OPERATION
from emu.rdna2_ops import MNEMONICS

REPO = Path(__file__).resolve().parents[1]
GENERATED = REPO / "crates" / "anyxboxx-rdna2-ref" / "src" / "mnemonics.rs"
OPCODES = {(family, name): opcode for (family, opcode), name in MNEMONICS.items()}
SCALAR_FAMILIES = ("SOP1", "SOP2", "SOPC", "SOPK", "SOPP")
# Opérandes sources que l'interpréteur sait lire : SGPR, constantes, flottants en ligne, littéral.
OPERANDS = [*range(0, 128), *range(128, 209), *range(240, 249), 255]
LITERAL = 255
SEED = 0x5CA1AB1E
PROGRAMS = 300


def binary():
    for profile in ("release", "debug"):
        for name in ("anyxboxx-rdna2-ref.exe", "anyxboxx-rdna2-ref"):
            path = REPO / "target" / profile / name
            if path.is_file():
                return path
    override = os.environ.get("ANYXBOXX_RDNA2_REF")
    if override and Path(override).is_file():
        return Path(override)
    if os.environ.get("ANYXBOXX_REQUIRE_RUNTIME") == "1":
        pytest.fail("anyxboxx-rdna2-ref absent : cargo build -p anyxboxx-rdna2-ref")
    pytest.skip("anyxboxx-rdna2-ref not built (cargo build -p anyxboxx-rdna2-ref)")


def sop2(name, sdst, ssrc0, ssrc1):
    return 0b10 << 30 | OPCODES["SOP2", name] << 23 | sdst << 16 | ssrc1 << 8 | ssrc0


def sop1(name, sdst, ssrc0):
    return 0x17D << 23 | sdst << 16 | OPCODES["SOP1", name] << 8 | ssrc0


def sopc(name, ssrc0, ssrc1):
    return 0x17E << 23 | OPCODES["SOPC", name] << 16 | ssrc1 << 8 | ssrc0


def sopk(name, sdst, simm16):
    return 0b1011 << 28 | OPCODES["SOPK", name] << 23 | sdst << 16 | simm16 & 0xFFFF


def sopp(name, simm16=0):
    return 0x17F << 23 | OPCODES["SOPP", name] << 16 | simm16 & 0xFFFF


def program(*words):
    """Programme terminé par s_endpgm, sous forme de mots (ce qu'attend le binaire Rust)."""
    return [*words, sopp("s_endpgm")]


def render(wave):
    """L'état d'un Wave, au format de la sortie de anyxboxx-rdna2-ref."""
    lines = [f"steps {wave.steps}", f"pc {wave.pc}", f"scc {int(wave.scc)}"]
    lines += [f"s {index} {value:08X}" for index, value in enumerate(wave.s) if value]
    for index, lanes in enumerate(wave.v[:256]):
        if any(lanes):
            lines.append(f"v {index} " + " ".join(f"{value:08X}" for value in lanes))
    for page, data in sorted(wave.memory.pages.items()):
        words = struct.unpack("<1024I", bytes(data))
        entries = "".join(f" {i * 4:X}:{value:08X}" for i, value in enumerate(words) if value)
        lines.append(f"page {page * PAGE:016X}{entries}")
    return "\n".join(lines) + "\n"


def run_python(lanes, scc, scalars, words, memory=()):
    wave = Wave(lanes=lanes)
    wave.scc = scc
    for index, value in scalars:
        wave.s[index] = value
    for address, values in memory:
        wave.memory.write_words(address, values)
    data = struct.pack(f"<{len(words)}I", *words)
    try:
        rdna2_exec.run(data, wave)
    except rdna2_exec.Untranslated:
        return "error untranslated\n"
    except RuntimeError:
        return "error loop\n"
    return render(wave)


def run_rust(exe, lanes, scc, scalars, words, memory=()):
    lines = [f"lanes {lanes}", f"scc {int(scc)}"]
    lines += [f"s {index} {value:X}" for index, value in scalars]
    lines += [f"mem {address:X} " + " ".join(f"{value:08X}" for value in values) for address, values in memory]
    lines.append("program " + " ".join(f"{word:08X}" for word in words))
    done = subprocess.run(
        [str(exe)], input="\n".join(lines) + "\n", capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def assert_same(exe, lanes, scc, scalars, words, memory=()):
    rust = run_rust(exe, lanes, scc, scalars, words, memory)
    python = run_python(lanes, scc, scalars, words, memory)
    assert rust == python, f"lanes={lanes} scc={scc} scalars={scalars} memory={memory}\nprogram={[hex(w) for w in words]}\n" \
                           f"rust:\n{rust}\npython:\n{python}"


def test_the_generated_mnemonic_table_matches_the_python_one():
    text = GENERATED.read_text(encoding="utf-8")
    found = {
        (family, int(opcode, 16)): name
        for family, opcode, name in re.findall(r'\("(\w+)", 0x([0-9A-F]+)\) => "(\w+)"', text)
    }
    assert found == MNEMONICS


def test_fixed_scalar_programs_match_the_python_model():
    exe = binary()
    cases = [
        (32, False, [(0, 0xFFFF_FFFF), (1, 1)], program(sop2("s_add_u32", 2, 0, 1), sop2("s_addc_u32", 3, 0, 1))),
        (32, False, [(0, 0x7FFF_FFFF), (1, 1)], program(sop2("s_add_i32", 2, 0, 1), sop2("s_mul_i32", 3, 0, 1))),
        (32, True, [(0, 5), (1, 9)], program(sop2("s_cselect_b32", 2, 0, 1), sop2("s_cselect_b64", 4, 0, 1))),
        (64, False, [(0, 1), (2, 3)], program(sop2("s_lshl_b64", 4, 0, 2), sop2("s_bfm_b64", 6, 0, 2))),
        (32, False, [(0, 0x12), (1, 7)], program(sop2("s_lshl1_add_u32", 2, 0, 1), sop2("s_bfe_u32", 3, 0, 1))),
        (32, False, [(0, 0xABCD_1234)], program(sop1("s_brev_b32", 1, 0), sop1("s_flbit_i32_b32", 2, 0))),
        (32, False, [(0, 0x80)], program(sop1("s_sext_i32_i8", 1, 0), sop1("s_abs_i32", 2, 1))),
        (32, False, [(0, 0xF0F0), (126, 0xFF)], program(sop1("s_and_saveexec_b32", 3, 0), sop1("s_wqm_b32", 4, 0))),
        (32, False, [(0, 1)], program(sopc("s_cmp_lt_i32", 0, 0), sopk("s_movk_i32", 5, 0xFFFE))),
        (32, False, [(7, 9)], program(sopk("s_addk_i32", 7, 100), sopk("s_cmpk_eq_u32", 7, 109))),
        (32, False, [], program(sopp("s_branch", 1), sop1("s_mov_b32", 0, 255), sop1("s_mov_b32", 1, 130))),
    ]
    for lanes, scc, scalars, words in cases:
        assert_same(exe, lanes, scc, scalars, words)


V0 = 256                        # v0 as a source operand (9 bits)
ONE_F, TWO_F = 242, 244         # inline constants 1.0 and 2.0


def vop1(name, vdst, src0):
    return 0x3F << 25 | vdst << 17 | OPCODES["VOP1", name] << 9 | src0


def vop2(name, vdst, src0, vsrc1):
    return OPCODES["VOP2", name] << 25 | vdst << 17 | vsrc1 << 9 | src0


def test_fixed_vector_programs_match_the_python_model():
    exe = binary()
    cases = [
        (32, False, [], program(vop1("v_cvt_f32_u32", 1, V0), vop2("v_mul_f32", 1, TWO_F, 1),
                                vop2("v_add_f32", 1, ONE_F, 1))),
        (32, False, [], program(vop2("v_add_co_ci_u32", 2, V0, V0), vop2("v_sub_co_ci_u32", 3, V0, 2))),
        (64, True, [], program(vop2("v_add_co_ci_u32", 2, V0, V0), vop1("v_readfirstlane_b32", 5, V0))),
        (32, False, [], program(vop1("v_sqrt_f32", 1, 255), 0xC080_0000, vop2("v_min_f32", 2, 255, 1), 0x7FC0_0000)),
        (32, False, [], [vop2("v_madmk_f32", 1, V0, 2), 0x4000_0000, sopp("s_endpgm")]),
        (32, False, [], program(vop1("v_fract_f32", 1, 255), 0xFF80_0000, vop1("v_rcp_f32", 2, 128))),
        (32, False, [], program(vop1("v_cvt_flr_i32_f32", 1, 255), 0x7FC0_0000)),
    ]
    for lanes, scc, scalars, words in cases:
        assert_same(exe, lanes, scc, scalars, words)


def test_a_literal_operand_is_the_second_word_in_both_models():
    exe = binary()
    words = program(sop1("s_mov_b32", 0, 255), 0xDEAD_BEEF, sop2("s_xor_b32", 1, 0, 255), 0x0F0F_0F0F)
    assert_same(exe, 32, False, [], words)


# Float literals the model treats specially: NaN, infinities, signed zeros, subnormals, the largest finite
# value, one. Half the literals come from this list, the rest are random 32-bit patterns.
SPECIAL_LITERALS = (
    0x7FC0_0000, 0xFFC0_0000, 0x7F80_0000, 0xFF80_0000, 0x0000_0000, 0x8000_0000, 0x0000_0001,
    0x8000_0001, 0x7F7F_FFFF, 0x3F80_0000, 0xC080_0000, 0x3F00_0000, 0x4000_0000,
)
VECTOR_FAMILIES = ("VOP1", "VOP2")
SAD_NAMES = ("v_msad_u8", "v_qsad_pk_u16_u8", "v_mqsad_pk_u16_u8", "v_mqsad_u32_u8")
# SDWA (0xF9), DPP16 (0xFA), DPP8 (0xE9) and DPP8_FI (0xEA): the source codes that announce a second word.
EXT_CODES = (0xF9, 0xFA, 0xE9, 0xEA)
EXT_PROBABILITY = 0.3


def extension_word(rng, code, vsrc1):
    """A random SDWA or DPP word whose scalar sources are readable: no SGPR read of the literal code 255,
    and no scalar read of a VOP2 vsrc1 that is the literal code (both are Python TypeErrors)."""
    word = rng.getrandbits(32)
    if code == 0xF9:
        if word & 0xFF == LITERAL:
            word &= ~(1 << 23)
        if vsrc1 == LITERAL:
            word &= ~(1 << 31)
    return word


def literal_bits(rng):
    return rng.choice(SPECIAL_LITERALS) if rng.random() < 0.5 else rng.getrandbits(32)
# Literal-carrying VOP2 opcodes (v_madmk, v_madak, v_fmamk, v_fmaak, f32 and f16): the literal is always there.
VOP2_WITH_LITERAL = {0x20, 0x21, 0x2C, 0x2D, 0x37, 0x38}


def random_program(rng):
    """Instructions scalaires et vectorielles aléatoires, valides pour les deux modèles.

    Les branches sautent vers le début d'une instruction plus loin dans le programme (ou vers s_endpgm) :
    sans cela un saut tombe dans un mot de données, qui se décode en instruction mémoire (hors du modèle)."""
    names = {family: [] for family in (*SCALAR_FAMILIES, *VECTOR_FAMILIES, "VOPC", "VOP3", "VOP3P")}
    for (family, opcode), name in MNEMONICS.items():
        if family in SCALAR_FAMILIES and name != "s_endpgm" and (
            name in MOVREL_SCALAR or
            name in SCALAR or name in BRANCHES or name in NO_OPERATION
        ):
            names[family].append((opcode, name))
        # Native VOP3 names at opcodes 0x200 and up: the Python routes lower opcodes through the VOP1/VOP2 tables.
        if family == "VOP3" and (
            (name in VECTOR3 and opcode >= 0x200)
            or name in SAD_NAMES
            or (name in VECTOR and name not in LITERAL_OPERATION_NAMES and (0x100 <= opcode < 0x140 or 0x180 <= opcode < 0x200))
            or (name in VECTOR_COMPARE and opcode < 0x100)
            or name in VOP3_CARRY + VOP3_MAD64 + VOP3_LANE + DIV_NAMES
            or name in COMPARE64
            or name in WIDE_GENERIC
            or name in MOVREL_VECTOR
        ):
            names[family].append((opcode, name))
        if family == "VOP1" and (name in WIDE_GENERIC or name in MOVREL_VECTOR):
            names[family].append((opcode, name))
        if family == "VOP3P" and name in DOT_OPERATIONS:
            names[family].append((opcode, name))
        if family == "VOPC" and (name in VECTOR_COMPARE or name in COMPARE64):
            names[family].append((opcode, name))
        if family in VECTOR_FAMILIES and (name in VECTOR or name in VECTOR_NO_OPERATION or name in VOP2_CARRY):
            names[family].append((opcode, name))
    blocks = []  # (words, branch template or None): a branch's offset is patched once the layout is known
    for _ in range(rng.randrange(1, 11)):
        words, template = instruction(rng, names)
        blocks.append((words, template))
    starts, position = [], 0
    for words, _ in blocks:
        starts.append(position)
        position += len(words)
    program_words = []
    for index, (words, template) in enumerate(blocks):
        if template is not None:
            # Target: a later instruction start, or s_endpgm (the position after the last block).
            later = [starts[j] for j in range(index + 1, len(blocks))] + [position]
            target = rng.choice(later[:3])
            words = [template | (target - starts[index] - 1)]
        program_words += words
    return program_words


def instruction(rng, names):
    """One random instruction: (its words, the branch template when it is a branch)."""
    family = rng.choice((*SCALAR_FAMILIES, *VECTOR_FAMILIES, "VOPC", "VOP3", "VOP3P"))
    opcode, name = rng.choice(names[family])
    ssrc0, ssrc1 = rng.choice(OPERANDS), rng.choice(OPERANDS)
    # 64-bit results need the register after sdst: stay below s126 (s127 is the last).
    sdst = rng.randrange(126)
    if family == "SOPP" and name in BRANCHES:
        return [0], 0x17F << 23 | opcode << 16
    if family == "SOP2":
        word = sop2_word(opcode, sdst, ssrc0, ssrc1)
    elif family == "SOP1":
        if name in MOVREL_SCALAR:
            ssrc0 = rng.randrange(106)                               # an indexed SGPR source (s0 to s105)
        word = 0x17D << 23 | sdst << 16 | opcode << 8 | ssrc0
    elif family == "SOPC":
        word = 0x17E << 23 | opcode << 16 | ssrc1 << 8 | ssrc0
    elif family == "SOPK":
        word = 0b1011 << 28 | opcode << 23 | sdst << 16 | rng.getrandbits(16)
    elif family == "SOPP":
        word = 0x17F << 23 | opcode << 16 | rng.randrange(0, 3)
    elif family == "VOP1":
        # v_readfirstlane_b32 writes an SGPR through the vdst field: keep it below s128.
        vdst = rng.randrange(128) if name == "v_readfirstlane_b32" else rng.randrange(255 if name in WIDE_GENERIC else 256)
        if name in MOVREL_VECTOR:
            ssrc0 = rng.randrange(256, 511)                          # an indexed VGPR source
        word = 0x3F << 25 | vdst << 17 | opcode << 9 | ssrc0
    elif family == "VOP3":
        return vop3_words(rng, opcode, name)
    elif family == "VOP3P":
        return vop3p_words(rng, opcode)
    elif family == "VOPC":
        # A VGPR pair as source 0 (64-bit compares read v[n], v[n+1]): n + 1 stays below v256.
        ssrc0 = rng.choice(OPERANDS + list(range(256, 511)))
        word = 0x3E << 25 | opcode << 17 | rng.randrange(255) << 9 | ssrc0
    else:
        vdst, vsrc1 = rng.randrange(256), rng.randrange(256)
        word = opcode << 25 | vdst << 17 | vsrc1 << 9 | ssrc0
    if family in VECTOR_FAMILIES and rng.random() < EXT_PROBABILITY and not (
        family == "VOP2" and opcode in VOP2_WITH_LITERAL
    ):
        # SDWA or DPP: the source code is the extension code, the next word is the extension word.
        code = rng.choice(EXT_CODES)
        return [(word & ~0x1FF) | code, extension_word(rng, code, (word >> 9) & 0xFF if family == "VOP2" else None)], None
    # The operands each family reads from the source fields (vsrc1 of VOP2 is a VGPR, never a literal).
    sources = {"SOP1": (ssrc0,), "VOP1": (ssrc0,), "VOP2": (ssrc0,), "SOP2": (ssrc0, ssrc1), "SOPC": (ssrc0, ssrc1), "VOPC": (ssrc0,)}
    needs_literal = LITERAL in sources.get(family, ()) or (family == "VOP2" and opcode in VOP2_WITH_LITERAL)
    return ([word, literal_bits(rng)] if needs_literal else [word]), None




# VOP3 names of the older encodings: the VOP1 and VOP2 operations written with VOP3 operands, the VOP3b
# carry forms, the 64-bit multiply-add and the lane operations. Their destinations are kept in range
# for the Python model (which indexes SGPRs and register pairs directly).
# Operations whose constant is a literal: the VOP3 form has no literal word unless a source is the literal code.
LITERAL_OPERATION_NAMES = ("v_madmk_f32", "v_madak_f32", "v_fmamk_f32", "v_fmaak_f32")
# The 64-bit operations; v_fma_f64 is left to its own test, where its operands cannot overflow the Python.
WIDE_GENERIC = tuple(name for name in WIDE_OPERATIONS if name != "v_fma_f64")
DIV_NAMES = (
    "v_div_scale_f32", "v_div_scale_f64", "v_div_fmas_f32", "v_div_fmas_f64", "v_div_fixup_f32", "v_div_fixup_f64",
)
VOP3_CARRY = ("v_add_co_u32", "v_sub_co_u32", "v_subrev_co_u32", "v_add_co_ci_u32", "v_sub_co_ci_u32",
              "v_subrev_co_ci_u32")
VOP3_MAD64 = ("v_mad_u64_u32", "v_mad_i64_i32")
VOP3_LANE = ("v_readfirstlane_b32", "v_readlane_b32", "v_writelane_b32", "v_mbcnt_lo_u32_b32", "v_mbcnt_hi_u32_b32")


def vop3_words(rng, opcode, name):
    """A VOP3 instruction: two words (the low half first), a third word when a source is the literal."""
    wide_sources = name in SAD_NAMES or name in VOP3_MAD64 or name.endswith(("_f64", "_u64", "_i64"))
    pool = list(range(256, 511)) if wide_sources else list(range(256, 512))
    if name in COMPARE64 and not name.endswith("class_f32"):
        pool = [code for code in OPERANDS if code != LITERAL] + list(range(256, 511))
    sources = [rng.choice(OPERANDS + pool) for _ in range(3)]
    # The SAD forms refuse any modifier: most of them get none, so that the executed path is covered too.
    plain = (name in SAD_NAMES or name in MOVREL_VECTOR) and rng.random() < 0.7
    if name in MOVREL_VECTOR:
        sources[0] = rng.randrange(256, 511)
    abs_bits = 0 if plain else rng.randrange(8)
    clamp = 0 if plain else rng.randrange(2)
    vdst = rng.randrange(256)
    if name in ("v_readfirstlane_b32", "v_readlane_b32"):
        vdst = rng.randrange(128)                                    # an SGPR destination
    if (name in VECTOR_COMPARE or name in COMPARE64) and "cmpx" not in name:
        vdst = rng.randrange(126)                                    # the compare writes the SGPR pair vdst
    field_8_14 = abs_bits
    if name in VOP3_CARRY or name in VOP3_MAD64:
        vdst = rng.randrange(255)
    if name.endswith("_f64") and name not in COMPARE64:
        vdst = rng.randrange(255)                                    # a 64-bit result takes vdst and vdst + 1
        field_8_14 = rng.randrange(126)                              # the carry SGPR pair sdst
    low = 0x35 << 26 | opcode << 16 | vdst | field_8_14 << 8 | rng.randrange(16) << 11 | clamp << 15
    high = sources[0] | sources[1] << 9 | sources[2] << 18 | (0 if plain else rng.randrange(4)) << 27 | (
        0 if plain else rng.randrange(8)) << 29
    words = [low, high]
    if LITERAL in sources:
        words.append(literal_bits(rng))
    return words, None


def vop3p_words(rng, opcode):
    """A VOP3P dot product: the default form most of the time (op_sel_hi all ones, no modifiers)."""
    sources = [rng.choice(OPERANDS + list(range(256, 512))) for _ in range(3)]
    plain = rng.random() < 0.8
    low = (0x33 << 26 | opcode << 16 | rng.randrange(256) | (1 << 14)
           | (0 if plain else rng.randrange(8) << 8 | rng.randrange(8) << 11 | rng.randrange(2) << 15))
    high = (sources[0] | sources[1] << 9 | sources[2] << 18
            | ((1 << 27 | 1 << 28) if plain else rng.randrange(4) << 27)
            | (0 if plain else rng.randrange(8) << 29))
    words = [low, high]
    if LITERAL in sources:
        words.append(literal_bits(rng))
    return words, None


def sop2_word(opcode, sdst, ssrc0, ssrc1):
    return 0b10 << 30 | opcode << 23 | sdst << 16 | ssrc1 << 8 | ssrc0


def test_random_scalar_programs_match_the_python_model():
    exe = binary()
    rng = random.Random(SEED)
    for _ in range(PROGRAMS):
        lanes = rng.choice((32, 64))
        scc = rng.random() < 0.5
        scalars = [(index, rng.getrandbits(32) if rng.random() < 0.5 else rng.randrange(8)) for index in range(16)]
        scalars.append((124, rng.randrange(256)))                    # M0, the index of the movrel forms
        words = program(*random_program(rng))
        assert_same(exe, lanes, scc, scalars, words)


# Operand bit patterns the division helpers treat specially: zeros, infinities, NaNs, subnormals, the
# largest and smallest normal values, and values near the scale thresholds.
DIVISION_SPECIAL_WORDS = (
    0x0000_0000, 0x8000_0000, 0x3F80_0000, 0xBF80_0000, 0x7F80_0000, 0xFF80_0000, 0x7FC0_0000, 0x0000_0001,
    0x7F7F_FFFF, 0x0080_0000, 0x4000_0000, 0x0080_0001, 0x6000_0000, 0x1000_0000, 0x7480_0000,
)


def test_division_helpers_match_the_python_model():
    """One division helper per program, on SGPR operands (pairs for f64) of special and random bit patterns."""
    exe = binary()
    rng = random.Random(SEED + 1)
    for _ in range(200):
        name = rng.choice(DIV_NAMES)
        opcode = OPCODES["VOP3", name]
        f64 = name.endswith("_f64")
        sources = (0, 2, 4) if f64 else (0, 1, 2)
        plain = rng.random() < 0.5
        neg_bits = 0 if plain else rng.randrange(8)
        clamp = 0 if plain else rng.randrange(2)
        sdst = rng.randrange(126)
        low = 0x35 << 26 | opcode << 16 | sdst << 8 | clamp << 15
        high = sources[0] | sources[1] << 9 | sources[2] << 18 | (0 if plain else rng.randrange(4)) << 27 | neg_bits << 29
        scalars = [
            (index, rng.choice(DIVISION_SPECIAL_WORDS) if rng.random() < 0.6 else rng.getrandbits(32))
            for index in range(8)
        ] + [(106, rng.getrandbits(32))]
        assert_same(exe, 32, False, scalars, program(low, high))


CURATED_DOUBLE_BITS = (
    0x0000_0000_0000_0000, 0x8000_0000_0000_0000, 0x3FF0_0000_0000_0000, 0xC004_0000_0000_0000,
    0x3F5F_F5E4_8E13_A95E, 0x4E33_F8D6_9C53_9B7D, 0xD34B_EE65_6C88_EC6E, 0x7FF0_0000_0000_0000,
    0xFFF0_0000_0000_0000, 0x7FF8_0000_0000_0000, 0x7FF0_0000_0000_0001, 0x0000_0000_0000_0001,
    0x3FE0_0000_0000_0000, 0x3DDB_7CDF_D9D7_BDBB, 0x4159_9A5D_3A7F_D000,
)


def test_wide_operations_match_the_python_model():
    """64-bit operations (f64, 64-bit shifts, f64 fma included) on SGPR pairs of curated doubles."""
    exe = binary()
    rng = random.Random(SEED + 2)
    names = tuple(name for name in WIDE_OPERATIONS if ("VOP3", name) in OPCODES)
    for _ in range(200):
        name = rng.choice(names)
        opcode = OPCODES["VOP3", name]
        low = 0x35 << 26 | opcode << 16 | rng.randrange(1) | rng.randrange(8) << 8 | rng.randrange(2) << 15
        high = 0 | 2 << 9 | 4 << 18 | rng.randrange(4) << 27 | rng.randrange(8) << 29
        scalars = []
        for index in range(8):
            value = rng.choice(CURATED_DOUBLE_BITS) if rng.random() < 0.7 else rng.getrandbits(64)
            scalars += [(index, value & 0xFFFF_FFFF), (index + 8, value >> 32)]
        assert_same(exe, 32, False, scalars, program(low, high))


def smem(name, sdata, sbase, offset=0, soffset=125, glc=0):
    """Les deux mots d'une instruction SMEM (sdata, sbase en SGPR, décalage signé 21 bits, soffset, glc)."""
    first = 0x3D << 26 | OPCODES["SMEM", name] << 18 | glc << 16 | sdata << 6 | sbase // 2
    return first, soffset << 25 | offset & 0x1FFFFF


def test_scalar_memory_programs_match_the_python_model():
    exe = binary()
    cases = [
        # s_load : adresse 64 bits en SGPR, décalage immédiat ou par SOFFSET, décalage négatif (zéros)
        (32, False, [(0, 0x2000), (1, 0), (2, 12)], [(0x2000, [0, 0, 0xDEADBEEF, 0x11])],
         program(*smem("s_load_dword", 4, 0, offset=8), *smem("s_load_dwordx2", 6, 0, offset=8),
                 *smem("s_load_dword", 9, 0, soffset=2), *smem("s_load_dword", 10, 0, offset=-4))),
        # s_buffer_load : V# en s4..s6 (base, pas, nombre d'octets) ; hors du buffer, zéros
        (32, False, [(4, 0x3000), (5, 0), (6, 16)], [(0x3000, [1, 2, 3, 4])],
         program(*smem("s_buffer_load_dwordx2", 8, 4, offset=4), *smem("s_buffer_load_dwordx2", 10, 4, offset=12))),
        (64, False, [(4, 0x3000), (5, 0x10000), (6, 64)], [(0x3000, [5, 6, 7, 8, 9, 10, 11, 12])],
         program(*smem("s_buffer_load_dwordx4", 12, 4, offset=8), *smem("s_buffer_load_dwordx8", 16, 4))),
        # s_store puis s_load du même mot
        (32, False, [(0, 0x4000), (1, 0), (2, 0x1234), (3, 0xABCD)], [],
         program(*smem("s_store_dword", 2, 0, offset=4), *smem("s_load_dword", 9, 0, offset=4),
                 *smem("s_store_dwordx2", 2, 0, offset=16))),
        # atomiques SMEM : ancienne valeur rendue avec GLC, cmpswap, _x2 avec retenue, buffer
        (32, False, [(0, 0x5000), (1, 0), (3, 5)], [(0x5000, [7])],
         program(*smem("s_atomic_add", 3, 0, glc=1))),
        (32, False, [(0, 0x5000), (1, 0), (6, 9), (7, 7)], [(0x5000, [7])],
         program(*smem("s_atomic_cmpswap", 6, 0))),
        (32, False, [(0, 0x5008), (1, 0), (4, 1), (5, 0)], [(0x5008, [0xFFFFFFFF, 0])],
         program(*smem("s_atomic_add_x2", 4, 0, glc=1))),
        (32, False, [(4, 0x5000), (5, 0), (6, 16), (3, 0x77)], [(0x5000, [1, 2])],
         program(*smem("s_buffer_atomic_swap", 3, 4, offset=4, glc=1))),
        # cache control (sans effet), s_memtime (compteur d'instructions)
        (32, False, [(0, 0x6000)], [],
         program(*smem("s_dcache_inv", 0, 0), sop1("s_mov_b32", 1, 128), *smem("s_memtime", 10, 0))),
    ]
    for lanes, scc, scalars, memory, words in cases:
        assert run_python(lanes, scc, scalars, words, memory).startswith("steps"), "le cas doit s'exécuter"
        assert_same(exe, lanes, scc, scalars, words, memory)


def ds(name, vdst=0, addr=0, data0=0, data1=0, offset0=0, offset1=0):
    """Les deux mots d'une instruction DS (décalages, ADDR, DATA0, DATA1, VDST)."""
    first = 0x36 << 26 | OPCODES["DS", name] << 18 | offset1 << 8 | offset0
    return first, addr | data0 << 8 | data1 << 16 | vdst << 24


def words(*items):
    """Mots d'un programme : les tuples (instructions à deux mots) sont aplatis."""
    flat = []
    for item in items:
        flat.extend(item if isinstance(item, tuple) else [item])
    return flat


def test_local_data_share_programs_match_the_python_model():
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)     # v4 = lane * 4
    lane8 = vop2("v_lshlrev_b32", 5, 131, 0)     # v5 = lane * 8
    cases = [
        # mots 32 bits, puis lecture avec ou sans signe, 64 bits, sous-mots
        (32, words(lane4, vop1("v_mov_b32", 1, 255), 0xDEADBEEF,
                   ds("ds_write_b32", addr=4, data0=1), ds("ds_read_b32", vdst=6, addr=4))),
        (32, words(lane8, vop1("v_mov_b32", 1, 255), 0x0000FF80, vop1("v_mov_b32", 2, 255), 0x55AA55AA,
                   ds("ds_write_b64", addr=5, data0=1), ds("ds_read_b64", vdst=8, addr=5),
                   ds("ds_read_i8", vdst=10, addr=5), ds("ds_read_u8", vdst=11, addr=5),
                   ds("ds_read_i16", vdst=12, addr=5), ds("ds_read_u16", vdst=13, addr=5))),
        # read2 et write2 (offsets en octets), écriture de 96 bits et lecture de 128 bits
        (32, words(lane4, vop1("v_mov_b32", 1, 255), 0x01020304, vop1("v_mov_b32", 2, 255), 0xA0B0C0D0,
                   ds("ds_write2_b32", addr=4, data0=1, data1=2, offset0=0, offset1=1),
                   ds("ds_read2_b32", vdst=6, addr=4, offset0=0, offset1=1),
                   ds("ds_write_b96", addr=4, data0=1), ds("ds_read_b128", vdst=10, addr=4))),
        # formes st64 (décalages × 64 éléments), ds_nop, wave64
        (64, words(lane4, vop1("v_mov_b32", 1, 255), 0x77770001, vop1("v_mov_b32", 2, 255), 0x88880002,
                   ds("ds_write2st64_b32", addr=4, data0=1, data1=2, offset0=0, offset1=1),
                   ds("ds_read2st64_b32", vdst=6, addr=4, offset0=0, offset1=1), ds("ds_nop"))),
    ]
    for lanes, program_words in cases:
        python = run_python(lanes, False, [], program_words)
        assert python.startswith("steps"), "le cas doit s'exécuter"
        assert_same(exe, lanes, False, [], program_words)


def test_lds_atomic_programs_match_the_python_model():
    """Atomiques LDS : formes simples, étendues (_rtn ou non), wrxchg2 ; les résultats sont relus
    dans les VGPR (la LDS n'est pas dans l'état rendu)."""
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)     # v4 = lane * 4
    lane8 = vop2("v_lshlrev_b32", 5, 131, 0)     # v5 = lane * 8
    cases = [
        # formes simples 32 bits : add rtn, sub sans retour, max signé rtn, lecture finale
        (32, words(lane4, vop1("v_mov_b32", 1, 255), 0x00000010, vop1("v_mov_b32", 2, 255), 0xFFFFFFFF,
                   vop1("v_mov_b32", 3, 255), 0x00000005,
                   ds("ds_write_b32", addr=4, data0=1),
                   ds("ds_add_rtn_u32", vdst=6, addr=4, data0=3),
                   ds("ds_sub_u32", addr=4, data0=3),
                   ds("ds_max_rtn_i32", vdst=7, addr=4, data0=2),
                   ds("ds_read_b32", vdst=8, addr=4))),
        # formes étendues 64 bits : add, min non signé, rsub, lecture 64 bits
        (32, words(lane8, vop1("v_mov_b32", 1, 255), 0x00000007, vop1("v_mov_b32", 2, 255), 0x00000001,
                   ds("ds_write_b64", addr=5, data0=1),
                   vop1("v_mov_b32", 3, 255), 0x00000003, vop1("v_mov_b32", 4, 255), 0x00000000,
                   ds("ds_add_rtn_u64", vdst=10, addr=5, data0=3),
                   ds("ds_min_rtn_u64", vdst=12, addr=5, data0=1),
                   ds("ds_xor_rtn_b64", vdst=14, addr=5, data0=1),
                   ds("ds_read_b64", vdst=16, addr=5))),
        # mskor, cmpst (DATA0 compare, DATA1 écrit), wrap, rsub, wrxchg, b32 avec retour
        (32, words(lane4, vop1("v_mov_b32", 1, 255), 0xFFFF0000, vop1("v_mov_b32", 2, 255), 0xFF00FF00,
                   vop1("v_mov_b32", 3, 255), 0x000000AB, vop1("v_mov_b32", 5, 255), 0x00000004,
                   ds("ds_write_b32", addr=4, data0=1),
                   ds("ds_mskor_rtn_b32", vdst=6, addr=4, data0=2, data1=3),
                   ds("ds_cmpst_rtn_b32", vdst=7, addr=4, data0=3, data1=5),
                   ds("ds_wrap_rtn_b32", vdst=8, addr=4, data0=5, data1=3),
                   ds("ds_rsub_rtn_u32", vdst=9, addr=4, data0=2),
                   ds("ds_wrxchg_rtn_b32", vdst=10, addr=4, data0=3),
                   ds("ds_read_b32", vdst=11, addr=4))),
        # wrxchg2 : deux échanges à décalages de 1 élément, puis wave64 avec st64 en b64
        (32, words(lane4, vop1("v_mov_b32", 1, 255), 0x11111111, vop1("v_mov_b32", 2, 255), 0x22222222,
                   ds("ds_write2_b32", addr=4, data0=1, data1=2, offset0=0, offset1=1),
                   ds("ds_wrxchg2_rtn_b32", vdst=6, addr=4, data0=2, data1=1, offset0=0, offset1=1),
                   ds("ds_read2_b32", vdst=8, addr=4, offset0=0, offset1=1))),
        (64, words(lane8, vop1("v_mov_b32", 1, 255), 0x00000001, vop1("v_mov_b32", 2, 255), 0x00000002,
                   vop1("v_mov_b32", 20, 255), 0x00000003, vop1("v_mov_b32", 21, 255), 0x00000004,
                   ds("ds_wrxchg2st64_rtn_b64", vdst=10, addr=5, data0=1, data1=20, offset0=0, offset1=1),
                   ds("ds_read_b64", vdst=16, addr=5, offset1=2))),
    ]
    for lanes, program_words in cases:
        python = run_python(lanes, False, [], program_words)
        assert python.startswith("steps"), "le cas doit s'exécuter"
        assert_same(exe, lanes, False, [], program_words)


def test_lds_half_and_lane_exchange_programs_match_the_python_model():
    """Acces _d16 (moitie de VGPR gardee) et ds_swizzle/ds_permute/ds_bpermute, en wave32 et wave64."""
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)     # v4 = lane * 4
    cases = [
        # _d16 : lecture signee et non signee des moities basse et haute, ecritures _hi
        (32, words(lane4, vop1("v_mov_b32", 1, 255), 0x80FF7F80, vop1("v_mov_b32", 6, 255), 0xAAAAAAAA,
                   vop1("v_mov_b32", 7, 255), 0x55555555,
                   ds("ds_write_b32", addr=4, data0=1),
                   ds("ds_read_i8_d16", vdst=6, addr=4),
                   ds("ds_read_u8_d16_hi", vdst=6, addr=4, offset0=1),
                   ds("ds_read_u16_d16", vdst=7, addr=4),
                   ds("ds_read_u16_d16_hi", vdst=7, addr=4, offset0=2),
                   ds("ds_write_b8_d16_hi", addr=4, data0=1, offset0=8),
                   ds("ds_write_b16_d16_hi", addr=4, data0=1, offset0=12),
                   ds("ds_read_b32", vdst=8, addr=4, offset0=8))),
        # ds_swizzle : quad perm, reverse (BITMASK), puis permute et bpermute (decalage de 4 octets)
        (32, words(lane4,
                   ds("ds_swizzle_b32", vdst=6, data0=4, offset0=0xB1, offset1=0x80),
                   ds("ds_swizzle_b32", vdst=7, data0=4, offset0=0x1F, offset1=0x7C),
                   ds("ds_bpermute_b32", vdst=8, addr=4, data0=4, offset0=4),
                   ds("ds_permute_b32", vdst=9, addr=4, data0=4, offset0=4))),
        # wave64 : chaque moitie de 32 lignes echange seule
        (64, words(lane4,
                   ds("ds_swizzle_b32", vdst=6, data0=4, offset0=0xB1, offset1=0x80),
                   ds("ds_bpermute_b32", vdst=8, addr=4, data0=4, offset0=4),
                   ds("ds_permute_b32", vdst=9, addr=4, data0=4, offset0=4))),
    ]
    for lanes, program_words in cases:
        python = run_python(lanes, False, [], program_words)
        assert python.startswith("steps"), "le cas doit s'executer"
        assert_same(exe, lanes, False, [], program_words)


def vmem(family, name, vdst=0, addr=0, data=0, saddr=125, offset=0, glc=0):
    """Les deux mots d'une instruction FLAT, GLOBAL ou SCRATCH (décalage sur 12 bits, GLC, ADDR, DATA,
    SADDR, VDST)."""
    segment = {"FLAT": 0, "SCRATCH": 1, "GLOBAL": 2}[family]     # bits 14-15 du premier mot
    first = 0x37 << 26 | segment << 14 | OPCODES[family, name] << 18 | glc << 16 | offset & 0xFFF
    return first, addr | data << 8 | saddr << 16 | vdst << 24


def test_flat_global_scratch_programs_match_the_python_model():
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)     # v4 = lane * 4 ; v5 reste nul (adresse haute)
    cases = [
        # FLAT : chargements (dword, signé, court, paire), écriture, atomiques avec retour
        (32, [], [(0, list(range(64))), (0x200, [0x80FF7F80] * 64)], words(
            lane4,
            vmem("FLAT", "flat_load_dword", vdst=6, addr=4),
            vmem("FLAT", "flat_store_dword", addr=4, data=6, offset=256),
            vmem("FLAT", "flat_load_sbyte", vdst=8, addr=4, offset=0x200),
            vmem("FLAT", "flat_load_ushort", vdst=9, addr=4, offset=0x200),
            vmem("FLAT", "flat_load_dwordx2", vdst=10, addr=4, offset=0x200),
            vmem("FLAT", "flat_atomic_add", vdst=12, addr=4, data=6, offset=0x300, glc=1),
            vmem("FLAT", "flat_atomic_cmpswap", vdst=14, addr=4, data=6, offset=0x300, glc=1))),
        # GLOBAL avec SADDR (paire SGPR + VGPR 32 bits, décalage négatif), SCRATCH en adresse VGPR
        (64, [(2, 0x1000), (3, 0)], [(0x1000, list(range(64)))], words(
            lane4,
            vmem("GLOBAL", "global_load_dword", vdst=6, addr=4, saddr=2),
            vmem("GLOBAL", "global_store_dword", addr=4, data=6, saddr=2, offset=-4),
            vmem("GLOBAL", "global_load_ubyte", vdst=8, addr=4, saddr=2),
            vmem("SCRATCH", "scratch_store_dword", addr=4, data=6, offset=0x400),
            vmem("SCRATCH", "scratch_load_dword", vdst=9, addr=4, offset=0x400))),
    ]
    for lanes, scalars, memory, program_words in cases:
        python = run_python(lanes, False, scalars, program_words, memory)
        assert python.startswith("steps"), "le cas doit s'exécuter"
        assert_same(exe, lanes, False, scalars, program_words, memory)


def mubuf(name, vdata=0, vaddr=0, srsrc=0, soffset=125, offset=0, offen=0, idxen=0, glc=0):
    """Les deux mots d'une instruction MUBUF (décalage, OFFEN, IDXEN, GLC ; VADDR, VDATA, SRSRC en quadruplets
    de SGPR, SOFFSET)."""
    first = 0x38 << 26 | OPCODES["MUBUF", name] << 18 | glc << 14 | idxen << 13 | offen << 12 | offset & 0xFFF
    return first, vaddr | vdata << 8 | srsrc << 16 | soffset << 24


def test_buffer_programs_match_the_python_model():
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)     # v4 = lane * 4
    cases = [
        # descripteur à pas nul : adresse de base 0x2000, 256 octets ; accès hors des enregistrements
        (32, [(8, 0x2000), (9, 0), (10, 0x100)], [(0x2000, list(range(128)))], words(
            lane4,
            mubuf("buffer_load_dword", vdata=6, vaddr=4, srsrc=2, offen=1),
            mubuf("buffer_store_dword", vdata=6, vaddr=4, srsrc=2, offen=1, offset=0x80),
            mubuf("buffer_load_ubyte", vdata=8, vaddr=4, srsrc=2, offen=1, offset=0x10),
            mubuf("buffer_load_dword", vdata=10, vaddr=4, srsrc=2, idxen=1),
            mubuf("buffer_atomic_add", vdata=6, vaddr=4, srsrc=2, offen=1, offset=0x40, glc=1))),
        # pas de 16 octets avec indice : seuls les indices inférieurs à 8 existent (wave64)
        (64, [(8, 0x3000), (9, 16 << 16), (10, 8)], [(0x3000, list(range(64)))], words(
            lane4,
            mubuf("buffer_load_dword", vdata=6, vaddr=4, srsrc=2, idxen=1),
            mubuf("buffer_store_dword", vdata=6, vaddr=4, srsrc=2, idxen=1, offset=4),
            mubuf("buffer_load_sbyte", vdata=12, vaddr=4, srsrc=2, idxen=1, offen=0, glc=0))),
    ]
    for lanes, scalars, memory, program_words in cases:
        python = run_python(lanes, False, scalars, program_words, memory)
        assert python.startswith("steps"), "le cas doit s'exécuter"
        assert_same(exe, lanes, False, scalars, program_words, memory)


FORMAT_TABLE = REPO / "crates" / "anyxboxx-rdna2-ref" / "src" / "format_table.rs"
# Opcodes MTBUF « xyz » que les tests de LLVM n'essaient pas (rdna2.ISA_ONLY_MNEMONICS).
MTBUF_OPCODES = {**{name: opcode for (family, name), opcode in OPCODES.items() if family == "MTBUF"},
                 "tbuffer_load_format_xyz": 2, "tbuffer_store_format_xyz": 6}
IDENTITY = 4 | 5 << 3 | 6 << 6 | 7 << 9         # DST_SEL X, Y, Z, W
FORMAT_DATA = [0x807F01FF, 0x3C007E01, 0x0001FC00, 0x7FFF8000, 0xFFFFFFFF, 0x00000000, 0x81828384, 0x12345678,
               0x7C00FBFF, 0x00FF7F80, 0xC0000001, 0x40490FDB]


def test_the_generated_format_table_matches_the_python_one():
    from emu.rdna2_buffer_format import FORMATS
    from emu.rdna2_image import FORMAT_NAMES

    text = FORMAT_TABLE.read_text(encoding="utf-8")
    names = {int(code): name for code, name in re.findall(r'\((\d+), "(GFX10_FORMAT_[^"]*)"\)', text)}
    assert names == FORMAT_NAMES
    kinds = {"Unorm": 1, "Snorm": 2, "Uscaled": 3, "Sscaled": 4, "Uint": 5, "Sint": 6, "Float": 7}
    found = {
        int(code): (kinds[kind], tuple(int(width) for width in widths.split(", ")), int(size), int(align))
        for code, kind, widths, size, align in re.findall(
            r"code: (\d+),\s*kind: Kind::(\w+),\s*widths: &\[([\d, ]+)\],\s*size: (\d+),\s*align: (\d+)\b", text)
    }
    assert found == {code: (f.kind, f.widths, f.size, f.align) for code, f in FORMATS.items()}


def mtbuf(name, fmt, vdata=0, vaddr=0, srsrc=0, soffset=125, offset=0, offen=0, idxen=0, tfe=0):
    """Les deux mots d'une instruction MTBUF (MTBUFe_gfx10 de LLVM) : opcode bits 16-18 du premier mot et
    bit 21 du second (Inst{53} = op{3}), FORMAT bits 19-25, TFE bit 23 du second mot."""
    opcode = MTBUF_OPCODES[name]
    first = 0x3A << 26 | fmt << 19 | (opcode & 7) << 16 | idxen << 13 | offen << 12 | offset & 0xFFF
    return first, vaddr | vdata << 8 | srsrc << 16 | (opcode >> 3 & 1) << 21 | tfe << 23 | soffset << 24


def buffer_descriptor(srsrc, word3, base=0x2000, records=0x100, stride=0, word1_high=0):
    """Les quatre SGPR d'un V# (base 48 bits, pas, NUM_RECORDS, mot 3) au quadruplet `srsrc`."""
    first = srsrc * 4
    return [(first, base & 0xFFFFFFFF), (first + 1, (base >> 32) & 0xFFFF | stride << 16 | word1_high),
            (first + 2, records), (first + 3, word3)]


def format_loads(loads, offset=0):
    """Descripteurs et instructions pour une liste de (nom, mot 3 du V#, format MTBUF ou None)."""
    scalars, program_words = [], []
    for k, (name, word3, fmt) in enumerate(loads):
        srsrc, vdata = 2 + k, 8 + 4 * k
        scalars += buffer_descriptor(srsrc, word3)
        fields = dict(vdata=vdata, vaddr=4, srsrc=srsrc, offen=1, offset=offset)
        program_words += mubuf(name, **fields) if fmt is None else mtbuf(name, fmt, **fields)
    return scalars, program_words


def format_memory():
    rng = random.Random(SEED)
    return [(0x2000, FORMAT_DATA + [rng.getrandbits(32) for _ in range(64 - len(FORMAT_DATA))])]


MUBUF_LOADS = [
    ("buffer_load_format_xyzw", IDENTITY | 56 << 12, None),                      # 8_8_8_8_UNORM
    ("buffer_load_format_xyzw", 7 | 6 << 3 | 1 << 6 | 57 << 12, None),           # 8_8_8_8_SNORM, W Z 1 0
    ("buffer_load_format_xyzw", 4 | 5 << 3 | 1 << 6 | 23 << 12, None),           # 16_16_UNORM, X Y 1 0
    ("buffer_load_format_xy", IDENTITY | 24 << 12, None),                        # 16_16_SNORM
    ("buffer_load_format_xyzw", 1 | 4 << 3 | 1 << 6 | 7 << 9 | 60 << 12, None),  # 8_8_8_8_UINT, 1 X 1 W
    ("buffer_load_format_xyzw", IDENTITY | 61 << 12, None),                      # 8_8_8_8_SINT
    ("buffer_load_format_xyzw", IDENTITY | 58 << 12, None),                      # 8_8_8_8_USCALED
    ("buffer_load_format_xyzw", IDENTITY | 59 << 12, None),                      # 8_8_8_8_SSCALED
    ("buffer_load_format_xyzw", 4 | 5 << 3 | 1 << 6 | 29 << 12, None),           # 16_16_FLOAT, X Y 1 0
    ("buffer_load_format_xy", 4 | 1 << 3 | 22 << 12, None),                      # 32_FLOAT, X 1
    ("buffer_load_format_xyzw", IDENTITY | 50 << 12, None),                      # 2_10_10_10_UNORM
    ("buffer_load_format_xyzw", IDENTITY | 51 << 12, None),                      # 2_10_10_10_SNORM
    ("buffer_load_format_x", IDENTITY | 7 << 12, None),                          # 16_UNORM
    ("buffer_load_format_x", IDENTITY | 8 << 12, None),                          # 16_SNORM
    ("buffer_load_format_xy", 4 | 1 << 3 | 2 << 12, None),                       # 8_SNORM, X 1
    ("buffer_load_format_x", IDENTITY | 13 << 12, None),                         # 16_FLOAT
]
MTBUF_LOADS = [
    ("tbuffer_load_format_x", 0xFFF | 1 << 12, 1),      # 8_UNORM (DST_SEL du V# ignorés)
    ("tbuffer_load_format_xy", 1 << 12, 15),            # 8_8_SNORM
    ("tbuffer_load_format_xyz", 1 << 12, 74),           # 32_32_32_FLOAT
    ("tbuffer_load_format_xyzw", 1 << 12, 71),          # 16_16_16_16_FLOAT
    ("tbuffer_load_format_xyzw", 1 << 12, 75),          # 32_32_32_32_UINT
    ("tbuffer_load_format_x", 1 << 12, 12),             # 16_SINT
    ("tbuffer_load_format_xyzw", 0, 56),                # V# FORMAT INVALID : composantes nulles
    ("tbuffer_load_format_xyz", 1 << 12, 54),           # 2_10_10_10_UINT
    ("tbuffer_load_format_xy", 1 << 12, 26),            # 16_16_SSCALED
]


def test_typed_buffer_loads_match_the_python_model():
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)     # v4 = lane * 4
    cases = []
    for lanes in (32, 64):
        # décalage 0xF0 ou 0xE8 : les lignes hautes sortent des 256 octets (DST_SEL = 1 reste 1)
        for loads, offset in ((MUBUF_LOADS, 0), (MUBUF_LOADS, 0xF0), (MTBUF_LOADS, 0), (MTBUF_LOADS, 0xE8)):
            scalars, program_words = format_loads(loads, offset=offset)
            cases.append((lanes, scalars, words(lane4, *program_words)))
    # pas de 8 octets avec indice : seuls les indices inférieurs à 20 existent
    strided = buffer_descriptor(2, IDENTITY | 65 << 12, stride=8, records=20)
    cases.append((64, strided, words(mubuf("buffer_load_format_xyzw", vdata=8, vaddr=0, srsrc=2, idxen=1))))
    for lanes, scalars, program_words in cases:
        python = run_python(lanes, False, scalars, program_words, format_memory())
        assert python.startswith("steps"), f"le cas doit s'exécuter : {python}"
        assert_same(exe, lanes, False, scalars, program_words, format_memory())


STORES = [
    (mubuf, "buffer_store_format_xyzw", 3, IDENTITY | 61 << 12, None, 0x000),          # 8_8_8_8_SINT
    (mubuf, "buffer_store_format_xy", 4, 4 | 5 << 3 | 1 << 6 | 27 << 12, None, 0x080),  # 16_16_UINT
    (mubuf, "buffer_store_format_xyzw", 5, IDENTITY | 54 << 12, None, 0x100),          # 2_10_10_10_UINT
    (mubuf, "buffer_store_format_x", 6, IDENTITY | 22 << 12, None, 0x180),             # 32_FLOAT
    (mubuf, "buffer_store_format_xyz", 7, IDENTITY | 35 << 12, None, 0x200),           # 10_11_11_SINT
    (mtbuf, "tbuffer_store_format_xyzw", 8, 1 << 12, 70, 0x280),                       # 16_16_16_16_SINT
    (mtbuf, "tbuffer_store_format_xy", 9, 1 << 12, 62, 0x300),                         # 32_32_UINT
    (mtbuf, "tbuffer_store_format_x", 10, 0, 5, 0x380),                                # V# INVALID : rien
    (mtbuf, "tbuffer_store_format_xyz", 11, 1 << 12, 41, 0x3C0),                       # 11_11_10_UINT
]


def test_typed_buffer_stores_match_the_python_model():
    exe = binary()
    lane4 = vop2("v_lshlrev_b32", 4, 130, 0)
    for lanes in (32, 64):
        scalars = buffer_descriptor(2, IDENTITY | 20 << 12)
        program_words = [lane4, *mubuf("buffer_load_dwordx4", vdata=20, vaddr=4, srsrc=2, offen=1)]
        for encode, name, srsrc, word3, fmt, offset in STORES:
            scalars += buffer_descriptor(srsrc, word3, base=0x3000, records=0x400)
            fields = dict(vdata=20, vaddr=4, srsrc=srsrc, offen=1, offset=offset)
            program_words += encode(name, **fields) if fmt is None else encode(name, fmt, **fields)
        program_words = words(*program_words)
        python = run_python(lanes, False, scalars, program_words, format_memory())
        assert python.startswith("steps"), f"le cas doit s'exécuter : {python}"
        assert_same(exe, lanes, False, scalars, program_words, format_memory())


def refused_format_accesses():
    """(mot 3 du V#, bits hauts du mot 1, instruction) refusés par les deux modèles."""
    lds = mubuf("buffer_load_format_x", vdata=8, srsrc=2)
    return [
        (IDENTITY, 0, mubuf("buffer_load_format_x", vdata=8, srsrc=2)),                       # FORMAT INVALID
        (IDENTITY | 36 << 12, 0, mubuf("buffer_load_format_x", vdata=8, srsrc=2)),            # 10_11_11_FLOAT
        (IDENTITY | 1 << 12, 0, mubuf("buffer_store_format_x", vdata=8, srsrc=2)),            # 8_UNORM écrit
        (IDENTITY | 13 << 12, 0, mubuf("buffer_store_format_x", vdata=8, srsrc=2)),           # 16_FLOAT écrit
        (7 | 14 << 12, 0, mubuf("buffer_load_format_x", vdata=8, srsrc=2)),                   # DST_SEL W, 8_8
        (2 | 22 << 12, 0, mubuf("buffer_load_format_x", vdata=8, srsrc=2)),                   # DST_SEL 2
        (IDENTITY | 18 << 12, 0, mubuf("buffer_store_format_x", vdata=8, srsrc=2)),           # 1 composante sur 2
        (IDENTITY | 18 << 12, 0, mubuf("buffer_store_format_xy", vdata=8, srsrc=2)),          # DST_SEL_Z = Z
        (5 | 4 << 3 | 20 << 12, 0, mubuf("buffer_store_format_x", vdata=8, srsrc=2)),         # DST_SEL Y X
        (1 << 12, 0, mtbuf("tbuffer_load_format_xyz", 23, vdata=8, srsrc=2)),                 # 3 sur 16_16
        (1 << 12, 0, mtbuf("tbuffer_load_format_x", 22, vdata=8, srsrc=2, tfe=1)),            # tfe
        (1 << 12, 0, mtbuf("tbuffer_load_format_d16_x", 22, vdata=8, srsrc=2)),               # _d16
        (IDENTITY | 27 << 12, 0, mubuf("buffer_load_format_x", vdata=8, srsrc=2, offset=1)),  # non aligné
        (IDENTITY | 22 << 12, 0, (lds[0] | 1 << 16, lds[1])),                                 # lds
        (IDENTITY | 22 << 12, 1 << 31, lds),                                                  # SWIZZLE_ENABLE
        (IDENTITY | 22 << 12 | 1 << 23, 0, lds),                                              # ADD_TID_ENABLE
    ]


def test_refused_typed_buffer_accesses_match_the_python_model():
    exe = binary()
    for word3, word1_high, instruction in refused_format_accesses():
        scalars = buffer_descriptor(2, word3, word1_high=word1_high)
        program_words = words(instruction)
        assert run_python(32, False, scalars, program_words) == "error untranslated\n", hex(word3)
        assert_same(exe, 32, False, scalars, program_words)
