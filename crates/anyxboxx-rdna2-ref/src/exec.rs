//! Running a program: one instruction at a time, until s_endpgm or the end of the binary (port of
//! `step` and `run` of `emu/rdna2_exec.py`).
//!
//! Families: scalar (SOP1, SOP2, SOPC, SOPK, SOPP) and branches, then VOP1 and VOP2 (`vector`). The other
//! families refuse with `Untranslated`, which names the instruction, as the Python does for the
//! instructions it has not written.

use crate::compare;
use crate::decode::{Classified, DWORD, classify, mnemonic};
use crate::error::Error;
use crate::ext;
use crate::scalar;
use crate::vector;
use crate::vop3;
use crate::vop3p;
use crate::wave::{MAX_STEPS, Wave};

/// The families this module executes.
const SCALAR_FAMILIES: [&str; 5] = ["SOP1", "SOP2", "SOPC", "SOPK", "SOPP"];
const VECTOR_FAMILIES: [&str; 2] = ["VOP1", "VOP2"];
/// The source codes that announce an SDWA or DPP word: refused here, executed by the Python model.
const EXTENSION_CODES: [u32; 4] = [0xE9, 0xEA, 0xF9, 0xFA];

/// Runs one VOP1 or VOP2 instruction: no-ops, the carry chain, the vector table, or the SDWA and DPP
/// forms when the source code announces an extension word (the literal slot holds that word).
fn execute_vector(
    wave: &mut Wave,
    name: &str,
    family: &str,
    word: u32,
    literal: Option<u32>,
) -> Result<bool, Error> {
    if vector::is_no_operation(name) {
        return Ok(true);
    }
    let fields = vector::fields(family, word);
    let carry = family == "VOP2" && vector::is_carry(name);
    if EXTENSION_CODES.contains(&(word & 0x1FF)) {
        if crate::wide::spec(name).is_some() || crate::movrel::is_vector(name) {
            // 64-bit operations take no extension word: refused before any lane, as the Python does.
            return Err(Error::Untranslated(format!(
                "instruction non traduite : {name} (SDWA/DPP)"
            )));
        }
        if carry {
            return Ok(false);
        }
        let ext = literal.ok_or_else(|| Error::Operand("mot d'extension absent".into()))?;
        ext::execute(wave, name, &fields, ext)?;
        return Ok(true);
    }
    if family == "VOP1" && crate::movrel::is_vector(name) {
        crate::movrel::vector(wave, name, fields.vdst, fields.src0, literal)?;
        return Ok(true);
    }
    if family == "VOP1" && crate::wide::spec(name).is_some() {
        crate::wide::execute(
            wave,
            name,
            &[fields.src0],
            fields.vdst,
            literal,
            0,
            0,
            false,
            0,
        )?;
        return Ok(true);
    }
    if carry {
        return vector::execute_carry(wave, name, &fields, literal);
    }
    vector::execute(wave, name, &fields, literal)
}

/// Branches of the Python `BRANCHES` table: the condition, read from the wave.
fn branch_taken(name: &str, wave: &Wave) -> Result<Option<bool>, Error> {
    let taken = match name {
        "s_branch" => true,
        "s_cbranch_scc0" => !wave.scc,
        "s_cbranch_scc1" => wave.scc,
        "s_cbranch_vccz" => wave.vcc()? == 0,
        "s_cbranch_vccnz" => wave.vcc()? != 0,
        "s_cbranch_execz" => wave.exec()? == 0,
        "s_cbranch_execnz" => wave.exec()? != 0,
        _ => return Ok(None),
    };
    Ok(Some(taken))
}

fn word_at(data: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes([
        data[offset],
        data[offset + 1],
        data[offset + 2],
        data[offset + 3],
    ])
}

