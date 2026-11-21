"""Génère PrototypeScarlett/emu/rdna2_ops.py : (famille, opcode) → mnémonique RDNA 2.

Source : les tests d'encodage publics de LLVM (llvm/test/MC/AMDGPU/gfx10_asm_*.s et
gfx1030_new.s, licence Apache 2.0 avec exception LLVM). Chaque ligne « encoding: [...] »
est passée au décodeur d'AnyXboxX ; on vérifie au passage que la longueur qu'il calcule
est celle de LLVM. Les noms de gfx1030 (RDNA 2) l'emportent sur ceux de gfx1010.

    python tools/rdna2_mnemonics.py <dossier des .s> [--verifier]
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "PrototypeScarlett"))
from emu import rdna2  # noqa: E402

OUTPUT = ROOT / "PrototypeScarlett" / "emu" / "rdna2_ops.py"
LINE = re.compile(r"^\s*(?://|;)\s*[A-Z0-9_,]*?:\s+([a-z][a-z0-9_]*)\b.*?encoding:\s*\[([^\]]*)\]")
SUFFIX = re.compile(r"_(e32|e64|sdwa|dpp|dpp8)$")
RDNA2_FILE = "gfx1030"
# Les opcodes VOP3 reprennent VOPC (0x000), VOP2 (0x100) et VOP1 (0x180).
VOP3_BASES = (("VOPC", 0x000, 0x100), ("VOP2", 0x100, 0x40), ("VOP1", 0x180, 0x80))


def read_encodings(folder):
    """(fichier, mnémonique, octets) de chaque ligne d'encodage des tests LLVM."""
    for path in sorted(Path(folder).glob("*.s")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = LINE.match(line)
            if match:
                data = bytes(int(b, 16) for b in match.group(2).split(","))
                yield path.name, SUFFIX.sub("", match.group(1)), data


def collect(folder):
    """Votes par (famille, opcode) et liste des longueurs que le décodeur calcule mal."""
    votes, preferred, wrong = defaultdict(Counter), defaultdict(Counter), []
    for name, mnemonic, data in read_encodings(folder):
        family, opcode, size = rdna2.classify(data + bytes(8))
        if size * rdna2.DWORD != len(data):
            wrong.append((mnemonic, len(data), size * rdna2.DWORD))
        base = "FLAT" if family in rdna2.FLAT_SEGMENTS.values() else family
        (preferred if name.startswith(RDNA2_FILE) else votes)[(base, opcode)][mnemonic] += 1
    return votes, preferred, wrong


def choose(votes, preferred):
    table = {}
    for key in set(votes) | set(preferred):
        source = preferred.get(key) or votes[key]
        table[key] = source.most_common(1)[0][0]
    for family, base, count in VOP3_BASES:
        for opcode in range(count):
            if (family, opcode) in table and ("VOP3", base + opcode) not in table:
                table[("VOP3", base + opcode)] = table[(family, opcode)]
    return dict(sorted(table.items()))


def render(table):
    lines = ['"""Mnémoniques RDNA 2 par (famille, opcode). Généré par tools/rdna2_mnemonics.py',
             "depuis les tests d'encodage de LLVM (Apache 2.0 avec exception LLVM). Ne pas modifier.\"\"\"",
             "", "MNEMONICS = {"]
    lines += [f'    ("{family}", 0x{opcode:03X}): "{name}",' for (family, opcode), name in table.items()]
    return "\n".join(lines + ["}", ""])


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    votes, preferred, wrong = collect(argv[0])
    total = sum(sum(c.values()) for c in votes.values()) + sum(sum(c.values()) for c in preferred.values())
    print(f"{total} encodages lus, {len(wrong)} longueurs fausses")
    for mnemonic, expected, got in wrong[:10]:
        print(f"  {mnemonic} : LLVM {expected} octets, décodeur {got}")
    if "--verifier" in argv:
        return 1 if wrong else 0
    table = choose(votes, preferred)
    OUTPUT.write_text(render(table), encoding="utf-8")
    print(f"{len(table)} mnémoniques écrits dans {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
