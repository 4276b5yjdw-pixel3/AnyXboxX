"""Traduction RDNA 2 → HLSL, instruction par instruction (utilisé par emu/rdna2_hlsl.py).

Chaque ligne du wave32 devient un thread d'un groupe de 32. Registres : `s[128]` (SGPR, VCC
en s[106], EXEC en s[126]), `v[n]` (VGPR du thread), `scc`. Les instructions vectorielles ne
s'appliquent que si le bit de la ligne est posé dans EXEC (`active`). Les masques (v_cmp)
sont construits pour tout le groupe par Ballot() ; la sémantique suit l'interpréteur de
référence emu/rdna2_exec*, contre lequel la traduction est vérifiée.
"""
import re

from emu.rdna2_exec_ops import float_bits, signed

NULL, VCC, EXEC, OFF = 125, 106, 126, 0x7D
INLINE_FLOATS = {240: 0.5, 241: -0.5, 242: 1.0, 243: -1.0, 244: 2.0, 245: -2.0, 246: 4.0, 247: -4.0,
                 248: 0.15915494309189535}


class Untranslatable(NotImplementedError):
    """Instruction que le recompilateur ne sait pas encore traduire en HLSL."""


HELPERS = """uint MulHiU32(uint a, uint b) {
  uint a0 = a & 0xFFFFu, a1 = a >> 16, b0 = b & 0xFFFFu, b1 = b >> 16;
  uint p00 = a0 * b0, p01 = a0 * b1, p10 = a1 * b0, p11 = a1 * b1;
  uint mid = (p00 >> 16) + (p01 & 0xFFFFu) + (p10 & 0xFFFFu);
  return p11 + (p01 >> 16) + (p10 >> 16) + (mid >> 16);
}
uint MulHiI32(uint a, uint b) {
  return MulHiU32(a, b) - (asint(a) < 0 ? b : 0u) - (asint(b) < 0 ? a : 0u);
}
uint BfeI32(uint v, uint off, uint w) {
  w &= 31u;
  if (w == 0u) return 0u;
  uint field = (v >> (off & 31u)) & ((1u << w) - 1u);
  uint shift = 32u - w;
  return asuint((asint(field) << shift) >> shift);
}
uint AlignBit(uint hi, uint lo, uint s) {
  s &= 31u;
  return s == 0u ? lo : ((hi << (32u - s)) | (lo >> s));
}
uint SadU32(uint a, uint b, uint c) {
  return (a > b ? (a - b) : (b - a)) + c;
}
uint MulLegacyF32(uint a, uint b) {
  float x = asfloat(a), y = asfloat(b);
  return (x == 0.0f || y == 0.0f) ? 0u : asuint(x * y);
}
uint FmaLegacyF32(uint a, uint b, uint c) {
  float x = asfloat(a), y = asfloat(b);
  return (x == 0.0f || y == 0.0f) ? c : asuint(mad(x, y, asfloat(c)));
}
uint PermB32(uint a, uint b, uint c) {
  uint r = 0u;
  [unroll] for (uint i = 0u; i < 4u; ++i) {
    uint sel = (c >> (i * 8u)) & 0xFFu;
    uint bt = 0xFFu;
    if (sel < 4u) bt = (b >> (sel * 8u)) & 0xFFu;
    else if (sel < 8u) bt = (a >> ((sel - 4u) * 8u)) & 0xFFu;
    else if (sel == 8u) bt = 0u;
    else if (sel == 9u) bt = (b & 0x00008000u) != 0u ? 0xFFu : 0u;
    else if (sel == 10u) bt = (b & 0x80000000u) != 0u ? 0xFFu : 0u;
    else if (sel == 11u) bt = (a & 0x00008000u) != 0u ? 0xFFu : 0u;
    else if (sel == 12u) bt = (a & 0x80000000u) != 0u ? 0xFFu : 0u;
    r |= bt << (i * 8u);
  }
  return r;
}
"""


def hexa(value):
    return f"0x{value & 0xFFFF_FFFF:X}u"


