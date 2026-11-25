"""Écrit les tables de crates/anyxboxx-rdna2-ref depuis les données Python de l'interpréteur de référence.

Source : PrototypeScarlett/emu/rdna2_ops.py (mnémoniques par famille et opcode, tirés des tests
d'encodage de LLVM par tools/rdna2_mnemonics.py). Sortie : crates/anyxboxx-rdna2-ref/src/mnemonics.rs,
une fonction `mnemonic(family, opcode)`. Le fichier généré n'est pas modifié à la main ; relancer
ce script après toute mise à jour de rdna2_ops.py :

    py -3.12 tools/rdna2_ref_tables.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "PrototypeScarlett"))
OUTPUT = ROOT / "crates" / "anyxboxx-rdna2-ref" / "src" / "mnemonics.rs"


def render(mnemonics):
    lines = [
        "//! Mnémoniques RDNA 2 par (famille, opcode). Généré par tools/rdna2_ref_tables.py depuis",
        "//! PrototypeScarlett/emu/rdna2_ops.py (tests d'encodage de LLVM). Ne pas modifier.",
        "",
        "/// Le nom de l'instruction de cet encodage, si les tests de LLVM le donnent.",
        "pub fn mnemonic(family: &str, opcode: u32) -> Option<&'static str> {",
        "    let name = match (family, opcode) {",
    ]
    for (family, opcode), name in sorted(mnemonics.items()):
        lines.append(f'        ("{family}", 0x{opcode:03X}) => "{name}",')
    lines += ["        _ => return None,", "    };", "    Some(name)", "}", ""]
    return "\n".join(lines)


def main():
    from emu.rdna2_ops import MNEMONICS

    OUTPUT.write_text(render(MNEMONICS), encoding="utf-8")
    print(f"{len(MNEMONICS)} mnémoniques -> {OUTPUT}")


if __name__ == "__main__":
    main()
