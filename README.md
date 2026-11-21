# AnyXboxX — émulateur Xbox Series X (prototype)

**Français** · [English](docs/i18n/README.en.md) · [Español](docs/i18n/README.es.md) · [Deutsch](docs/i18n/README.de.md) · [Italiano](docs/i18n/README.it.md) · [Português](docs/i18n/README.pt-BR.md) · [日本語](docs/i18n/README.ja.md) · [中文](docs/i18n/README.zh-CN.md)

AnyXboxX charge des exécutables Xbox GDK (format PE32+ x86-64) et exécute leur code avec Unicorn. Les fonctions système de la console sont remplacées par du code Python (émulation de haut niveau, comme WinDurango ou Wine). Le programme se présente comme une Xbox Series X : `XSystemGetDeviceType` renvoie `XboxScarlettAnaconda`.

![Démo de conduite exécutée dans AnyXboxX](docs/images/demo-conduite.png)

## Avancée du projet

| Étape | État |
|---|---|
| Lecture de `MicrosoftGame.Config` (TitleId, identité, exécutable Scarlett) | ✅ fait |
| Chargement PE32+ : sections et protections, relocations, imports, exports | ✅ fait |
| TLS : copie du modèle, index, callbacks | ✅ fait |
| TEB et PEB accessibles par le registre GS | ✅ fait |
| Page HLE : 135 noms de fonctions GDK, kernel, CRT et maths émulés | ✅ fait |
| Fonctions inconnues : `E_NOTIMPL` et journal au lieu d'un refus | ✅ fait |
| Constructeurs C++ globaux (`_initterm`) en code invité | ✅ fait |
| Rapport de compatibilité (`--rapport`) et banc d'essai (`--banc`) | ✅ fait |
| 16/16 DLL d'un paquet Scarlett du commerce initialisées (`DllMain` → `TRUE`) | ✅ fait |
| 49 tests automatisés, 82 % de couverture | ✅ fait |
| Chargement de plusieurs modules liés dans une même machine | ⏳ à faire |
| Échantillon libre `Xbox-GDK-Samples` compilé et ajouté au banc | ⏳ à faire |
| Exceptions SEH x64 (`.pdata`), threads multiples | ⏳ à faire |
| Chargement des DLL annexes du paquet | ⏳ à faire |
| Graphismes D3D12.X vers Direct3D 12 / Vulkan | ⏳ à faire |
| Audio, manette, sauvegardes `XGameSave` | ⏳ à faire |

<table>
<tr>
<td><img src="docs/images/demo-virage.png" alt="La voiture tourne vers la droite" width="380"></td>
<td><img src="docs/images/rapport-compatibilite.png" alt="Rapport de compatibilité de la démo" width="380"></td>
</tr>
<tr>
<td align="center">La démo répond aux flèches du clavier.</td>
<td align="center">Le journal affiche le rapport de compatibilité.</td>
</tr>
</table>

## Essayer la démo

Sous Windows, installe Python 3.12 64 bits avec Tcl/Tk, puis ouvre PowerShell à la racine du dépôt.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

Le programme de démonstration compilé est `PrototypeScarlett/demo.pe` ; son code source est `PrototypeScarlett/demo.c`.

## Analyser un programme

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

Le banc d'essai charge tous les modules PE d'un dossier et lance leur initialisation :

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Banc d'essai sur les DLL d'un paquet Scarlett](docs/images/banc-dll.svg)

Résultats détaillés et choix d'un jeu libre pour les tests : [docs/avancee.md](docs/avancee.md).

Le rapport liste les fonctions importées, le pourcentage déjà émulé et les fonctions manquantes. Dans l'interface, le bouton **Ouvrir un dossier Xbox…** lit `MicrosoftGame.Config`, affiche ce rapport puis lance le programme ; chaque appel non émulé apparaît dans le journal.

## Architecture

![Schéma des modules d'AnyXboxX](docs/images/architecture.svg)

| Module | Rôle |
|---|---|
| `emu/config.py` | lit le manifeste du paquet GDK |
| `emu/loader.py` | charge l'image PE et prépare imports, exports et TLS |
| `emu/machine.py` | processeur Unicorn, pile, tas, TEB/PEB, répartition des appels |
| `emu/hle/` | fonctions émulées : `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | rapport de compatibilité |
| `emu/bench.py` | banc d'essai sur un dossier de modules |
| `scarlett.py` | interface Tkinter et ligne de commande |

Pour ajouter une fonction, décore un gestionnaire dans `emu/hle/` :

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## Recherche

- [Architecture matérielle de la Xbox Series X](docs/recherche/architecture-xbox-series-x.md) : CPU Zen 2, GPU RDNA 2, mémoire, Velocity Architecture, sécurité.
- [Émulateurs et couches de compatibilité existants](docs/recherche/etat-de-l-art.md) : WinDurango, XWine1, Xenia, outils XVD.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Contribuer

La branche `main` est protégée : toute contribution passe par une pull request relue, et les tests doivent passer. Les bogues et les fonctions à émuler se signalent dans les issues. Les règles complètes sont dans [CONTRIBUTING.md](CONTRIBUTING.md).

## Limites

AnyXboxX est un prototype. Il n'exécute pas de jeux commerciaux : ils exigent le GPU de la console (D3D12.X), de nombreux services système, et sont livrés dans des conteneurs chiffrés dont les clés restent dans la console. Le projet ne contient et n'accepte aucun contenu protégé.
