"""Compile des DLL console de TomBox (sous-module third_party/tombox) depuis leur dépôt public.

Leur crate compat-common incorpore à la compilation des données de serveurs privés de jeux
(`backend_data/`, profils et vidéos Fortnite, routes Trackmania et XDefiant) qui ne sont pas
publiées. Ce script crée des fichiers vides à leur place, uniquement sous `backend_data/`, pour
que la compilation aboutisse ; seule l'émulation en ligne de ces jeux en dépend. Aucun fichier
de jeu n'est créé ni récupéré.

    python tools/build_tombox.py d3d12_xs [xg_xs …]
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOMBOX = ROOT / "third_party" / "tombox"
MISSING = re.compile(r"couldn't read `([^`]+)`")
MAX_ROUNDS = 5
TIMEOUT = 3600


def _cargo(crates):
    command = ["cargo", "build", "--release", *(arg for crate in crates for arg in ("-p", crate))]
    return subprocess.run(command, cwd=TOMBOX, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=TIMEOUT)


def _placeholder(raw):
    path = Path(raw)
    path = path if path.is_absolute() else (TOMBOX / path)
    resolved = path.resolve()
    if "backend_data" not in resolved.parts or TOMBOX.resolve() not in resolved.parents:
        raise RuntimeError(f"fichier manquant hors de backend_data, non créé : {raw}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.touch()
    return resolved


def build(crates):
    """Compile `crates` ; renvoie la liste des fichiers vides créés."""
    created = []
    for _ in range(MAX_ROUNDS):
        result = _cargo(crates)
        if result.returncode == 0:
            return created
        missing = MISSING.findall(result.stderr)
        if not missing:
            raise RuntimeError(f"cargo build a échoué :\n{result.stderr[-4000:]}")
        created += [_placeholder(path) for path in missing]
    raise RuntimeError("compilation toujours en échec après création des fichiers vides")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    created = build(argv)
    print(f"{len(created)} fichier(s) vide(s) créé(s) sous backend_data ; compilation réussie : {', '.join(argv)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
