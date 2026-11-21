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
    "s_movk_i32": "{d} = {k};",
    "s_cselect_b32": "{d} = scc ? {a} : {b};",
    "s_add_u32": "{{ uint x = {a}, y = {b}; uint r = x + y; scc = r < x; {d} = r; }}",
    "s_sub_u32": "{{ uint x = {a}, y = {b}; scc = x < y; {d} = x - y; }}",
    "s_add_i32": "{{ uint x = {a}, y = {b}; uint r = x + y; scc = ((~(x ^ y) & (x ^ r)) >> 31) != 0; {d} = r; }}",
    "s_sub_i32": "{{ uint x = {a}, y = {b}; uint r = x - y; scc = (((x ^ y) & (x ^ r)) >> 31) != 0; {d} = r; }}",
    "s_mul_i32": "{d} = {a} * {b};",
    "s_and_b32": "{{ uint r = {a} & {b}; scc = r != 0; {d} = r; }}",
    "s_or_b32": "{{ uint r = {a} | {b}; scc = r != 0; {d} = r; }}",
    "s_xor_b32": "{{ uint r = {a} ^ {b}; scc = r != 0; {d} = r; }}",
    "s_andn2_b32": "{{ uint r = {a} & ~{b}; scc = r != 0; {d} = r; }}",
    "s_lshl_b32": "{{ uint r = {a} << ({b} & 31u); scc = r != 0; {d} = r; }}",
    "s_lshr_b32": "{{ uint r = {a} >> ({b} & 31u); scc = r != 0; {d} = r; }}",
    "s_ashr_i32": "{{ uint r = asuint(asint({a}) >> ({b} & 31u)); scc = r != 0; {d} = r; }}",
    "s_min_u32": "{{ uint x = {a}, y = {b}; scc = x < y; {d} = min(x, y); }}",
    "s_max_u32": "{{ uint x = {a}, y = {b}; scc = x > y; {d} = max(x, y); }}",
    "s_not_b32": "{{ uint r = ~{a}; scc = r != 0; {d} = r; }}",
    "s_and_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} & e; scc = s[126] != 0; {d} = e; }}",
    "s_or_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} | e; scc = s[126] != 0; {d} = e; }}",
    "s_andn2_saveexec_b32": "{{ uint e = s[126]; s[126] = {a} & ~e; scc = s[126] != 0; {d} = e; }}",
}
for _name in ("s_nop", "s_waitcnt", "s_waitcnt_vscnt", "s_barrier", "s_dcache_inv", "s_gl1_inv",
              "buffer_gl0_inv", "buffer_gl1_inv", "s_clause", "s_inst_prefetch"):
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
    "v_min_f32": "asuint(min(asfloat({a}), asfloat({b})))",
    "v_max_f32": "asuint(max(asfloat({a}), asfloat({b})))",
    "v_fmac_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({d})))",
    "v_mac_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({d})))",
    "v_fma_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({c})))",
    "v_mad_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({c})))",
    "v_fmamk_f32": "asuint(mad(asfloat({a}), asfloat({k}), asfloat({b})))",
    "v_fmaak_f32": "asuint(mad(asfloat({a}), asfloat({b}), asfloat({k})))",
    "v_rcp_f32": "asuint(rcp(asfloat({a})))",
    "v_rsq_f32": "asuint(rsqrt(asfloat({a})))",
    "v_sqrt_f32": "asuint(sqrt(asfloat({a})))",
    "v_exp_f32": "asuint(exp2(asfloat({a})))",
    "v_log_f32": "asuint(log2(asfloat({a})))",
    "v_floor_f32": "asuint(floor(asfloat({a})))",
    "v_ceil_f32": "asuint(ceil(asfloat({a})))",
    "v_trunc_f32": "asuint(trunc(asfloat({a})))",
    "v_fract_f32": "asuint(frac(asfloat({a})))",
    "v_cvt_f32_u32": "asuint((float){a})",
    "v_cvt_f32_i32": "asuint((float)asint({a}))",
    "v_cvt_u32_f32": "(uint)max(asfloat({a}), 0.0f)",
    "v_cvt_i32_f32": "asuint((int)asfloat({a}))",
    "v_add_nc_u32": "({a} + {b})",
    "v_sub_nc_u32": "({a} - {b})",
    "v_subrev_nc_u32": "({b} - {a})",
    "v_and_b32": "({a} & {b})",
    "v_or_b32": "({a} | {b})",
    "v_xor_b32": "({a} ^ {b})",
    "v_not_b32": "(~{a})",
    "v_lshlrev_b32": "({b} << ({a} & 31u))",
    "v_lshrrev_b32": "({b} >> ({a} & 31u))",
    "v_ashrrev_i32": "asuint(asint({b}) >> ({a} & 31u))",
    "v_min_u32": "min({a}, {b})",
    "v_max_u32": "max({a}, {b})",
    "v_min_i32": "asuint(min(asint({a}), asint({b})))",
    "v_max_i32": "asuint(max(asint({a}), asint({b})))",
    "v_mul_u32_u24": "(({a} & 0xFFFFFFu) * ({b} & 0xFFFFFFu))",
    "v_mul_lo_u32": "({a} * {b})",
    "v_mad_u32_u24": "(({a} & 0xFFFFFFu) * ({b} & 0xFFFFFFu) + {c})",
    "v_bfe_u32": "(({a} >> ({b} & 31u)) & ((1u << ({c} & 31u)) - 1u))",
    "v_bfi_b32": "(({a} & {b}) | (~{a} & {c}))",
    "v_add3_u32": "({a} + {b} + {c})",
    "v_lshl_add_u32": "(({a} << ({b} & 31u)) + {c})",
    "v_lshl_or_b32": "(({a} << ({b} & 31u)) | {c})",
    "v_and_or_b32": "(({a} & {b}) | {c})",
    "v_or3_b32": "({a} | {b} | {c})",
    "v_xor3_b32": "({a} ^ {b} ^ {c})",
    "v_min3_u32": "min(min({a}, {b}), {c})",
    "v_max3_u32": "max(max({a}, {b}), {c})",
    "v_med3_i32": "asuint(max(min(asint({a}), asint({b})), min(max(asint({a}), asint({b})), asint({c}))))",
    "v_bcnt_u32_b32": "(countbits({a}) + {b})",
    "v_mbcnt_lo_u32_b32": "(countbits({a} & ((1u << lane) - 1u)) + {b})",
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
