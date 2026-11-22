# AnyXboxX — émulateur Xbox Series X (prototype)

[English](../../README.md) · **Français** · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [中文](README.zh-CN.md)

AnyXboxX charge des exécutables Xbox GDK (format PE32+ x86-64) et exécute leur code avec Unicorn. Les fonctions système de la console sont remplacées par un runtime C++ en mode natif, et par du code Python dans la machine isolée (émulation de haut niveau, comme WinDurango ou Wine). Le programme se présente comme une Xbox Series X : `XSystemGetDeviceType` renvoie `XboxScarlettAnaconda`.

Pour poursuivre l'analyse du paquet Scarlett étudié, voir le [plan de compatibilité et ses limites](../recherche/plan-compatibilite-paquet.md).

## Avancée de la traduction

![Carte de l'avancée : une case par fonction, verte si traduite](../images/carte-avancee.svg)

Régénérer : `scarlett.py --carte <dossier du paquet> docs/images/carte-avancee.svg`.

![Avancée de la traduction Xbox Series X](../images/traduction.svg)

- **Instructions processeur : 100 %.** La Series X utilise un AMD Zen 2 en x86-64, le même jeu d'instructions qu'un PC : en mode natif, le code du jeu s'exécute tel quel, sans traduction.
- **Instructions GPU : 36 %.** Les shaders d'un jeu console sont compilés pour le GPU RDNA 2 de la Series X. 521 des 1 458 encodages RDNA 2 tournent dans l'interpréteur de référence, et le recompilateur RDNA 2 → DXIL dessine déjà un premier vertex shader et pixel shader avec D3D12.
- **Fonctions système : 66 %** des 1 337 fonctions importées par les DLL du paquet de test sont résolues en mode isolé.
- **DLL propres à la console** : `xmem.dll` (4/4) et `d3d12_xs.dll` (2/2) sont traduites pour les fonctions que le paquet utilise. D3D12.X (périphérique et interfaces `ID3D12*`) est servi par la `d3d12_xs.dll` de TomBox, pas encore essayé avec un jeu.
- **Runtime GDK : 152 des 396 fonctions** sont écrites dans AnyXboxX, en C++ : la file de tâches (`XTaskQueue`, `XAsync`, `XThread`), l'utilisateur (`XUser`, un profil local hors ligne) l'identité Xbox Series X (`XSystem`, Title ID, analytique, fonctionnalités du runtime) les sauvegardes (`XGameSave`, `XGameSaveFiles`, `XPersistentLocalStorage`) et le paquet du jeu (`XPackage`). Elles servent quand AnyXboxX gère seul le runtime : sans Gaming Services, ou avec `ANYXBOXX_SYSTEM_RUNTIME=0`. Si le runtime GDK de Windows est présent, il sert toutes les interfaces, file de tâches comprise, car ses API n'acceptent que ses propres files. La trace (`ANYXBOXX_TRACE=1`) nomme chaque interface demandée.

Le graphique est régénéré par `scarlett.py --traduction <dossier du paquet> docs/images/traduction.svg`.

## Performance (objectif : 60 images par seconde constantes)

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc-perf <jeu.exe> [secondes] [courbe.svg]
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --natif <jeu.exe> --fps
```

Le runtime C++ chronomètre chaque `Present` de la swap chain DXGI du jeu, y compris quand DXGI est chargé dynamiquement par une DLL du jeu (SDL3). Il en tire les images par seconde, le temps moyen d'une image et le « 1 % bas » (cadence des 1 % d'images les plus lentes, qui révèle les saccades). `--fps` affiche ces valeurs dans le titre de la fenêtre. `--banc-perf` mesure pendant N secondes, sans compter la première (chargement), et rend un verdict « 60 i/s constants » (code de retour 2 si l'objectif est manqué). Sans ces options, rien n'est intercepté.

![SimpleTriangle : images par seconde](../images/fps-simpletriangle.svg)

![testgdk : images par seconde](../images/fps-testgdk.svg)

Les deux jeux de test tournent sans synchronisation verticale : environ 11 700 i/s pour SimpleTriangle et 12 600 i/s pour testgdk, en mode natif.

## Avancée du projet

| Étape | État |
|---|---|
| Lecture de `MicrosoftGame.Config` (TitleId, identité, exécutable Scarlett) | ✅ fait |
| Chargement PE32+ : sections et protections, relocations, imports, exports | ✅ fait |
| TLS : copie du modèle, index, callbacks | ✅ fait |
| TEB et PEB accessibles par le registre GS | ✅ fait |
| Page HLE : 158 noms de fonctions GDK, kernel, CRT et maths émulés | ✅ fait |
| Fonctions inconnues : `E_NOTIMPL` et journal au lieu d'un refus | ✅ fait |
| Constructeurs C++ globaux (`_initterm`) en code invité | ✅ fait |
| Rapport de compatibilité (`--rapport`) et banc d'essai (`--banc`) | ✅ fait |
| Plusieurs modules liés dans une même machine : DLL du paquet, ordinaux, redirections, relocation en cas de conflit | ✅ fait |
| `GetModuleHandle`, `GetProcAddress`, `LoadLibrary`, `RtlPcToFileHeader` | ✅ fait |
| 16/16 DLL d'un paquet Scarlett initialisées avec leurs dépendances, 0 appel non émulé | ✅ fait |
| Jeu de test libre `SimpleTriangle` compilé : démarrage C et initialisation GDK passent dans AnyXboxX | ✅ fait |
| Exécution native façon Wine (`--natif`) : **SimpleTriangle s'affiche**, runtime GDK servi par AnyXboxX | ✅ fait |
| Deuxième jeu de test libre, `testgdk` de SDL3 : **tourne en mode natif** (fenêtre, sprites, son) | ✅ fait |
| Lancement isolé d'un paquet ou d'un exe (`--lancer`) avec la liste des appels à émuler | ✅ fait |
| Runtime C++ (`runtime/`) : `xgameruntime.dll`, `xmem.dll`, `d3d12_xs.dll` préchargées en mode natif, servies à toutes les DLL du jeu | ✅ fait |
| `xmem.dll` : `XMemAlloc`, `XMemFree` avec `XALLOC_ATTRIBUTES` décodés (disposition ERA : mémoire tas et graphique, alignement), crochets, `XMemVirtualQuery` (drapeau de mémoire graphique) | ✅ fait |
| `d3d12_xs.dll` : sérialisation des signatures racine, redirigée vers le D3D12 du PC | ✅ fait |
| Table des 396 fonctions GDK : interface et n° de méthode, extraits de `xgameruntime.lib` (`tools/gdk_interfaces.py`) | ✅ fait |
| `XTaskQueue`, `XAsync`, `XThread` servies par AnyXboxX : testgdk tourne sans le runtime de Windows | ✅ fait |
| Autres interfaces GDK : déléguées au runtime GDK de Windows, nommées par la trace | 🟡 en cours |
| 360 tests automatisés | ✅ fait |
| D3D12.X : `D3D12XboxCreateDevice`, interfaces `ID3D12*` de la console et `DXGIXPresentArray`, servis par la `d3d12_xs.dll` en Rust de TomBox (MIT, 48 exports implémentés, compilée par `tools/build_tombox.py d3d12_xs`, chargée avec `ANYXBOXX_D3D12_XS=<chemin>`) ; pas testable ici sans exécutable console | 🟡 en cours |
| Bibliothèques console de TomBox (Rust, MIT) pour ce qui manque à AnyXboxX : `xg_xs` (agencement des textures, 23 exports) et `xmem` complet (38 exports), avec `ANYXBOXX_TOMBOX_DIR=<dossier>` ; compilées par `tools/build_tombox.py xg_xs xmem` | 🟡 en cours |
| `XUser` hors ligne : profil local toujours connecté, gamertag réglable (`ANYXBOXX_GAMERTAG`), connexion de testgdk réussie | ✅ fait |
| Identité Xbox Series X : type de console (registre `ConsoleMode` simulé, y compris dans les DLL du jeu), `XSystem`, Title ID lu dans `MicrosoftGame.config`, analytique « Xbox Series X » | ✅ fait |
| Carte d'avancée : une case par fonction (`--carte`) | ✅ fait |
| Manette (`GameInput`) et audio (`XAudio2`) : même API sur console et sur PC, liés aux DLL de Windows en mode natif | ✅ fait |
| Rapport Markdown des imports manquants par DLL et des appels non émulés (`--lancer … --md rapport.md`) | ✅ fait |
| Outil de premier lancement d'un exécutable console : inventaire, fournisseur de chaque import (paquet, AnyXboxX, TomBox, Windows, manquant), lancements isolés, lancement natif facultatif ; rapport gardé hors du dépôt : `python tools/jour_j.py <paquet> [--natif]` ([guide](../jour-j.md)) | ✅ fait |
| Compteur d'images (`--fps`) et banc de performance avec verdict « 60 i/s constants » et courbe (`--banc-perf`) | ✅ fait |
| Sauvegardes `XGameSave` (conteneurs, blobs, quota, lecture asynchrone) et stockage local persistant, sur le disque du PC (`%LOCALAPPDATA%\AnyXboxX\<TitleId>`, ou `ANYXBOXX_SAVE_DIR`) | ✅ fait |
| `XPackage` : paquet installé en local (identifiant, langue, morceaux prêts, montage sur le dossier du jeu) | ✅ fait |
| `kernelx.dll` (noyau console) : 2 661 fonctions redirigées vers `kernel32`/`kernelbase` de Windows | ✅ fait |
| TLS implicite (`thread_local`) des jeux en mode natif : DLL porteuse `anyxboxx_tls.dll`, chaque thread reçoit sa copie (256 Kio au plus) | ✅ fait |
| Lanceur natif en C++ sans Python (`runtime/build/bin/anyxboxx.exe <jeu.exe \| dossier> [--fps]`) : SimpleTriangle et testgdk à ~12 000 i/s | ✅ fait |
| Désassembleur GPU RDNA 2 : 1 458 mnémoniques et opérandes au format LLVM (scalaires, VOP1/VOP2/VOPC/VOP3/SMEM/DS/EXP/MUBUF/MTBUF/MIMG/FLAT avec modificateurs), vérifié sur 35 088 encodages publics de LLVM : `scarlett.py --rdna2 <shader.bin> [--liste]` | 🟡 en cours |
| Opérandes du désassembleur RDNA 2 identiques au texte de LLVM : scalaires et VOP1/VOPC 100 %, DS 100 %, EXP 100 %, SMEM 96,5 % (le maximum : LLVM écrit les autres encodages de deux façons) | ✅ fait |
| Premiers vertex et pixel shaders RDNA 2 dessinés avec D3D12 (`anyxboxx_gpu_run.exe --draw`) : chaque sommet et chaque pixel identiques à l'interpréteur de référence, sur le GPU et avec WARP | ✅ fait |
| Textures dans les shaders RDNA 2 recompilés : descripteurs T#/S# et `image_sample` (2D, texel le plus proche, wrap ou clamp-to-edge, 8_8_8_8_UNORM et 32_32_32_32_FLOAT), identiques à l'interpréteur de référence sur le GPU et avec WARP, pixel shader texturé compris ; disposition des descripteurs reprise de Leonida et de Mesa | ✅ fait |
| Second traducteur RDNA 2 → SPIR-V (Vulkan) : celui de Leonida (GPL-3.0), copié sans modification dans `third_party/leonida/` et alimenté par le désassembleur d'AnyXboxX, sans `llvm-mc` ; un vertex shader et un pixel shader traduits (`scarlett.py --rdna2 <shader.bin> --spirv ps`) | 🟡 en cours |
| TomBox mis à jour (D3D12.X : 194 méthodes sur 200 d'après leur décompte) et 4 bibliothèques console de plus compilées et servies depuis `ANYXBOXX_TOMBOX_DIR` : `d3d12_x` (ESRAM), `XAudio2_9` (voix XMA), `xapu`, `xgs12` ; `tools/build_tombox.py d3d12_xs xg_xs xmem d3d12_x xaudio2_9 xapu xgs12` | 🟡 en cours |
| Conversion du DXIL console en DXIL du PC (`dxil-ms-xb2` → `dxil-ms-dx`, sans repasser par HLSL) : l'outil de Xbox2Windows (MIT), copié sans modification avec son test dans `third_party/xbox2windows/` ; `python third_party/xbox2windows/tools/dxil_retarget.py <entrée> <sortie>` ou `--pe <jeu.exe>` | ✅ fait |
| Vérifications des pull requests : lint et synchronisation des 8 README (lignes, images, nombre de tests) à chaque pull request | ✅ fait |
| Textures console en Rust : décodage BC7 et désentrelacement GFX10 `SW_4K_S` portés de Xbox2Windows (MIT), empreintes de référence reproduites ; `anyxboxx_texture bc7 <blocs.bin> <l> <h> <sortie.png> [--4k-s]` | 🟡 en cours |
| Autres interfaces GDK écrites par AnyXboxX (`XStore`, `XGameUi`, `XNetworking`…) | ⏳ à faire |
| Recompilateur de shaders RDNA 2 → DXIL : premiers programmes traduits en HLSL, compilés en DXIL et exécutés sur le GPU du PC avec D3D12 (`--hlsl`, `anyxboxx_gpu_run.exe`, WARP sans GPU), mémoire identique à un interpréteur de référence wave32 qui exécute 521 encodages sur 1 458 (scalaires, VOP1/VOP2/VOPC/VOP3, mémoire : SMEM, LDS, GLOBAL, MUBUF avec bornes V#, atomiques, branchements, divergence par `exec`) ; un premier vertex shader et pixel shader (exports EXP, interpolation VINTRP) dessinés avec D3D12, identiques sommet par sommet et pixel par pixel : `scarlett.py --rdna2 <shader.bin> --executer` | 🟡 en cours |
| Cache de shaders : shaders traduits compilés une seule fois en DXIL, puis repris du disque (1,4 ms) ou de la mémoire (0,8 ms) au lieu de dxc (22 ms) ; `%LOCALAPPDATA%\AnyXboxX\shader-cache` ou `ANYXBOXX_SHADER_CACHE`, taille plafonnée | 🟡 en cours |
| Exceptions SEH x64 (`.pdata`), threads multiples | ⏳ à faire |
| Chargement dynamique d'une DLL pendant l'exécution (`LoadLibrary` + `DllMain`) | ⏳ à faire |
| Graphismes D3D12.X vers Direct3D 12 / Vulkan | ⏳ à faire |
| Son XMA2 de la console : décodé en WAV par le portage Rust du décodeur de FFmpeg fait par TomBox (LGPL, à 1 près de FFmpeg sur l'échantillon public FATE) ; `anyxboxx_xma <entrée.xma> <sortie.wav>`, fichiers à un flux | 🟡 en cours |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="La voiture tourne vers la droite" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="Rapport de compatibilité de la démo" width="380"></td>
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

Le mode natif a besoin du runtime C++. Il se compile avec Visual Studio 2022 ou 2026 (charge C++) et CMake :

```powershell
cmake -S runtime -B runtime/build -A x64
cmake --build runtime/build --config Release
```

La file de tâches reprend le module `Task` de [libHttpClient](https://github.com/microsoft/libHttpClient) (licence MIT, `runtime/third_party/libhttpclient-task`). Les DLL arrivent dans `runtime/build/bin`, ou dans le dossier indiqué par `ANYXBOXX_RUNTIME`. `ANYXBOXX_SYSTEM_RUNTIME=0` coupe la délégation au runtime GDK de Windows.

Le programme de démonstration compilé est `PrototypeScarlett/demo.pe` ; son code source est `PrototypeScarlett/demo.c`.

## Lancer un jeu en mode natif

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --natif <dossier ou fichier .exe> [dossiers de DLL…]
```

![SimpleTriangle lancé par AnyXboxX en mode natif](../images/simpletriangle-anyxboxx.png)

AnyXboxX charge l'exécutable lui-même et l'exécute directement sur le processeur, comme Wine. Le runtime Xbox (`xgameruntime.dll`) est fourni par AnyXboxX ; la fenêtre et DirectX 12 sont ceux du PC. **Attention : en mode natif, le programme n'est pas isolé.** Réservez ce mode aux programmes de confiance ; `--rapport` et `--banc` restent isolés dans Unicorn. `ANYXBOXX_TRACE=1` affiche les appels interceptés. Détails : [docs/jeu-de-test.md](../jeu-de-test.md).

## Lancer un paquet en mode isolé

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --lancer <dossier du paquet ou fichier .exe> [dossiers de DLL…]
```

Avec un dossier, AnyXboxX lit `MicrosoftGame.Config`, prend l'exécutable déclaré pour `Scarlett` et le lance dans la machine isolée (Unicorn) : le programme ne touche pas le PC. Le compte rendu donne les imports non résolus puis les appels non émulés, du plus fréquent au plus rare : c'est la liste de travail pour compléter l'émulateur. Si l'exécutable manque, le message le nomme. Avec `--md rapport.md`, le même compte rendu est écrit en Markdown, avec les imports manquants groupés par DLL.

## Analyser un programme

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

Le banc d'essai charge tous les modules PE d'un dossier et lance leur initialisation :

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Banc d'essai sur les DLL d'un paquet Scarlett](../images/banc-dll.svg)

Résultats détaillés : [docs/avancee.md](../avancee.md). Jeu de test libre comparé à son exécution native : [docs/jeu-de-test.md](../jeu-de-test.md). Un dossier de DLL supplémentaire (par exemple les DLL Visual C++) peut suivre la cible : `--rapport <cible> <dossier>`.

Le rapport liste les fonctions importées, le pourcentage déjà émulé et les fonctions manquantes. Dans l'interface, le bouton **Open an Xbox folder…** (ouvrir un dossier Xbox) lit `MicrosoftGame.Config`, affiche ce rapport puis lance le programme ; chaque appel non émulé apparaît dans le journal.

## Architecture

![Schéma des modules d'AnyXboxX](../images/architecture.svg)

| Module | Rôle |
|---|---|
| `emu/config.py` | lit le manifeste du paquet GDK |
| `emu/loader.py` | charge l'image PE et prépare imports, exports et TLS |
| `emu/machine.py` | processeur Unicorn, pile, tas, TEB/PEB, répartition des appels |
| `emu/hle/` | fonctions émulées : `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | rapport de compatibilité |
| `emu/modules.py` | charge les DLL du paquet, lie les imports, ordonne les initialisations |
| `emu/bench.py` | banc d'essai sur un dossier de modules |
| `emu/native/` | exécution native façon Wine : chargeur, imports réels, runtime GDK d'AnyXboxX |
| `scarlett.py` | interface Tkinter et ligne de commande |

Pour ajouter une fonction, décore un gestionnaire dans `emu/hle/` :

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## Recherche

- [Architecture matérielle de la Xbox Series X](../recherche/architecture-xbox-series-x.md) : CPU Zen 2, GPU RDNA 2, mémoire, Velocity Architecture, sécurité.
- [Émulateurs et couches de compatibilité existants](../recherche/etat-de-l-art.md) : WinDurango, XWine1, Xenia, outils XVD.
- [Notes de rétro-ingénierie du paquet Scarlett étudié](../recherche/paquet/README.md) (rédigées par Codex) : tables RDS5/ETPF, en-têtes RPF, organisation du paquet.
- [TomBox et sa suite](../recherche/tombox.md) : DLL console en Rust, Direct3D 12.x, traducteur de shaders RDNA 2, ce qu'AnyXboxX reprend (MIT, cité).
- [Xbox2Windows](../recherche/xbox2windows.md) : recherche sur la recompilation statique ; BC7 et agencement GFX10 repris par AnyXboxX (MIT, cité).

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Contribuer

La branche `main` est protégée : toute contribution passe par une pull request relue, et les tests doivent passer. Les bogues et les fonctions à émuler se signalent dans les issues. Les règles complètes sont dans [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Licence

AnyXboxX est distribué sous [GNU GPL 3.0 ou ultérieure](../../LICENSE). Les parties tierces gardent leur licence : le module `Task` de libHttpClient (MIT, `runtime/third_party/libhttpclient-task`) et les tables RDNA 2 générées depuis les tests d'encodage publics de LLVM (Apache 2.0 avec exception LLVM, `PrototypeScarlett/emu/rdna2_ops.py` et `rdna2_shapes.py`).

Composants tiers et crédits : [THIRD_PARTY.md](../../THIRD_PARTY.md).
