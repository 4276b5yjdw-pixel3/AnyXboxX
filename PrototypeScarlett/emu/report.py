"""Rapport de compatibilité : quelles fonctions importées sont émulées."""
from dataclasses import dataclass

from . import hle
from .loader import read_pe

MAX_LISTED = 40


@dataclass(frozen=True)
class Report:
    executable: str
    total: int
    emulated: tuple
    missing: tuple
    has_tls: bool
    relocated: bool

    @property
    def coverage(self):
        return 100.0 if self.total == 0 else 100.0 * len(self.emulated) / self.total

    def text(self):
        lines = [
            f"Exécutable : {self.executable}",
            f"Fonctions importées : {self.total} · émulées : {len(self.emulated)}"
            f" ({self.coverage:.1f} %)",
            f"TLS : {'oui' if self.has_tls else 'non'} · relocalisé : "
            f"{'oui' if self.relocated else 'non'}",
        ]
        if self.missing:
            lines.append("Fonctions manquantes (renvoient E_NOTIMPL) :")
            lines += [f"  - {name}" for name in self.missing[:MAX_LISTED]]
            if len(self.missing) > MAX_LISTED:
                lines.append(f"  … et {len(self.missing) - MAX_LISTED} autres")
        return "\n".join(lines)


def analyse(path):
    image, _ = read_pe(path)
    names = sorted({f"{i.dll}!{i.name}" for i in image.imports}, key=str.lower)
    emulated, missing = [], []
    for name in names:
        dll, function = name.split("!", 1)
        kind, _ = hle.resolve(dll, function)
        (missing if kind == "absent" else emulated).append(name)
    return Report(
        executable=path.name,
        total=len(names),
        emulated=tuple(emulated),
        missing=tuple(missing),
        has_tls=image.tls is not None,
        relocated=image.relocated,
    )
