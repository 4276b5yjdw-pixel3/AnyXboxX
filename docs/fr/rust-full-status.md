# État de la branche `rust/full`

Version anglaise : [../rust-full-status.md](../rust-full-status.md). Plan : [architecture-rust.md](architecture-rust.md).

## La tester en local (Windows)

```powershell
git fetch origin
git checkout rust/full
git submodule update --init
cargo build --release --workspace

# Ligne de commande (a remplacé tools\lancer_victory.ps1 : mêmes options, même environnement) :
.\target\release\anyxboxx.exe run --game-dir "C:\Users\ANAKIN\Downloads\GTA6.Xbox.v1.0.2.1-CYBERLEEK" --xg-dll "C:\Users\ANAKIN\Downloads\GTA6.Xbox.v1.0.2.1-CYBERLEEK\dll\xg_xs.dll" --precompile

# Lanceur graphique (double-clic sur target\release\anyxboxx-launcher.exe, ou) :
.\target\release\anyxboxx-launcher.exe
```

- `anyxboxx run` compile d'abord VIctory (`cargo build --profile diag -p victory --features diagnostics`), comme le script : le premier lancement prend plusieurs minutes. `--precompile` remplit le cache de shaders avant le jeu (environ 4,5 minutes la première fois, mesuré le 25/11/2026). Le premier lancement à froid peut planter pendant la compilation des pipelines ; relancer une fois le cache rempli.
- Les noms d'options PowerShell sont acceptés aussi (`--GameDir`, `--XgDll`, `--XgMode`, `--Precompile`, `--Dred`, `--NoTunedSettings`, `--SkipPipelines`, `--BatchCardRehash`). `anyxboxx run --help` les liste.
- Un seul jeu à la fois : fermer d'abord un jeu déjà lancé. Le lanceur graphique le vérifie lui-même.

### Lanceur graphique (`crates/anyxboxx-launcher`)

Il est fait avec egui via eframe 0.34 : du Rust pur, sans liaison C++ ni installeur. La fenêtre compte quatre pages avec des barres de progression, un journal et quelques boîtes de dialogue, qu'egui (mode immédiat) dessine en quelques centaines de lignes. Le Win32 brut aurait demandé des boucles de messages et une mise en page écrites à la main pour les mêmes pages. La logique vit dans des modules simples que la fenêtre ne fait qu'appeler : les 80 tests n'ouvrent jamais de fenêtre.

| Page | Ce qu'elle fait | Limites |
| --- | --- | --- |
| Installation | Vérifie la chaîne Rust, `d3d12.dll`, le runtime VC++ (présent, version non vérifiée), `dxc` du SDK Windows et le GPU via DXGI. Liens vers les pages officielles seulement ; rien n'est téléchargé. | La version du pilote affiche « inconnue » : le dépôt ne fixe encore aucun minimum. |
| Fichiers | Dossier du jeu (chemin saisi) : présence, fichiers vides, bornes des sections PE (exe ou DLL tronqué), bornes de la table d'en-tête RPF7, et un manifeste SHA-256 des fichiers requis et des `.rpf` de premier niveau, calculé en local. Rien n'est copié ni envoyé. | Il n'y a pas de hachés de référence : le manifeste est un relevé, pas une preuve. Une archive coupée après des tables intactes n'est pas détectée. La disposition RPF7 n'a pas été vérifiée sur un vrai fichier. |
| Shaders | `victory translate --cache --pipelines --used-pipelines … --jobs N` sur `shaders.rpf`, l'exe et ses deux DLL seulement, avec l'environnement du jeu (la clé du cache en dépend). La progression est lue dans les lignes « N of M containers (x%) » de VIctory. Refusé pendant que `victory.exe` ou le jeu tourne. | |
| Jouer | Profil choisi selon le système et le GPU (`profiles.toml`), surcharges dans le panneau avancé, `xg_xs.dll` facultative (real ou compare), compilation puis lancement par les mêmes étapes qu'`anyxboxx run`, emplacement des sauvegardes, nettoyage du cache de shaders (demande confirmation ; seul un dossier nommé `cache` peut être supprimé). | VIctory n'écrit les i/s que dans le titre de sa fenêtre : pas de ligne d'i/s à afficher. Le chemin des sauvegardes affiché est le dossier de données de VIctory, pas le sous-dossier du titre. |

