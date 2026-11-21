"""Avancée de la « traduction » des DLL propres à la console Xbox Series X."""
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import pefile

from .bench import PATTERNS, is_pe32_plus
from .modules import dll_name

CONSOLE_DLLS = ("xmem.dll", "d3d12_xs.dll", "kernelx.dll", "xg_xs.dll", "xgameruntime.dll")
DIRECTORY_IMPORT = pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]
DIRECTORY_EXPORT = pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]
COMPLETE = "complet"
MAX_LISTED = 4
WIDTH, MARGIN, LABEL_W, BAR_X, BAR_W = 760, 24, 270, 300, 220
HEADER_H, ROW_H = 76, 46
GREEN, ORANGE, RED, TRACK = "#107c10", "#e8890c", "#c42b1c", "#e3e6ee"


@dataclass(frozen=True)
class Area:
    """Un domaine à traduire : `done` éléments faits sur `total`."""
    name: str
    done: int
    total: int
    note: str
    counted: bool = True   # False : seule la part est affichée (domaine non dénombrable)

    @property
    def share(self):
        """Part traduite entre 0 et 1 (0 si rien à traduire)."""
        return self.done / self.total if self.total else 0.0


# Exportées par le runtime mais seulement amorcées : elles signalent un échec propre.
PARTIAL = {
    "XMemGetWorkingSetStatistics": "structure non publique",
}

CPU_AREA = Area("Instructions processeur (x86-64, Zen 2)", 1, 1,
                "même jeu d'instructions que le PC : exécutées telles quelles en mode natif",
                counted=False)
GPU_AREA = Area("Instructions GPU (RDNA 2, shaders console)", 0, 1,
                "recompilateur RDNA 2 → DXIL pas commencé", counted=False)

STATIC_AREAS = (
    Area("D3D12.X : périphérique et interfaces ID3D12*", 0, 1,
         "pas commencé : tables de méthodes console différentes du PC", counted=False),
    Area("Interfaces GDK servies par AnyXboxX", 0, 1,
         "aucune : déléguées au runtime GDK de Windows (XTaskQueue, XUser…)", counted=False),
)


def functions_area(rows):
    """Fonctions système importées par le paquet et résolues en mode isolé (banc d'essai)."""
    total = sum(r.imports for r in rows)
    done = sum(round(r.imports * r.coverage / 100) for r in rows)
    return Area("Fonctions système importées par le paquet", done, total,
                "mode isolé : émulées ou fournies par une DLL du paquet")


def _modules(folder):
    paths = {p for pattern in PATTERNS for p in Path(folder).glob(pattern)}
    return sorted((p for p in paths if p.is_file() and is_pe32_plus(p)),
                  key=lambda p: p.name.lower())


def _imported_names(path):
    """Imports du module : {dll normalisée: noms}, ordinaux écrits `#n`."""
    try:
        pe = pefile.PE(str(path), fast_load=True)
    except (OSError, pefile.PEFormatError):
        return {}
    try:
        pe.parse_data_directories(directories=[DIRECTORY_IMPORT])
        found = {}
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", ()):
            dll = dll_name(entry.dll.decode("latin-1"))
            for imp in entry.imports:
                name = imp.name.decode("latin-1") if imp.name else f"#{imp.ordinal}"
                found.setdefault(dll, set()).add(name)
        return found
    except (pefile.PEFormatError, ValueError):
        return {}
    finally:
        pe.close()


def package_imports(folder):
    """Fonctions importées par le paquet, regroupées par DLL console."""
    merged = {}
    for path in _modules(folder):
        for dll, names in _imported_names(path).items():
            if dll in CONSOLE_DLLS:
                merged[dll] = merged.get(dll, frozenset()) | frozenset(names)
    return merged


def _exported_names(path):
    try:
        pe = pefile.PE(str(path), fast_load=True)
    except (OSError, pefile.PEFormatError):
        return frozenset()
    try:
        pe.parse_data_directories(directories=[DIRECTORY_EXPORT])
        directory = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
        symbols = directory.symbols if directory else ()
        return frozenset(s.name.decode("latin-1") for s in symbols if s.name)
    except (pefile.PEFormatError, ValueError):
        return frozenset()
    finally:
        pe.close()


def runtime_exports(runtime_dir):
    """Exports nommés (redirections comprises) des DLL console présentes dans le runtime."""
    if runtime_dir is None or not Path(runtime_dir).is_dir():
        return {}
    result = {}
    for name in CONSOLE_DLLS:
        path = Path(runtime_dir) / name
        if path.is_file():
            result[name] = _exported_names(path)
    return result


def measure(package_dir, runtime_dir, extra=()):
    """Une `Area` par DLL console importée par le paquet, suivie de `extra`."""
    imports = package_imports(package_dir)
    exports = runtime_exports(runtime_dir)
    areas = []
    for dll in CONSOLE_DLLS:
        if dll not in imports:
            continue
        exported = exports.get(dll, frozenset())
        missing = sorted(imports[dll] - exported)
        partial = sorted(n for n in imports[dll] & exported if n in PARTIAL)
        remaining = missing + [f"{n} (partiel : {PARTIAL[n]})" for n in partial]
        listed = ", ".join(remaining[:MAX_LISTED]) + (", …" if len(remaining) > MAX_LISTED else "")
        areas.append(Area(dll, len(imports[dll]) - len(remaining), len(imports[dll]),
                          listed if remaining else COMPLETE))
    return (*areas, *extra)


def table(areas):
    """Tableau Markdown de l'avancée."""
    lines = ["| Domaine | Traduit | Total | Part | Reste |", "|---|---|---|---|---|"]
    lines += [f"| {a.name} | {a.done} | {a.total} | {a.share * 100:.0f} % | {a.note} |"
              for a in areas]
    return "\n".join(lines)


def _color(area):
    if area.total and area.done >= area.total:
        return GREEN
    return ORANGE if area.done else RED


def _amount(area):
    share = f"{area.share * 100:.0f} %"
    return f"{area.done}/{area.total} ({share})" if area.counted else share


def _row(area, top):
    mid = top + 14
    fill = round(BAR_W * area.share)
    return [
        f'<text x="{LABEL_W}" y="{mid}" text-anchor="end" fill="#1d2230">{escape(area.name)}</text>',
        f'<rect x="{BAR_X}" y="{top}" width="{BAR_W}" height="18" rx="3" fill="{TRACK}"/>',
        f'<rect x="{BAR_X}" y="{top}" width="{fill}" height="18" rx="3" fill="{_color(area)}"/>',
        f'<text x="{BAR_X + BAR_W + 12}" y="{mid}" fill="#1d2230">'
        f'{_amount(area)}</text>',
        f'<text x="{BAR_X}" y="{top + 34}" font-size="11" fill="#4b5263">{escape(area.note)}</text>',
    ]


def svg(areas, title):
    """Image SVG autonome de l'avancée, une barre par domaine."""
    height = HEADER_H + ROW_H * len(areas) + 12
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="13">',
            f'<rect width="{WIDTH}" height="{height}" fill="#f7f8fa"/>',
            f'<text x="{MARGIN}" y="34" font-size="18" font-weight="600" fill="#1d2230">'
            f'{escape(title)}</text>',
            f'<text x="{MARGIN}" y="56" fill="#4b5263">Part traduite pour la Xbox Series X · '
            f'vert complet, orange partiel, rouge pas commencé</text>']
    for index, area in enumerate(areas):
        body += _row(area, HEADER_H + ROW_H * index)
    return "\n".join([*body, "</svg>"])
