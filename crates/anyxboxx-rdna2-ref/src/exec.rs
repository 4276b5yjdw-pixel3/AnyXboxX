//! Running a program: one instruction at a time, until s_endpgm or the end of the binary (port of
//! `step` and `run` of `emu/rdna2_exec.py`).
//!
//! Families are added in order: scalar (SOP1, SOP2, SOPC, SOPK, SOPP) and branches first. The other
//! families refuse with `Untranslated`, which names the instruction, as the Python does for the
//! instructions it has not written.

use crate::decode::{Classified, DWORD, classify, mnemonic};
use crate::error::Error;
use crate::scalar;
use crate::wave::{MAX_STEPS, Wave};

/// The families this module executes.
const SCALAR_FAMILIES: [&str; 5] = ["SOP1", "SOP2", "SOPC", "SOPK", "SOPP"];

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
    if !SCALAR_FAMILIES.contains(&family) {
        return Err(refused());
    }
    if wave.pc + size * DWORD > data.len() {
        return Err(Error::Operand(format!(
            "instruction tronquée à l'octet {}",
            wave.pc
        )));
    }
    wave.steps += 1;
    let word = word_at(data, wave.pc);
    let literal = (size > 1).then(|| word_at(data, wave.pc + DWORD));
    let fields = scalar::fields(word);
    let next_pc = wave.pc + size * DWORD;
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
        let data = program(&[0x3F << 25]); // a VOP1 the model does not execute yet
        let mut wave = Wave::new(32).unwrap();
        match run(&data, &mut wave) {
            Err(Error::Untranslated(message)) => assert!(message.contains("VOP1"), "{message}"),
            other => panic!("expected untranslated, got {other:?}"),
        }
    }
}
