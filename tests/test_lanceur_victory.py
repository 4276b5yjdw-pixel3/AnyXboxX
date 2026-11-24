"""Épinglage de VIctory sur le fork fxceless/victory-gta6 et réglages par défaut du lanceur."""
import configparser
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
COMMIT_FORK = "d279e69"
REGLAGES = (
    "VICTORY_RT_MISS", "VICTORY_WAVE32_READFIRSTLANE", "VICTORY_WAVE32_CROSSLANE", "VICTORY_SKIP_BVH_BUILDER",
    "VICTORY_CAPPED_DYNAMIC", "VICTORY_SHADER_LOOP_LIMIT", "VICTORY_D3D12_DRED", "VICTORY_LATE_WAIT",
    "VICTORY_WIDE_BACK", "VICTORY_CARD_BUFFERS_MIN_MB", "VICTORY_CARD_BUFFERS_MB",
)


def _lanceur():
    return (RACINE / "tools" / "lancer_victory.ps1").read_text(encoding="utf-8")


def test_gitmodules_points_victory_to_the_fork():
    declares = configparser.ConfigParser()
    declares.read(RACINE / ".gitmodules", encoding="utf-8")
    urls = {declares[s]["path"]: declares[s]["url"] for s in declares.sections()}
    assert urls["third_party/victory"].removesuffix(".git") == "https://github.com/fxceless/victory-gta6"


def test_gitlink_is_pinned_to_the_measured_commit():
    sortie = subprocess.run(["git", "ls-files", "-s", "third_party/victory"], cwd=RACINE, capture_output=True,
                            text=True, check=False).stdout
    if not sortie:
        return                                           # arbre sans historique git : rien à vérifier
    assert sortie.split()[1].startswith(COMMIT_FORK)


def test_launcher_sets_the_tuned_settings_and_can_turn_them_off():
    texte = _lanceur()
    for nom in REGLAGES:
        assert nom in texte, nom
    assert "$NoTunedSettings" in texte and "-not $NoTunedSettings" in texte


def test_launcher_keeps_its_parameters_and_builds_with_the_diag_profile():
    texte = _lanceur()
    assert "$GameDir" in texte and "$SkipPipelines" in texte
    assert "--profile diag -p victory --features diagnostics" in texte