def source(code, literal=None):
    """Expression HLSL (uint) d'un opérande source 9 bits."""
    if code >= 256:
        return f"v[{code - 256}]"
    if code == NULL:
        return "0u"
    if code < 128:
        return f"s[{code}]"
    if 128 <= code <= 192:
        return f"{code - 128}u"
    if 193 <= code <= 208:
        return hexa(192 - code)
    if code in INLINE_FLOATS:
        return hexa(float_bits(INLINE_FLOATS[code]))
    if code == 255 and literal is not None:
        return hexa(literal)
    raise Untranslatable(f"opérande {code} non traduit")


def scalar_target(code):
    return "s_null" if code == NULL else f"s[{code}]"


def f(expression):
    return f"asfloat({expression})"


# --- Scalaires : modèles avec {d} (destination), {a}, {b} (sources), {k} (immédiat) ----------
SCALAR = {
    "s_mov_b32": "{d} = {a};",
    "s_cmov_b32": "if (scc) {d} = {a};",
    "s_movk_i32": "{d} = {k};",
    "s_cmovk_i32": "if (scc) {d} = {k};",
    "s_addk_i32": "{{ uint x = {d}, y = {k}; uint r = x + y; scc = ((~(x ^ y) & (x ^ r)) >> 31) != 0; {d} = r; }}",
    "s_mulk_i32": "{d} = {d} * {k};",
    "s_cselect_b32": "{d} = scc ? {a} : {b};",
    "s_add_u32": "{{ uint x = {a}, y = {b}; uint r = x + y; scc = r < x; {d} = r; }}",
    "s_sub_u32": "{{ uint x = {a}, y = {b}; scc = x < y; {d} = x - y; }}",
    "s_addc_u32": "{{ uint x = {a}, y = {b}, k = scc ? 1u : 0u; uint r = x + y + k; scc = (r < x) || (k != 0u && r == x); {d} = r; }}",
    "s_subb_u32": "{{ uint x = {a}, y = {b}, k = scc ? 1u : 0u; scc = (x < y) || (k != 0u && x == y); {d} = x - y - k; }}",
    "s_add_i32": "{{ uint x = {a}, y = {b}; uint r = x + y; scc = ((~(x ^ y) & (x ^ r)) >> 31) != 0; {d} = r; }}",
    "s_sub_i32": "{{ uint x = {a}, y = {b}; uint r = x - y; scc = (((x ^ y) & (x ^ r)) >> 31) != 0; {d} = r; }}",
    "s_mul_i32": "{d} = {a} * {b};",
    "s_and_b32": "{{ uint r = {a} & {b}; scc = r != 0; {d} = r; }}",
    "s_or_b32": "{{ uint r = {a} | {b}; scc = r != 0; {d} = r; }}",
    "s_xor_b32": "{{ uint r = {a} ^ {b}; scc = r != 0; {d} = r; }}",
    "s_andn2_b32": "{{ uint r = {a} & ~{b}; scc = r != 0; {d} = r; }}",
    "s_orn2_b32": "{{ uint r = {a} | ~{b}; scc = r != 0; {d} = r; }}",
    "s_nand_b32": "{{ uint r = ~({a} & {b}); scc = r != 0; {d} = r; }}",
    "s_nor_b32": "{{ uint r = ~({a} | {b}); scc = r != 0; {d} = r; }}",
    "s_xnor_b32": "{{ uint r = ~({a} ^ {b}); scc = r != 0; {d} = r; }}",
    "s_lshl_b32": "{{ uint r = {a} << ({b} & 31u); scc = r != 0; {d} = r; }}",
    "s_lshr_b32": "{{ uint r = {a} >> ({b} & 31u); scc = r != 0; {d} = r; }}",
    "s_ashr_i32": "{{ uint r = asuint(asint({a}) >> ({b} & 31u)); scc = r != 0; {d} = r; }}",
    "s_bfm_b32": "{d} = ((1u << ({a} & 31u)) - 1u) << ({b} & 31u);",
    "s_min_u32": "{{ uint x = {a}, y = {b}; scc = x < y; {d} = min(x, y); }}",
    "s_max_u32": "{{ uint x = {a}, y = {b}; scc = x > y; {d} = max(x, y); }}",
    "s_min_i32": "{{ int x = asint({a}), y = asint({b}); scc = x < y; {d} = asuint(min(x, y)); }}",
    "s_max_i32": "{{ int x = asint({a}), y = asint({b}); scc = x > y; {d} = asuint(max(x, y)); }}",
    "s_not_b32": "{{ uint r = ~{a}; scc = r != 0; {d} = r; }}",
    "s_brev_b32": "{d} = reversebits({a});",
    "s_bcnt1_i32_b32": "{{ uint x = {a}; scc = x != 0u; {d} = countbits(x); }}",
    "s_ff1_i32_b32": "{d} = firstbitlow({a});",
    "s_flbit_i32_b32": "{{ uint x = {a}; {d} = x != 0u ? (31u - firstbithigh(x)) : 0xFFFFFFFFu; }}",
    "s_sext_i32_i8": "{d} = asuint((asint({a}) << 24) >> 24);",
    "s_sext_i32_i16": "{d} = asuint((asint({a}) << 16) >> 16);",
    "s_abs_i32": "{{ int x = asint({a}); scc = x != 0; {d} = asuint(x < 0 ? -x : x); }}",
    "s_bitcmp0_b32": "scc = (({a} >> ({b} & 31u)) & 1u) == 0u;",
    "s_bitcmp1_b32": "scc = (({a} >> ({b} & 31u)) & 1u) != 0u;",
    "s_and_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} & e; scc = s[126] != 0; {d} = e; }}",
    "s_or_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} | e; scc = s[126] != 0; {d} = e; }}",
    "s_xor_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} ^ e; scc = s[126] != 0; {d} = e; }}",
    "s_andn2_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} & ~e; scc = s[126] != 0; {d} = e; }}",
}
for _name in ("s_nop", "s_waitcnt", "s_waitcnt_vscnt", "s_waitcnt_vmcnt", "s_waitcnt_expcnt",
              "s_waitcnt_lgkmcnt", "s_barrier", "s_sleep", "s_setprio", "s_ttracedata",
              "s_dcache_inv", "s_gl1_inv", "buffer_gl0_inv", "buffer_gl1_inv", "s_clause",
              "s_inst_prefetch"):
    SCALAR[_name] = ""
