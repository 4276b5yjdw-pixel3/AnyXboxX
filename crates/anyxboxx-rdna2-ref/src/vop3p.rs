//! VOP3P integer dot products (`v_dot2`, `v_dot4`, `v_dot8`, signed and unsigned): port of
//! `emu/rdna2_exec_dot.py`.
//!
//! D = S2 + Σ S0[i] × S1[i] over 32 bits, where S0 and S1 are read as 2 values of 16 bits, 4 of 8 bits or
//! 8 of 4 bits. Only the default form runs: op_sel 0, op_sel_hi all ones, no neg_lo, neg_hi or clamp. The
//! other forms are refused, naming the modifier. The other VOP3P instructions are not executed yet.

use crate::error::Error;
use crate::wave::Wave;

const MASK32: u64 = 0xFFFF_FFFF;
const VDST_MASK: u64 = 0xFF;
const SOURCE_SHIFTS: [u32; 3] = [32, 41, 50];
const SOURCE_MASK: u64 = 0x1FF;
const NEG_HI_SHIFT: u32 = 8;
const OP_SEL_SHIFT: u32 = 11;
const NEG_LO_SHIFT: u32 = 61;
const OP_SEL_HI_SHIFTS: [u32; 3] = [59, 60, 14];
const CLAMP_BIT: u32 = 15;
const THREE_BITS: u64 = 0x7;

/// The dot products of this module: element width in bits and whether the elements are signed.
pub fn operation(name: &str) -> Option<(u32, bool)> {
    match name {
        "v_dot2_i32_i16" => Some((16, true)),
        "v_dot2_u32_u16" => Some((16, false)),
        "v_dot4_i32_i8" => Some((8, true)),
        "v_dot4_u32_u8" => Some((8, false)),
        "v_dot8_i32_i4" => Some((4, true)),
        "v_dot8_u32_u4" => Some((4, false)),
        _ => None,
    }
}

/// The modifiers present outside the default form, by name (empty for the default form).
fn unsupported_modifiers(word: u64) -> Vec<&'static str> {
    let mut found = Vec::new();
    if (word >> OP_SEL_SHIFT) & THREE_BITS != 0 {
        found.push("op_sel");
    }
    if OP_SEL_HI_SHIFTS
        .iter()
        .any(|shift| (word >> shift) & 1 == 0)
    {
        found.push("op_sel_hi");
    }
    if (word >> NEG_LO_SHIFT) & THREE_BITS != 0 {
        found.push("neg_lo");
    }
    if (word >> NEG_HI_SHIFT) & THREE_BITS != 0 {
        found.push("neg_hi");
    }
    if (word >> CLAMP_BIT) & 1 != 0 {
        found.push("clamp");
    }
    found
}

/// S2 + Σ S0[i] × S1[i] modulo 2^32, with the element width and signedness of the operation.
pub fn dot(width: u32, signed: bool, a: u32, b: u32, c: u32) -> u32 {
    let mask = (1u64 << width) - 1;
    let element = |value: u32, shift: u32| -> i64 {
        let raw = (u64::from(value) >> shift) & mask;
        if signed {
            let sign = 1u64 << (width - 1);
            if raw & sign != 0 {
                raw as i64 - (1i64 << width)
            } else {
                raw as i64
            }
        } else {
            raw as i64
        }
    };
    let mut total = i64::from(c);
    for shift in (0..32).step_by(width as usize) {
        total += element(a, shift) * element(b, shift);
    }
    (total as u64 & MASK32) as u32
}

/// Executes a dot product for every active lane. `Ok(false)` when `name` is not one of them.
pub fn execute(
    wave: &mut Wave,
    name: &str,
    word: u64,
    literal: Option<u32>,
) -> Result<bool, Error> {
    let Some((width, signed)) = operation(name) else {
        return Ok(false);
    };
    let modifiers = unsupported_modifiers(word);
    if !modifiers.is_empty() {
        return Err(Error::Untranslated(format!(
            "{name} avec {} : sens non documenté pour RDNA 2",
            modifiers.join(", ")
        )));
    }
    let codes: Vec<u32> = SOURCE_SHIFTS
        .iter()
        .map(|shift| ((word >> shift) & SOURCE_MASK) as u32)
        .collect();
    let destination = (word & VDST_MASK) as usize;
    for lane in wave.active()? {
        let a = wave.read_lane(codes[0], lane, literal)?;
        let b = wave.read_lane(codes[1], lane, literal)?;
        let c = wave.read_lane(codes[2], lane, literal)?;
        wave.v[destination][lane] = dot(width, signed, a, b, c);
    }
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unsigned_and_signed_dot_products_follow_the_elements() {
        // 0x02 * 0x03 + 0x04 * 0x05 + 10 = 36 for four bytes (only the low two here: 0x0201 * 0x0403 ...).
        assert_eq!(
            dot(8, false, 0x0403_0201, 0x0605_0403, 10),
            3 + 8 + 15 + 24 + 10
        );
        // -1 * -1 for signed bytes.
        assert_eq!(dot(8, true, 0xFF, 0xFF, 0), 1);
    }

    #[test]
    fn default_form_has_no_modifier_and_op_sel_hi_must_be_set() {
        let default = 1u64 << 59 | 1u64 << 60 | 1u64 << 14;
        assert!(unsupported_modifiers(default).is_empty());
        assert_eq!(unsupported_modifiers(0), vec!["op_sel_hi"]);
    }
}
