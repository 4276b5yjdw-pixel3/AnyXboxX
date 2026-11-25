//! Integer atomic operations of the reference interpreter: port of `operation` in
//! `emu/rdna2_exec_atomic.py`, for the integer kinds. `integer` gives the new value from the old one,
//! the data and the compare value, masked to the width of the access (32 or 64 bits).

/// The integer kinds `integer` knows.
pub const KINDS: [&str; 13] = [
    "swap", "cmpswap", "add", "sub", "smin", "umin", "smax", "umax", "and", "or", "xor", "inc",
    "dec",
];

fn mask(width: u32) -> u64 {
    if width == 64 {
        u64::MAX
    } else {
        (1u64 << width) - 1
    }
}

/// The two's-complement value of the low `width` bits of `value`.
fn signed(value: u64, width: u32) -> i64 {
    let shift = 64 - width;
    ((value << shift) as i64) >> shift
}

/// The new value of an integer atomic of `width` bits, or `None` for a kind not in `KINDS`.
pub fn integer(kind: &str, width: u32, old: u64, data: u64, compare: u64) -> Option<u64> {
    let mask = mask(width);
    let (old, data) = (old & mask, data & mask);
    let value = match kind {
        "add" => old.wrapping_add(data),
        "sub" => old.wrapping_sub(data),
        "swap" => data,
        "and" => old & data,
        "or" => old | data,
        "xor" => old ^ data,
        "umin" => old.min(data),
        "umax" => old.max(data),
        "smin" => signed(old, width).min(signed(data, width)) as u64,
        "smax" => signed(old, width).max(signed(data, width)) as u64,
        "inc" => {
            if old >= data {
                0
            } else {
                old + 1
            }
        }
        "dec" => {
            if old == 0 || old > data {
                data
            } else {
                old - 1
            }
        }
        "cmpswap" => {
            if old == compare & mask {
                data
            } else {
                old
            }
        }
        _ => return None,
    };
    Some(value & mask)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inc_and_dec_wrap_at_the_data_value() {
        assert_eq!(integer("inc", 32, 5, 5, 0), Some(0));
        assert_eq!(integer("inc", 32, 4, 5, 0), Some(5));
        assert_eq!(integer("dec", 32, 0, 7, 0), Some(7));
        assert_eq!(integer("dec", 32, 9, 7, 0), Some(7));
        assert_eq!(integer("dec", 32, 3, 7, 0), Some(2));
    }

    #[test]
    fn signed_min_and_max_read_the_width() {
        assert_eq!(integer("smin", 32, 1, 0xFFFF_FFFF, 0), Some(0xFFFF_FFFF));
        assert_eq!(integer("smax", 32, 1, 0xFFFF_FFFF, 0), Some(1));
        assert_eq!(integer("umin", 32, 1, 0xFFFF_FFFF, 0), Some(1));
    }

    #[test]
    fn add_is_masked_to_the_width() {
        assert_eq!(integer("add", 32, 0xFFFF_FFFF, 2, 0), Some(1));
        assert_eq!(integer("sub", 64, 0, 1, 0), Some(u64::MAX));
    }

    #[test]
    fn cmpswap_stores_data_only_when_the_compare_matches() {
        assert_eq!(integer("cmpswap", 32, 7, 9, 7), Some(9));
        assert_eq!(integer("cmpswap", 32, 6, 9, 7), Some(6));
    }

    #[test]
    fn unknown_kinds_are_none() {
        assert_eq!(integer("fadd", 32, 0, 0, 0), None);
    }
}