COMPARE_OPERATORS = {"eq": "==", "lg": "!=", "ne": "!=", "neq": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<="}
for _op, _symbol in COMPARE_OPERATORS.items():
    SCALAR[f"s_cmp_{_op}_u32"] = f"scc = {{a}} {_symbol} {{b}};"
    SCALAR[f"s_cmp_{_op}_i32"] = f"scc = asint({{a}}) {_symbol} asint({{b}});"
    SCALAR[f"s_cmpk_{_op}_u32"] = f"scc = {{d}} {_symbol} {{u}};"
    SCALAR[f"s_cmpk_{_op}_i32"] = f"scc = asint({{d}}) {_symbol} asint({{k}});"

BRANCHES = {
    "s_branch": "true", "s_cbranch_scc0": "!scc", "s_cbranch_scc1": "scc",
    "s_cbranch_vccz": "s[106] == 0", "s_cbranch_vccnz": "s[106] != 0",
    "s_cbranch_execz": "s[126] == 0", "s_cbranch_execnz": "s[126] != 0",
}


def scalar_statement(name, fields, literal):
    template = SCALAR[name]
    if not template:
        return ""
    values = {"d": scalar_target(fields.get("sdst", NULL))}
    for key, field in (("a", "ssrc0"), ("b", "ssrc1")):
        if field in fields:
            values[key] = source(fields[field], literal)
    if "simm16" in fields:
        values["k"] = hexa(signed(fields["simm16"], 16))
        values["u"] = hexa(fields["simm16"])
    return template.format(**values)


# --- Vectorielles : expressions uint de {a}, {b}, {c} (sources) et {d} (destination) --------
VECTOR = {
    "v_mov_b32": "{a}",
    "v_add_f32": "asuint(asfloat({a}) + asfloat({b}))",
    "v_sub_f32": "asuint(asfloat({a}) - asfloat({b}))",
    "v_subrev_f32": "asuint(asfloat({b}) - asfloat({a}))",
    "v_mul_f32": "asuint(asfloat({a}) * asfloat({b}))",
    "v_mul_legacy_f32": "MulLegacyF32({a}, {b})",
    "v_min_f32": "asuint(min(asfloat({a}), asfloat({b})))",
    "v_max_f32": "asuint(max(asfloat({a}), asfloat({b})))",
    "v_fmac_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({d})))",
    "v_mac_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({d})))",
    "v_fma_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({c})))",
    "v_mad_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({c})))",
    "v_fma_legacy_f32": "FmaLegacyF32({a}, {b}, {c})",
    "v_fmamk_f32": "asuint(mad(asfloat({a}), asfloat({k}), asfloat({b})))",
    "v_fmaak_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({k})))",
    "v_rcp_f32": "asuint(rcp(asfloat({a})))",
    "v_rsq_f32": "asuint(rsqrt(asfloat({a})))",
    "v_sqrt_f32": "asuint(sqrt(asfloat({a})))",
    "v_exp_f32": "asuint(exp2(asfloat({a})))",
    "v_log_f32": "asuint(log2(asfloat({a})))",
    "v_sin_f32": "asuint(sin(asfloat({a}) * 6.283185307179586f))",
    "v_cos_f32": "asuint(cos(asfloat({a}) * 6.283185307179586f))",
    "v_floor_f32": "asuint(floor(asfloat({a})))",
    "v_ceil_f32": "asuint(ceil(asfloat({a})))",
    "v_trunc_f32": "asuint(trunc(asfloat({a})))",
    "v_rndne_f32": "asuint(round(asfloat({a})))",
    "v_fract_f32": "asuint(frac(asfloat({a})))",
    "v_ldexp_f32": "asuint(ldexp(asfloat({a}), (float)asint({b})))",
    "v_cvt_f32_u32": "asuint((float){a})",
    "v_cvt_f32_i32": "asuint((float)asint({a}))",
    "v_cvt_u32_f32": "(uint)max(asfloat({a}), 0.0f)",
    "v_cvt_i32_f32": "asuint((int)asfloat({a}))",
    "v_cvt_f32_ubyte0": "asuint((float)({a} & 0xFFu))",
    "v_cvt_f32_ubyte1": "asuint((float)(({a} >> 8) & 0xFFu))",
    "v_cvt_f32_ubyte2": "asuint((float)(({a} >> 16) & 0xFFu))",
    "v_cvt_f32_ubyte3": "asuint((float)(({a} >> 24) & 0xFFu))",
    "v_add_nc_u32": "({a} + {b})",
    "v_sub_nc_u32": "({a} - {b})",
    "v_subrev_nc_u32": "({b} - {a})",
    "v_and_b32": "({a} & {b})",
    "v_or_b32": "({a} | {b})",
    "v_xor_b32": "({a} ^ {b})",
    "v_xnor_b32": "(~({a} ^ {b}))",
    "v_not_b32": "(~{a})",
    "v_bfrev_b32": "reversebits({a})",
    "v_ffbl_b32": "firstbitlow({a})",
    "v_ffbh_u32": "({a} != 0u ? (31u - firstbithigh({a})) : 0xFFFFFFFFu)",
    "v_lshlrev_b32": "({b} << ({a} & 31u))",
    "v_lshrrev_b32": "({b} >> ({a} & 31u))",
    "v_ashrrev_i32": "asuint(asint({b}) >> ({a} & 31u))",
    "v_min_u32": "min({a}, {b})",
    "v_max_u32": "max({a}, {b})",
    "v_min_i32": "asuint(min(asint({a}), asint({b})))",
    "v_max_i32": "asuint(max(asint({a}), asint({b})))",
    "v_mul_u32_u24": "(({a} & 0xFFFFFFu) * ({b} & 0xFFFFFFu))",
    "v_mul_hi_u32_u24": "MulHiU32({a} & 0xFFFFFFu, {b} & 0xFFFFFFu)",
    "v_mul_i32_i24": "asuint(((asint({a}) << 8) >> 8) * ((asint({b}) << 8) >> 8))",
    "v_mul_lo_u32": "({a} * {b})",
    "v_mul_hi_u32": "MulHiU32({a}, {b})",
    "v_mul_hi_i32": "MulHiI32({a}, {b})",
    "v_mad_u32_u24": "(({a} & 0xFFFFFFu) * ({b} & 0xFFFFFFu) + {c})",
    "v_mad_i32_i24": "asuint(((asint({a}) << 8) >> 8) * ((asint({b}) << 8) >> 8) + asint({c}))",
    "v_bfe_u32": "(({a} >> ({b} & 31u)) & ((1u << ({c} & 31u)) - 1u))",
    "v_bfe_i32": "BfeI32({a}, {b}, {c})",
    "v_bfi_b32": "(({a} & {b}) | (~{a} & {c}))",
    "v_bfm_b32": "(((1u << ({a} & 31u)) - 1u) << ({b} & 31u))",
    "v_alignbit_b32": "AlignBit({a}, {b}, {c})",
    "v_alignbyte_b32": "AlignBit({a}, {b}, ({c} & 3u) * 8u)",
    "v_perm_b32": "PermB32({a}, {b}, {c})",
    "v_add3_u32": "({a} + {b} + {c})",
    "v_lshl_add_u32": "(({a} << ({b} & 31u)) + {c})",
    "v_add_lshl_u32": "(({a} + {b}) << ({c} & 31u))",
    "v_lshl_or_b32": "(({a} << ({b} & 31u)) | {c})",
    "v_and_or_b32": "(({a} & {b}) | {c})",
    "v_or3_b32": "({a} | {b} | {c})",
    "v_xor3_b32": "({a} ^ {b} ^ {c})",
    "v_xad_u32": "(({a} ^ {b}) + {c})",
    "v_sad_u32": "SadU32({a}, {b}, {c})",
    "v_min3_f32": "asuint(min(min(asfloat({a}), asfloat({b})), asfloat({c})))",
    "v_max3_f32": "asuint(max(max(asfloat({a}), asfloat({b})), asfloat({c})))",
    "v_med3_f32": "asuint(max(min(asfloat({a}), asfloat({b})), min(max(asfloat({a}), asfloat({b})), asfloat({c}))))",
    "v_min3_u32": "min(min({a}, {b}), {c})",
    "v_max3_u32": "max(max({a}, {b}), {c})",
    "v_med3_u32": "max(min({a}, {b}), min(max({a}, {b}), {c}))",
    "v_min3_i32": "asuint(min(min(asint({a}), asint({b})), asint({c})))",
    "v_max3_i32": "asuint(max(max(asint({a}), asint({b})), asint({c})))",
    "v_med3_i32": "asuint(max(min(asint({a}), asint({b})), min(max(asint({a}), asint({b})), asint({c}))))",
    "v_bcnt_u32_b32": "(countbits({a}) + {b})",
    "v_mbcnt_lo_u32_b32": "(countbits({a} & ((1u << lane) - 1u)) + {b})",
    "v_mbcnt_hi_u32_b32": "{b}",
    "v_cndmask_b32": "((({c} >> lane) & 1u) != 0 ? {b} : {a})",
}
COMPARE = re.compile(r"^v_cmp(x?)_(f|lt|eq|le|gt|lg|ge|ne|neq|t|tru)_(f32|u32|i32)$")
CONSTANT_TESTS = {"f": "false", "t": "true", "tru": "true"}


def compare_condition(name, a, b):
    found = COMPARE.match(name)
    operation, kind = found.group(2), found.group(3)
    if operation in CONSTANT_TESTS:
        return CONSTANT_TESTS[operation]
    cast = {"f32": "asfloat", "u32": "", "i32": "asint"}[kind]
    symbol = COMPARE_OPERATORS[operation]
    if operation == "lg" and kind == "f32":            # ordonné et différent
        return f"({cast}({a}) < {cast}({b}) || {cast}({a}) > {cast}({b}))"
    return f"{cast}({a}) {symbol} {cast}({b})"


def is_compare(name):
    return bool(COMPARE.match(name))
