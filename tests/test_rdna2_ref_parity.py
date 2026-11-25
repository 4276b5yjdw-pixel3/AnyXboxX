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
from emu.rdna2_exec import Wave
from emu.rdna2_exec_ops import BRANCHES, NO_OPERATION, SCALAR
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
    return "\n".join(lines) + "\n"


def run_python(lanes, scc, scalars, words):
    wave = Wave(lanes=lanes)
    wave.scc = scc
    for index, value in scalars:
        wave.s[index] = value
    data = struct.pack(f"<{len(words)}I", *words)
    try:
        rdna2_exec.run(data, wave)
    except rdna2_exec.Untranslated:
        return "error untranslated\n"
    except RuntimeError:
        return "error loop\n"
    return render(wave)


def run_rust(exe, lanes, scc, scalars, words):
    lines = [f"lanes {lanes}", f"scc {int(scc)}"]
    lines += [f"s {index} {value:X}" for index, value in scalars]
    lines.append("program " + " ".join(f"{word:08X}" for word in words))
    done = subprocess.run(
        [str(exe)], input="\n".join(lines) + "\n", capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def assert_same(exe, lanes, scc, scalars, words):
    rust = run_rust(exe, lanes, scc, scalars, words)
    python = run_python(lanes, scc, scalars, words)
    assert rust == python, f"lanes={lanes} scc={scc} scalars={scalars}\nprogram={[hex(w) for w in words]}\n" \
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


def test_a_literal_operand_is_the_second_word_in_both_models():
    exe = binary()
    words = program(sop1("s_mov_b32", 0, 255), 0xDEAD_BEEF, sop2("s_xor_b32", 1, 0, 255), 0x0F0F_0F0F)
    assert_same(exe, 32, False, [], words)


def random_program(rng):
    """Instructions scalaires aléatoires, valides pour les deux modèles, branches vers l'avant seulement."""
    names = {family: [] for family in SCALAR_FAMILIES}
    for (family, opcode), name in MNEMONICS.items():
        if family in names and name != "s_endpgm" and (name in SCALAR or name in BRANCHES or name in NO_OPERATION):
            names[family].append((opcode, name))
    words = []
    for _ in range(rng.randrange(1, 11)):
        family = rng.choice(SCALAR_FAMILIES)
        opcode, name = rng.choice(names[family])
        ssrc0, ssrc1 = rng.choice(OPERANDS), rng.choice(OPERANDS)
        sdst = rng.randrange(128)
        if family == "SOP2":
            word = sop2_word(opcode, sdst, ssrc0, ssrc1)
        elif family == "SOP1":
            word = 0x17D << 23 | sdst << 16 | opcode << 8 | ssrc0
        elif family == "SOPC":
            word = 0x17E << 23 | opcode << 16 | ssrc1 << 8 | ssrc0
        elif family == "SOPK":
            word = 0b1011 << 28 | opcode << 23 | sdst << 16 | rng.getrandbits(16)
        else:
            simm16 = rng.randrange(1, 4) if name in BRANCHES else rng.randrange(0, 3)
            word = 0x17F << 23 | opcode << 16 | simm16
        words.append(word)
        # Only the operands the family reads count: SOP1 has one source, the others two.
        sources = (ssrc0,) if family == "SOP1" else (ssrc0, ssrc1) if family in ("SOP2", "SOPC") else ()
        if LITERAL in sources:
            words.append(rng.getrandbits(32))
    return words


def sop2_word(opcode, sdst, ssrc0, ssrc1):
    return 0b10 << 30 | opcode << 23 | sdst << 16 | ssrc1 << 8 | ssrc0


def test_random_scalar_programs_match_the_python_model():
    exe = binary()
    rng = random.Random(SEED)
    for _ in range(PROGRAMS):
        lanes = rng.choice((32, 64))
        scc = rng.random() < 0.5
        scalars = [(index, rng.getrandbits(32) if rng.random() < 0.5 else rng.randrange(8)) for index in range(16)]
        words = program(*random_program(rng))
        assert_same(exe, lanes, scc, scalars, words)