Profils (`crates/anyxboxx-launcher/profiles.toml`, un test chacun) :

- **Windows + NVIDIA :** ton jeu de réglages (les six valeurs `TUNED` d'`anyxboxx run`, sans DRED, sans relais). Mesuré : 2-3 i/s sur `main` après la PR #199, 5-7 i/s sur le fork à `80d58f8`. Mettre les interrupteurs de la PR #199 à `0` n'a pas changé le chiffre de `main` : le profil les laisse aux valeurs par défaut de VIctory.
- **Linux (Proton) + AMD :** les valeurs de l'essai de la PR #199 (RX 9070 XT, RADV, GE-Proton11-12) :
  - `SHADER_LOOP_LIMIT=256`, `LATE_WAIT=0`, `WIDE_BACK=0`, `PIPELINE_WAIT_MS=50`
  - `TEXTURE_BUDGET_MB=8192` (pour une carte de 16 Go), `TEXTURE_NO_WAIT=1`
  - `CARD_BUFFERS_MIN_MB=1`, `CARD_BUFFERS_MB=1024`
  - `VKD3D_CONFIG=descriptor_heap`
- **Windows + AMD, Intel, autres :** valeurs par défaut de VIctory, marquées « non mesuré ».

## Composant par composant

| Composant (avant) | Maintenant sur `rust/full` | Vérification de parité | Ancien code |
| --- | --- | --- | --- |
| `tools/lancer_victory.ps1` (PowerShell) | `anyxboxx run` (`crates/anyxboxx`) | mêmes appels, même environnement `VICTORY_*` et mêmes codes de sortie que le script, avec un faux cargo et un faux victory.exe | **supprimé** ; `tests/test_anyxboxx_run.py` garde les attentes |
| `emu/loader.py` (chargeur PE) | `crates/anyxboxx-pe` (sur `victory-pe`) | `tests/test_rust_pe_parity.py` : 13 images, même JSON et mêmes protections de pages | gardé (le bac à sable Python s'en sert encore) |
| `--rapport` (`emu/report.py`, `config.py`) | `anyxboxx rapport` (`crates/anyxboxx-report`) | `tests/test_rust_rapport_parity.py` : même texte sur 7 cibles, mêmes refus sur 5 | gardé (utilisé par la CLI Python et les outils) |
| `--traduction` | `anyxboxx traduction` | `tests/test_rust_traduction_parity.py` : même tableau, SVG identique à l'octet sur 6 configurations | gardé |
| `--carte` | `anyxboxx carte` | `tests/test_rust_carte_parity.py` : SVG et badges identiques à l'octet sur 5 cas, plus 3 tables GDK synthétiques | gardé |
| `tools/jour_j.py` | `anyxboxx jour-j` | `tests/test_rust_jour_j_parity.py` : partie statique de `rapport.md` identique à l'octet sur 5 cas | gardé : les sections de lancement Unicorn et natif sont déclarées indisponibles en Rust (D2, D4), le portage est partiel |
| `--banc` | `anyxboxx banc` | `tests/test_rust_banc_parity.py` : colonnes Module, Imports, Résolus et pied de tableau | gardé : les colonnes chargement/initialisation demandent le bac à sable Unicorn (D2) et affichent `n/d` |
| `rust/` (textures, son, passerelle RDNA 2) | `crates/` (un seul espace) | tests existants inchangés | `rust/Cargo.toml` supprimé |
| `runtime/xcrdapi` | `crates/anyxboxx-xcrdapi` | `test_xcrdapi.py`, table d'exports identique | **supprimé** |
| `runtime/kernelx` | `crates/anyxboxx-kernelx` (2 661 redirections) | `test_kernelx.py`, table d'exports identique | **supprimé** (la table de redirections est passée dans la crate) |
| `runtime/d3d12_xs` | `crates/anyxboxx-d3d12-xs` | `test_d3d12_virtual_memory.py`, `test_runtime_cpp.py`, table d'exports identique | **supprimé** |
| `runtime/tls` (`anyxboxx_tls.dll`) | `crates/anyxboxx-tls`, cdylib `no_std` | `test_native_tls.py`, `test_native_tls_callbacks.py`, table d'exports identique | **supprimé** |
| `runtime/xmem` | `crates/anyxboxx-xmem` (attributs ERA partagés avec le module xmem de VIctory) | `test_xmem_era.py`, `test_xmem_virtual.py`, `test_runtime_cpp.py`, table d'exports identique | **supprimé** |
| `runtime/xgameruntime` | `crates/anyxboxx-xgameruntime` (file de tâches = `xasync` de VIctory) | 66 des 90 tests GDK passent contre elle | gardé : sauvegardes, boutique, plateforme (HDR, réseau), image du joueur et compteur d'images DXGI pas encore portés |
| Lanceur graphique | `crates/anyxboxx-launcher` (nouveau) | 80 tests Rust | |

Comment les DLL Rust du runtime arrivent dans le dossier du runtime : `cargo build --release` les compile, puis `runtime/CMakeLists.txt` les copie de `target/release` vers `runtime/build/bin` (`rust_dlls.cmake` ; s'il en manque une, la compilation s'arrête en donnant la commande à lancer). `cargo build --release` passe donc avant `cmake` (CI, AGENTS.md, README).

Constat sur la porteuse TLS : en cdylib `no_std`, son bloc TLS contient exactement la zone porteuse (262 208 octets, sans variables de thread de la std Rust). Le modèle du jeu la partage donc comme avec la DLL C++. `no_std` exige `panic = "abort"`, que Cargo n'accepte que pour tout le profil release : le profil release de l'espace racine interrompt donc le programme sur panique.

**Encore en C++ :**

- `runtime/xgameruntime` (24 de ses 90 tests échouent encore avec la DLL Rust).
- `runtime/launcher` (`anyxboxx.exe`) : la décision D4 le supprime, mais ses tests du mode natif n'ont pas encore d'équivalent Rust.
- `runtime/gpu_runner` : phase 4.
- `runtime/third_party/libhttpclient-task` : part avec xgameruntime.

**Encore en Python :**

- Le bac à sable Unicorn et ses fonctions HLE (abandonnés dans l'état final, D2).
- `emu/modules.py`, `emu/loader.py`, `report.py`, `status_map.py`, `translation.py`, `bench.py`, `tools/jour_j.py` : ils ont un portage Rust avec parité, mais d'autres parties Python (la CLI, la fenêtre, le bac à sable) les importent encore. Ils partiront avec le bac à sable.
- RDNA 2 (`emu/rdna2*.py`, phase 4). D'ici là, `anyxboxx traduction` lit la couverture RDNA 2 dans `crates/anyxboxx-report/data/rdna2-coverage.txt` ; un test échoue quand cette table s'écarte de la mesure Python, et `python tests/test_rust_traduction_parity.py` la régénère.
- `tools/*.py` et la suite pytest (l'oracle).

## Vérifications sur cette branche (25/11/2026, Windows 11, Rust 1.98.1, Python 3.12)

```
python -m pytest                       → 1251 passed, 11 skipped
python -m ruff check --select W605,F,E9 PrototypeScarlett tests tools → All checks passed!
cargo test --release --workspace       → 198 passed, 0 failed
cargo clippy --release --workspace --all-targets → 0 warnings
cargo fmt --check                      → propre
```

Le runtime a été compilé depuis cette branche (cargo, puis CMake). Avec `ANYXBOXX_REQUIRE_RUNTIME=1`, les tests des DLL de TomBox demandent aussi `python tools/build_tombox.py`.

## Constats en chemin

- À ce commit, VIctory ne compile pas sans sa fonctionnalité `diagnostics` (`victory_gpu::queue::presented` en dépend mais sert hors d'elle). L'espace racine dépend de `victory-hle` avec cette fonctionnalité, comme VIctory est toujours compilé.
- VIctory n'écrit les i/s que dans le titre de sa fenêtre. Une ligne d'i/s sur stdout dans VIctory permettrait aux deux lanceurs de l'afficher.
- Le test `a_read_in_place_never_meets_the_gap_of_a_remapping` de VIctory (victory-hle, xmem) est instable : il échoue environ 3 fois sur 8 sur le fichier non modifié.
- Le profil Windows+NVIDIA a été corrigé après ton essai : les interrupteurs de la PR #199 à `0` n'ont rien changé (2-3 i/s sur `main`, 5-7 i/s sur le fork à `80d58f8`).
