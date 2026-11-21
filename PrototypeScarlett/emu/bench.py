"""Banc d'essai : charge chaque module PE d'un dossier et exécute son initialisation."""
from dataclasses import dataclass

from unicorn import UcError
import pefile

from .machine import Machine
from .report import analyse

DLL_PROCESS_ATTACH = 1
PATTERNS = ("*.dll", "*.exe")
ERRORS = (ValueError, OSError, UcError, pefile.PEFormatError)


@dataclass(frozen=True)
class BenchRow:
    name: str
    imports: int
    coverage: float
    loaded: bool
    initialised: bool
    detail: str


def _initialise(machine):
    """Lance les callbacks TLS puis DllMain(base, DLL_PROCESS_ATTACH, 0)."""
    base = machine.image.base
    for callback in machine.image.tls.callbacks if machine.image.tls else ():
        machine.call(callback, base, DLL_PROCESS_ATTACH, 0)
    return machine.call(machine.image.entry, base, DLL_PROCESS_ATTACH, 0) & 0xFFFF_FFFF


def run_one(path):
    try:
        report = analyse(path)
    except ERRORS as error:
        return BenchRow(path.name, 0, 0.0, False, False, f"analyse : {error}")
    try:
        machine = Machine(path)
    except ERRORS as error:
        return BenchRow(path.name, report.total, report.coverage, False, False, str(error))
    try:
        code = _initialise(machine)
        detail = f"retour {code:#x}"
        ok = code == 1
    except ERRORS as error:
        detail, ok = str(error), False
    missing = len(machine.missing_calls)
    if missing:
        detail += f" · {missing} appel(s) non émulé(s)"
    return BenchRow(path.name, report.total, report.coverage, True, ok, detail)


def run(folder):
    paths = sorted({p for pattern in PATTERNS for p in folder.glob(pattern)},
                   key=lambda p: p.name.lower())
    return tuple(run_one(path) for path in paths if path.is_file())


def table(rows):
    lines = ["| Module | Imports | Émulés | Chargé | Init. | Détail |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.name} | {r.imports} | {r.coverage:.0f} % | "
                     f"{'oui' if r.loaded else 'non'} | {'oui' if r.initialised else 'non'} "
                     f"| {r.detail} |")
    total = sum(r.imports for r in rows)
    emulated = sum(round(r.imports * r.coverage / 100) for r in rows)
    ok = sum(r.initialised for r in rows)
    share = 100 * emulated / total if total else 0
    lines.append(f"\nInitialisation réussie : {ok}/{len(rows)} · imports émulés : "
                 f"{emulated}/{total} ({share:.0f} %)")
    return "\n".join(lines)
