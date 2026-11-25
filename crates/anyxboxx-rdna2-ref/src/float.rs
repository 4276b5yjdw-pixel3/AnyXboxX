//! Single-precision values as the model holds them: bits, with arithmetic in double precision and
//! the result rounded once to single precision (`emu/rdna2_exec_ops.py`, `float_bits`).

/// IEEE 754 single-precision bits of a double. Values beyond the format are ±infinity.
pub fn float_bits(value: f64) -> u32 {
    (value as f32).to_bits()
}

/// The single-precision value of some bits.
pub fn bits_float(bits: u32) -> f64 {
    f64::from(f32::from_bits(bits))
}

/// The inline float constants of source operands 240 to 248 (the Python `INLINE_FLOATS`).
pub fn inline_constant(code: u32) -> Option<u64> {
    let value = match code {
        240 => 0.5,
        241 => -0.5,
        242 => 1.0,
        243 => -1.0,
        244 => 2.0,
        245 => -2.0,
        246 => 4.0,
        247 => -4.0,
        248 => 0.159_154_943_091_895_35,
        _ => return None,
    };
    Some(u64::from(float_bits(value)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_inline_constants_are_their_single_precision_bits() {
        assert_eq!(inline_constant(242), Some(0x3F80_0000));
        assert_eq!(inline_constant(241), Some(0xBF00_0000));
        assert_eq!(inline_constant(248), Some(0x3E22_F983));
        assert_eq!(inline_constant(249), None);
    }

    #[test]
    fn values_beyond_the_format_are_infinities() {
        assert_eq!(float_bits(1e300), 0x7F80_0000);
        assert_eq!(float_bits(-1e300), 0xFF80_0000);
        assert_eq!(bits_float(0x3F80_0000), 1.0);
    }
}
