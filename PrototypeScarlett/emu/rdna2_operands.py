"""Opérandes des instructions RDNA 2 : champs, registres et constantes, au format de LLVM.

Couvre les encodages scalaires (SOP1, SOP2, SOPC, SOPK, SOPP) et vectoriels 32 bits
(VOP1, VOP2, VOPC). La forme de chaque opcode (quels champs, dans quel ordre, quelle
largeur de registre) vient de rdna2_ops.SHAPES, apprise sur les tests de LLVM.
"""
import struct

from emu import rdna2

LITERAL = 255
INLINE_FLOATS = {240: "0.5", 241: "-0.5", 242: "1.0", 243: "-1.0", 244: "2.0", 245: "-2.0",
                 246: "4.0", 247: "-4.0", 248: "0.15915494"}
NAMED = {124: "m0", 125: "null", 235: "src_shared_base", 236: "src_shared_limit",
         237: "src_private_base", 238: "src_private_limit", 239: "src_pops_exiting_wave_id",
         251: "src_vccz", 252: "src_execz", 253: "src_scc", 254: "src_lds_direct"}
PAIRS = {106: ("vcc_lo", "vcc"), 126: ("exec_lo", "exec")}
HIGH_HALVES = {107: "vcc_hi", 127: "exec_hi"}
SGPR_LAST, TTMP_FIRST, TTMP_LAST, VGPR_FIRST = 105, 108, 123, 256

# Champs de chaque famille : nom → (décalage, masque, genre).
FIELDS = {
    "SOP2": {"sdst": (16, 0x7F, "src"), "ssrc0": (0, 0xFF, "src"), "ssrc1": (8, 0xFF, "src")},
    "SOP1": {"sdst": (16, 0x7F, "src"), "ssrc0": (0, 0xFF, "src")},
    "SOPC": {"ssrc0": (0, 0xFF, "src"), "ssrc1": (8, 0xFF, "src")},
    "SOPK": {"sdst": (16, 0x7F, "src"), "simm16": (0, 0xFFFF, "imm")},
    "SOPP": {"simm16": (0, 0xFFFF, "imm")},
    # v_readfirstlane_b32 écrit un registre scalaire dans le champ vdst : « sdst » en est la lecture scalaire.
    "VOP1": {"vdst": (17, 0xFF, "vgpr"), "src0": (0, 0x1FF, "src"), "sdst": (17, 0xFF, "src")},
    "VOP2": {"vdst": (17, 0xFF, "vgpr"), "src0": (0, 0x1FF, "src"), "vsrc1": (9, 0xFF, "vgpr")},
    "VOPC": {"src0": (0, 0x1FF, "src"), "vsrc1": (9, 0xFF, "vgpr")},
}
FAMILIES = frozenset(FIELDS)
IMMEDIATE_FORMATS = ("auto", "dec", "sdec", "hex", "hwreg", "waitcnt")
INLINE_INTEGER_MAX = 64                  # LLVM écrit en décimal jusqu'à 64, en hexadécimal au-delà
HWREG_DEFAULT_SIZE = 32
WAITCNT_MAX = {"vmcnt": 0x3F, "expcnt": 0x7, "lgkmcnt": 0x3F}


def _range(prefix, first, width):
    return f"{prefix}{first}" if width == 1 else f"{prefix}[{first}:{first + width - 1}]"


def source(code, width=1, literal=None):
    """Texte d'un opérande source (ou destination scalaire) encodé sur 9 bits."""
    if code >= VGPR_FIRST:
        return _range("v", code - VGPR_FIRST, width)
    if code <= SGPR_LAST:
        return _range("s", code, width)
    if TTMP_FIRST <= code <= TTMP_LAST:
        return _range("ttmp", code - TTMP_FIRST, width)
    if code in PAIRS:
        return PAIRS[code][width > 1]
    if code in HIGH_HALVES:
        return HIGH_HALVES[code]
    if code in NAMED:
        return NAMED[code]
    if 128 <= code <= 192:
        return str(code - 128)
    if 193 <= code <= 208:
        return str(192 - code)
    if code in INLINE_FLOATS:
        return INLINE_FLOATS[code]
    if code == LITERAL:
        return "<littéral>" if literal is None else f"0x{literal:x}"
    return f"<réservé {code}>"


def hwreg(value):
    """simm16 de s_getreg/s_setreg : identifiant (bits 5-0), décalage (10-6), taille - 1 (15-11)."""
    from emu.rdna2_shapes import HWREG_NAMES

    ident, offset, size = value & 0x3F, (value >> 6) & 0x1F, ((value >> 11) & 0x1F) + 1
    name = HWREG_NAMES.get(ident, str(ident))
    if offset == 0 and size == HWREG_DEFAULT_SIZE:
        return f"hwreg({name})"
    return f"hwreg({name}, {offset}, {size})"


def waitcnt(value):
    """simm16 de s_waitcnt : vmcnt (bits 3-0 et 15-14), expcnt (6-4), lgkmcnt (13-8)."""
    counters = {"vmcnt": (value & 0xF) | ((value >> 14) & 0x3) << 4,
                "expcnt": (value >> 4) & 0x7, "lgkmcnt": (value >> 8) & 0x3F}
    shown = [f"{name}({count})" for name, count in counters.items() if count != WAITCNT_MAX[name]]
    return " ".join(shown) or f"0x{value:x}"


def immediate(value, style):
    if style == "auto":
        return str(value) if value <= INLINE_INTEGER_MAX else f"0x{value:x}"
    if style == "hwreg":
        return hwreg(value)
    if style == "waitcnt":
        return waitcnt(value)
    if style == "hex":
        return f"0x{value:x}"
    if style == "sdec" and value >= 0x8000:
        return str(value - 0x10000)
    return str(value)


def render(family, word, literal, element):
    """Texte d'un élément de forme : ("=", texte fixe) ou (champ, largeur ou style)."""
    name, option = element
    if name == "=":
        return option
    if name == "literal":
        return "<littéral>" if literal is None else f"0x{literal:x}"
    shift, mask, kind = FIELDS[family][name]
    value = (word >> shift) & mask
    if kind == "imm":
        return immediate(value, option)
    if kind == "vgpr":
        return _range("v", value, option)
    return source(value, option, literal)


ALIASES = frozenset({("VOP1", "sdst")})


def default_shape(family):
    return tuple((name, "dec" if kind == "imm" else 1) for name, (_, _, kind) in FIELDS[family].items()
                 if (family, name) not in ALIASES)


def text(data, offset=0):
    """Instruction désassemblée au format de LLVM, ou None si la famille n'est pas couverte."""
    from emu.rdna2_shapes import SHAPES

    family, opcode, size = rdna2.classify(data, offset)
    name = rdna2.mnemonic(family, opcode)
    if family not in FAMILIES or name is None:
        return None
    word = struct.unpack_from("<I", data, offset)[0]
    literal = None
    if size > 1 and len(data) >= offset + 2 * rdna2.DWORD:
        literal = struct.unpack_from("<I", data, offset + rdna2.DWORD)[0]
    shape = SHAPES.get((family, opcode), default_shape(family))
    operands = ", ".join(render(family, word, literal, element) for element in shape)
    return f"{name} {operands}".rstrip()
