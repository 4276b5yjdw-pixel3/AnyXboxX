"""Site GitHub Pages (site/index.html) : l'espace disque annoncé suit le README de Leonida."""
import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
SITE = RACINE / "site" / "index.html"
README_LEONIDA = RACINE / "third_party" / "leonida-src" / "README.md"

# Phrases du README de Leonida (« Prerequisites » et « Low disk space ») qui donnent chaque chiffre.
SOURCES = {
    "full": r"about \*\*(\d+) GB\*\* free",
    "run": r"needs about (\d+) GB",
    "assets": r"`assets` stage \(~(\d+) GB\)",
}


def chiffres_du_site(html):
    return {cle: int(gb) for cle, gb in re.findall(r'data-disk="(\w+)" data-gb="(\d+)"', html)}


def test_site_states_the_game_is_not_playable_and_links_the_dashboard():
    html = SITE.read_text(encoding="utf-8")
    assert "Not yet." in html and "game_scarlett_master.exe" in html
    assert 'href="leonida/progress.html"' in html
    assert set(chiffres_du_site(html)) == set(SOURCES)


def test_disk_space_matches_leonida_readme():
    if not README_LEONIDA.is_file():
        pytest.skip("sous-module third_party/leonida-src absent (git submodule update --init)")
    readme = README_LEONIDA.read_text(encoding="utf-8")
    attendus = {}
    for cle, motif in SOURCES.items():
        trouve = re.search(motif, readme)
        assert trouve, f"phrase introuvable dans le README de Leonida : {motif}"
        attendus[cle] = int(trouve.group(1))
    assert chiffres_du_site(SITE.read_text(encoding="utf-8")) == attendus


def test_pages_workflow_builds_leonida_dashboard_outside_the_repository():
    workflow = (RACINE / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "progress_dashboard.py --out \"$RUNNER_TEMP/leonida\"" in workflow
    assert "actions/deploy-pages" in workflow
