"""image_sample dans l'interpréteur RDNA 2 : échantillonnage au plus proche d'une image 2D.

Descripteurs et cas pris en charge : emu/rdna2_image.py. Le texel est choisi comme
floor(s × largeur) (coordonnées normalisées) ou floor(s) (non normalisées), puis replié (wrap) ou
borné au dernier texel (clamp-to-edge) ; NaN donne 0. Le HLSL généré fait le même calcul.
"""
import math

from emu import rdna2_image as images
from emu.rdna2_exec_ops import bits_float, float_bits

FAMILIES = frozenset({"MIMG"})
INT_MIN, INT_MAX_FLOAT = -2147483648.0, 2147483520.0   # bornes float32 d'un entier signé 32 bits


def supports(family, name):
    return family in FAMILIES and name in images.SUPPORTED_OPS


def texel_index(bits, size, unnormalized, mode):
    """Indice de texel sur un axe, à partir de la coordonnée float32 `bits`."""
    value = bits_float(bits)
    if not unnormalized:
        value = bits_float(float_bits(value * size))
    if math.isnan(value):
        return 0
    index = int(math.floor(min(max(value, INT_MIN), INT_MAX_FLOAT)))
    if mode == images.CLAMP_WRAP:
        return index % size
    return min(max(index, 0), size - 1)


def texel(memory, image, x, y):
    """Les 4 canaux (bits float32) du texel (x, y)."""
    address = image["address"] + (y * image["width"] + x) * images.TEXEL_BYTES[image["format"]]
    if image["format"] == images.FORMAT_32_32_32_32_FLOAT:
        return list(memory.read_words(address, 4))
    word = memory.read_words(address, 1)[0]
    return [images.UNORM8[(word >> (8 * channel)) & 0xFF] for channel in range(4)]


def swizzled(channels, swizzle):
    selected = {images.SELECT_ZERO: 0, images.SELECT_ONE: images.ONE_BITS}
    return [channels[sel - images.SELECT_X] if sel >= images.SELECT_X else selected.get(sel, 0) for sel in swizzle]


def execute(wave, name, word):
    """Exécute une instruction MIMG ; `word` : l'instruction entière."""
    from emu.rdna2_exec import Untranslated

    fields = images.instruction_fields(word)
    try:
        images.check_instruction(name, fields)
        image = images.image([wave.s[fields["srsrc"] + i] for i in range(8)])
        sampler = images.sampler([wave.s[fields["ssamp"] + i] for i in range(4)])
    except images.ImageError as error:
        raise Untranslated(str(error)) from None
    unnormalized = fields["unorm"] or sampler["unnormalized"]
    s_register, t_register = images.coordinate_registers(fields)
    for lane in wave.active():
        x = texel_index(wave.v[s_register][lane], image["width"], unnormalized, sampler["clamp_x"])
        y = texel_index(wave.v[t_register][lane], image["height"], unnormalized, sampler["clamp_y"])
        result = swizzled(texel(wave.memory, image, x, y), image["swizzle"])
        written = 0
        for component in range(4):
            if fields["dmask"] >> component & 1:
                wave.v[fields["vdata"] + written][lane] = result[component]
                written += 1