/// Executes the instruction at `wave.pc`. `Ok(false)` after s_endpgm.
pub fn step(wave: &mut Wave, data: &[u8]) -> Result<bool, Error> {
    let Classified {
        family,
        opcode,
        size,
    } = classify(data, wave.pc);
    let name =
        mnemonic(family, opcode).map_or_else(|| format!("{family}#{opcode}"), str::to_string);
    if name == "s_endpgm" {
        return Ok(false);
    }
    let refused = || {
        Error::Untranslated(format!(
            "instruction non traduite : {name} ({family}, opcode 0x{opcode:X})"
        ))
    };
    let vector_family = VECTOR_FAMILIES.contains(&family);
    let compare_family = family == "VOPC";
    let vop3_family = family == "VOP3";
    let vop3p_family = family == "VOP3P";
    if !SCALAR_FAMILIES.contains(&family)
        && !vector_family
        && !compare_family
        && !vop3_family
        && !vop3p_family
    {
        return Err(refused());
    }
    if wave.pc + size * DWORD > data.len() {
        return Err(Error::Operand(format!(
            "instruction tronquée à l'octet {}",
            wave.pc
        )));
    }
    let word = word_at(data, wave.pc);
    wave.steps += 1;
    let literal = (size > 1).then(|| word_at(data, wave.pc + DWORD));
    let fields = scalar::fields(word);
    let next_pc = wave.pc + size * DWORD;
    if vop3_family {
        // The 64-bit word: the first word is the low half. The literal, when present, is the third word.
        let wide = u64::from(word) | u64::from(word_at(data, wave.pc + DWORD)) << 32;
        let literal3 = (size > 2).then(|| word_at(data, wave.pc + 2 * DWORD));
        if !vop3::execute(wave, &name, wide, literal3)? {
            return Err(refused());
        }
        wave.pc = next_pc;
        return Ok(true);
    }
    if vop3p_family {
        let wide = u64::from(word) | u64::from(word_at(data, wave.pc + DWORD)) << 32;
        let literal3 = (size > 2).then(|| word_at(data, wave.pc + 2 * DWORD));
        if !vop3p::execute(wave, &name, wide, literal3)? {
            return Err(refused());
        }
        wave.pc = next_pc;
        return Ok(true);
    }
    if compare_family {
        // The SDWA and DPP forms of VOPC are not modelled yet: refused, as untranslated.
        let (src0, vsrc1) = (word & 0x1FF, (word >> 9) & 0xFF);
        if EXTENSION_CODES.contains(&src0) || !compare::execute(wave, &name, src0, vsrc1, literal)?
        {
            return Err(refused());
        }
        wave.pc = next_pc;
        return Ok(true);
    }
    if vector_family {
        if !execute_vector(wave, &name, family, word, literal)? {
            return Err(refused());
        }
        wave.pc = next_pc;
        return Ok(true);
    }
    if let Some(taken) = branch_taken(&name, wave)? {
        wave.pc = if taken {
            let offset = i64::from(fields.simm16 as u16 as i16) * DWORD as i64;
            (wave.pc as i64 + DWORD as i64 + offset) as usize
        } else {
            next_pc
        };
        return Ok(true);
    }
    if !scalar::execute(wave, &name, &fields, literal)? {
        return Err(refused());
    }
    wave.pc = next_pc;
    Ok(true)
}

/// Runs a program until s_endpgm, or until its bytes end. Its state is left in `wave`.
pub fn run(data: &[u8], wave: &mut Wave) -> Result<(), Error> {
    for _ in 0..MAX_STEPS {
        if wave.pc + DWORD > data.len() || !step(wave, data)? {
            return Ok(());
        }
    }
    Err(Error::Loop(MAX_STEPS))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn program(words: &[u32]) -> Vec<u8> {
        let mut all = words.to_vec();
        all.push(0x17F << 23 | 1 << 16); // s_endpgm
        all.iter().flat_map(|word| word.to_le_bytes()).collect()
    }

    #[test]
    fn a_literal_mov_and_an_add_run_to_the_end() {
        // s_mov_b32 s0, 0x12345678 ; s_add_u32 s1, s0, 1
        let data = program(&[
            0x17D << 23 | 3 << 8 | 255,
            0x1234_5678,
            0b10 << 30 | 1 << 16,
        ]);
        let mut wave = Wave::new(32).unwrap();
        wave.s[0] = 0;
        run(&data, &mut wave).unwrap();
        assert_eq!(wave.s[0], 0x1234_5678);
        assert_eq!(wave.steps, 2);
    }

    #[test]
    fn a_branch_skips_the_instructions_it_jumps_over() {
        // s_branch +1 ; s_mov_b32 s0, 1 (skipped) ; s_mov_b32 s1, 2
        let data = program(&[
            (0x17F << 23) | (2 << 16) | 1,
            (0x17D << 23) | (3 << 8) | (128 + 1),
            (0x17D << 23) | (1 << 16) | (3 << 8) | (128 + 2),
        ]);
        let mut wave = Wave::new(32).unwrap();
        run(&data, &mut wave).unwrap();
        assert_eq!((wave.s[0], wave.s[1]), (0, 2));
    }

    #[test]
    fn an_unknown_instruction_is_named_as_untranslated() {
        let data = program(&[0x35 << 26 | 0x3FF << 16, 0]); // a VOP3 opcode no table names
        let mut wave = Wave::new(32).unwrap();
        match run(&data, &mut wave) {
            Err(Error::Untranslated(message)) => assert!(message.contains("VOP3"), "{message}"),
            other => panic!("expected untranslated, got {other:?}"),
        }
    }
}
