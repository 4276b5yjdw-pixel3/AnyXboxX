"""Traduction HLSL de image_sample : le même échantillonnage logiciel que l'interpréteur.

Le shader lit le T# et le S# dans ses SGPR et le texel dans la mémoire u0, comme
emu/rdna2_exec_image.py, pour rester identique au bit près. Les champs de l'instruction sont
vérifiés à la traduction ; un descripteur hors du cas pris en charge (connu seulement à
l'exécution) donne des zéros, alors que l'interpréteur le refuse en le nommant.
"""
from emu import rdna2_image as images
from emu.rdna2_hlsl_ops import Untranslatable

_TABLE = ", ".join(f"0x{value:08X}u" for value in images.UNORM8)

HELPERS = f"""
static const uint UNORM8[256] = {{ {_TABLE} }};

uint ImageWidth(uint4 t) {{ return (((t.y >> 30) & 3u) | ((t.z & 0xFFFu) << 2)) + 1u; }}
uint ImageHeight(uint4 t) {{ return ((t.z >> 14) & 0x3FFFu) + 1u; }}

int ImageIndex(uint bits, uint size, uint unnormalized, uint mode) {{
  precise float value = asfloat(bits);
  if (unnormalized == 0u) value = value * float(size);
  uint raw = asuint(value);
  if ((raw & 0x7F800000u) == 0x7F800000u && (raw & 0x007FFFFFu) != 0u) return 0;   // NaN
  int index = int(floor(clamp(value, -2147483648.0f, 2147483520.0f)));
  if (mode == {images.CLAMP_WRAP}u) {{ int r = index % int(size); return r < 0 ? r + int(size) : r; }}
  return clamp(index, 0, int(size) - 1);
}}

uint4 ImageTexel(uint4 t, int x, int y) {{
  uint format = (t.y >> 20) & 0x1FFu;
  uint pixel = uint(y) * ImageWidth(t) + uint(x);
  uint base = t.x << 8;
  if (format == {images.FORMAT_32_32_32_32_FLOAT}u) return g_memory.Load4(base + pixel * 16u);
  if (format == {images.FORMAT_8_8_8_8_UNORM}u) {{
    uint w = g_memory.Load(base + pixel * 4u);
    return uint4(UNORM8[w & 255u], UNORM8[(w >> 8) & 255u], UNORM8[(w >> 16) & 255u], UNORM8[w >> 24]);
  }}
  return uint4(0u, 0u, 0u, 0u);
}}

uint ImageSelect(uint4 c, uint sel) {{
  if (sel >= {images.SELECT_X}u) return c[sel - {images.SELECT_X}u];
  return sel == {images.SELECT_ONE}u ? {images.ONE_BITS:#x}u : 0u;
}}
"""


def statements(name, word, active):
    """HLSL d'une instruction MIMG ; `word` : l'instruction entière (mot NSA compris)."""
    fields = images.instruction_fields(word)
    try:
        images.check_instruction(name, fields)
    except images.ImageError as error:
        raise Untranslatable(str(error)) from None
    r, q = fields["srsrc"], fields["ssamp"]
    s_register, t_register = images.coordinate_registers(fields)
    components = [k for k in range(4) if fields["dmask"] >> k & 1]
    lines = [f"uint4 t = uint4(s[{r}], s[{r + 1}], s[{r + 2}], s[{r + 3}]);",
             f"uint un = {fields['unorm']}u | ((s[{q}] >> 15) & 1u);",
             f"int x = ImageIndex(v[{s_register}], ImageWidth(t), un, s[{q}] & 7u);",
             f"int y = ImageIndex(v[{t_register}], ImageHeight(t), un, (s[{q}] >> 3) & 7u);",
             "uint4 c = ImageTexel(t, x, y);"]
    lines += [f"uint r{n} = ImageSelect(c, (t.w >> {3 * k}) & 7u);" for n, k in enumerate(components)]
    lines += [f"v[{fields['vdata'] + n}] = r{n};" for n in range(len(components))]
    return [f"if ({active}) {{ " + " ".join(lines) + " }"]
