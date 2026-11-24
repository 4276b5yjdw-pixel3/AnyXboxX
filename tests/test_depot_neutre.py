"""Le dépôt reste neutre : aucune mention du jeu testé dans les fichiers suivis."""
import re
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

CE_FICHIER = "tests/test_depot_neutre.py"  # contient forcément le motif

# Titre du jeu (toutes casses, y compris « gta6 » accolé à un autre mot) et nom complet.
MOTIF = re.compile(r"(?i)(?<![a-z])gta ?(vi|6)?|grand theft auto|rockstar")

# Identifiants externes que nous ne contrôlons pas (pseudonyme d'un contributeur VIctory).
EXCEPTIONS = ("@claude-GTA6",)


def _fichiers_suivis():
    sortie = subprocess.run(
        ["git", "ls-files", "-z"], cwd=RACINE, capture_output=True, check=True
    ).stdout.decode("utf-8")
    for nom in filter(None, sortie.split("\0")):
        if nom.startswith("third_party/") or nom == CE_FICHIER:
            continue
        if not (RACINE / nom).is_file():
            continue
        yield nom


def _texte(nom):
    try:
        return (RACINE / nom).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def test_aucune_mention_du_jeu():
    trouvees = []
    for nom in _fichiers_suivis():
        if MOTIF.search(nom):
            trouvees.append(f"{nom} (nom de fichier)")
        texte = _texte(nom)
        if texte is None:
            continue
        for exception in EXCEPTIONS:
            texte = texte.replace(exception, "")
        for numero, ligne in enumerate(texte.splitlines(), 1):
            if MOTIF.search(ligne):
                trouvees.append(f"{nom}:{numero}")
    assert not trouvees, "mentions du jeu à retirer : " + ", ".join(trouvees[:20])
