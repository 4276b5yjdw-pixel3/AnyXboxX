"""Rapport de compatibilité : quelles fonctions importées sont émulées."""
from dataclasses import dataclass
from pathlib import Path

from . import hle
from .loader import read_pe
from .modules import dll_name, is_system

MAX_LISTED = 40


@dataclass(frozen=True)
class Report:
    executable: str
    total: int
    emulated: tuple
    missing: tuple
    has_tls: bool
    relocated: bool
    provided: tuple = ()   # fonctions fournies par une DLL présente dans le paquet

    @property
    def coverage(self):
        """Part des imports résolus : émulés ou fournis par le paquet."""
        resolved = len(self.emulated) + len(self.provided)
        return 100.0 if self.total == 0 else 100.0 * resolved / self.total

    def text(self):
        lines = [
            f"Exécutable : {self.executable}",
            f"Fonctions importées : {self.total} · émulées : {len(self.emulated)}"
            f" · fournies par le paquet : {len(self.provided)} ({self.coverage:.1f} % résolues)",
            f"TLS : {'oui' if self.has_tls else 'non'} · relocalisé : "
            f"{'oui' if self.relocated else 'non'}",
        ]
        if self.missing:
            lines.append("Fonctions manquantes (renvoient E_NOTIMPL) :")
            lines += [f"  - {name}" for name in self.missing[:MAX_LISTED]]
            if len(self.missing) > MAX_LISTED:
                lines.append(f"  … et {len(self.missing) - MAX_LISTED} autres")
        return "\n".join(lines)


def _package_files(folder):
    return {p.name.lower() for p in folder.iterdir() if p.is_file()} if folder.is_dir() else set()


def analyse(path, extra_dirs=()):
    """Classe chaque import : émulé (HLE), fourni par une DLL du paquet, ou manquant.

    `extra_dirs` : dossiers de DLL supplémentaires (ex. redistribuables Visual C++).
    """
    image, _ = read_pe(path)
    files = set().union(*(_package_files(Path(d)) for d in (path.parent, *extra_dirs)))
    names = sorted({f"{i.dll}!{i.name}" for i in image.imports}, key=str.lower)
    emulated, provided, missing = [], [], []
    for name in names:
        dll, function = name.split("!", 1)
        if not is_system(dll) and dll_name(dll) in files:
            provided.append(name)
        elif hle.resolve(dll, function)[0] == "absent":
            missing.append(name)
        else:
            emulated.append(name)
    return Report(
        executable=path.name,
        total=len(names),
        emulated=tuple(emulated),
        missing=tuple(missing),
        has_tls=image.tls is not None,
        relocated=image.relocated,
        provided=tuple(provided),
    )
