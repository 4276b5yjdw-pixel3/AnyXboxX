"""Images RDNA 2 (MIMG) : champs de l'instruction, descripteurs T# (image) et S# (échantillonneur).

Positions des champs : décodage de Leonida, runtime/src/gfx10_descriptors.h (GPL-3.0, d'après le
registre de Mesa src/amd/registers/gfx10-rsrc.json, MIT) ; encodage MIMG gfx10 : LLVM
SIInstrFormats.td (MIMGe_gfx10, Apache 2.0). Noms des formats : data/gfx10_formats.json (Leonida).

Échantillonnage pris en charge (le reste est refusé en le nommant) : image 2D linéaire (lignes de
width × taille du texel), filtre au plus proche, adressage wrap ou clamp-to-edge, formats
8_8_8_8_UNORM et 32_32_32_32_FLOAT. L'interpréteur et le HLSL font le même calcul, au bit près.
"""
import json
import struct
from pathlib import Path

DWORD = 4
FORMAT_NAMES = {int(code): name for code, name in
                json.loads((Path(__file__).parent / "data" / "gfx10_formats.json").read_text(encoding="utf-8")).items()}
FORMAT_8_8_8_8_UNORM, FORMAT_32_32_32_32_FLOAT = 56, 77
TEXEL_BYTES = {FORMAT_8_8_8_8_UNORM: 4, FORMAT_32_32_32_32_FLOAT: 16}
TYPE_2D = 9
DIM_2D = 1
CLAMP_WRAP, CLAMP_LAST_TEXEL = 0, 2
FILTER_POINT = 0
SELECT_ZERO, SELECT_ONE, SELECT_X = 0, 1, 4
ONE_BITS = 0x3F800000
# float32 exact de c / 255 (conversion UNORM 8 bits), table partagée avec le HLSL.
UNORM8 = tuple(struct.unpack("<I", struct.pack("<f", value / 255.0))[0] for value in range(256))
SUPPORTED_OPS = frozenset({"image_sample"})


class ImageError(ValueError):
    """Instruction ou descripteur d'image non pris en charge."""


def instruction_fields(word):
    """Champs MIMG gfx10 ; `word` : l'instruction entière (64 bits + mot NSA éventuel)."""
    nsa = (word >> 1) & 0x3
    addresses = [(word >> 32) & 0xFF] + [(word >> (64 + 8 * k)) & 0xFF for k in range(4 * nsa)]
    return {"nsa": nsa, "dim": (word >> 3) & 0x7, "dmask": (word >> 8) & 0xF, "unorm": (word >> 12) & 1,
            "r128": (word >> 15) & 1, "tfe": (word >> 16) & 1, "lwe": (word >> 17) & 1,
            "vaddr": addresses, "vdata": (word >> 40) & 0xFF, "srsrc": ((word >> 48) & 0x1F) * 4,
            "ssamp": ((word >> 53) & 0x1F) * 4, "a16": (word >> 62) & 1, "d16": (word >> 63) & 1}


def check_instruction(name, fields):
    if name not in SUPPORTED_OPS:
        raise ImageError(f"instruction d'image non prise en charge : {name}")
    if fields["dim"] != DIM_2D:
        raise ImageError(f"{name} : dimension {fields['dim']} non prise en charge (2D seulement)")
    for flag in ("r128", "tfe", "lwe", "a16", "d16"):
        if fields[flag]:
            raise ImageError(f"{name} : option {flag} non prise en charge")


def coordinate_registers(fields):
    """VGPR de s et de t : consécutifs, ou donnés par le mot NSA."""
    if fields["nsa"]:
        return fields["vaddr"][0], fields["vaddr"][1]
    return fields["vaddr"][0], fields["vaddr"][0] + 1


def _get(word, low, width):
    return (word >> low) & ((1 << width) - 1)


def image(words):
    """T# (8 mots) → dictionnaire ; ImageError si le descripteur sort du cas pris en charge."""
    kind = _get(words[3], 28, 4)
    fmt = _get(words[1], 20, 9)
    found = {"address": ((_get(words[1], 0, 8) << 32 | words[0]) << 8), "format": fmt, "type": kind,
             "width": (_get(words[1], 30, 2) | _get(words[2], 0, 12) << 2) + 1,
             "height": _get(words[2], 14, 14) + 1,
             "swizzle": [_get(words[3], 3 * i, 3) for i in range(4)]}
    if kind != TYPE_2D:
        raise ImageError(f"T# de type {kind} non pris en charge (2D = {TYPE_2D})")
    if fmt not in TEXEL_BYTES:
        raise ImageError(f"format {FORMAT_NAMES.get(fmt, fmt)} non pris en charge")
    return found


def sampler(words):
    """S# (4 mots) → dictionnaire ; ImageError hors du cas pris en charge."""
    found = {"clamp_x": _get(words[0], 0, 3), "clamp_y": _get(words[0], 3, 3),
             "unnormalized": _get(words[0], 15, 1),
             "mag_filter": _get(words[2], 20, 2), "min_filter": _get(words[2], 22, 2)}
    for axis in ("clamp_x", "clamp_y"):
        if found[axis] not in (CLAMP_WRAP, CLAMP_LAST_TEXEL):
            raise ImageError(f"S# : adressage {found[axis]} non pris en charge (wrap ou clamp-to-edge)")
    if found["mag_filter"] != FILTER_POINT or found["min_filter"] != FILTER_POINT:
        raise ImageError("S# : filtrage bilinéaire non pris en charge (au plus proche seulement)")
    return found


def encode_image(address, fmt, width, height, swizzle=(4, 5, 6, 7)):
    """T# d'une image 2D (pour les tests et les outils) ; inverse de image()."""
    units = address >> 8
    words = [units & 0xFFFFFFFF, (units >> 32) & 0xFF | fmt << 20 | ((width - 1) & 0x3) << 30,
             (width - 1) >> 2 | (height - 1) << 14,
             sum(sel << (3 * i) for i, sel in enumerate(swizzle)) | TYPE_2D << 28, 0, 0, 0, 0]
    return words


def encode_sampler(clamp_x=CLAMP_LAST_TEXEL, clamp_y=CLAMP_LAST_TEXEL, unnormalized=0):
    return [clamp_x | clamp_y << 3 | unnormalized << 15, 0, 0, 0]
