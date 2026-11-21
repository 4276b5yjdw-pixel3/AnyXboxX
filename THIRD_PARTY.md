# Composants tiers

AnyXboxX est distribué sous [GNU LGPL 2.1 ou ultérieure](LICENSE). Les composants suivants gardent leur propre licence.

| Composant | Origine | Licence | Utilisation dans AnyXboxX |
| --- | --- | --- | --- |
| Module `Task` de libHttpClient | [microsoft/libHttpClient](https://github.com/microsoft/libHttpClient) | MIT | File de tâches du runtime GDK (`runtime/third_party/libhttpclient-task`) |
| Tests d'encodage AMDGPU de LLVM | [llvm/llvm-project](https://github.com/llvm/llvm-project), `llvm/test/MC/AMDGPU` | Apache 2.0 avec exception LLVM | Tables générées `PrototypeScarlett/emu/rdna2_ops.py` et `rdna2_shapes.py` (outils `tools/rdna2_*.py`) |
| TomBox | [drycheetah84/TomBox](https://github.com/drycheetah84/TomBox) | voir le dépôt | Projet d'origine de la suite ci-dessous |
| Suite de TomBox (DLL console en Rust, `tombox-xshader`) | [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator) | MIT ou Apache-2.0 (AnyXboxX l'utilise sous MIT) | Code et observations sur Direct3D 12.x, les bibliothèques console et les shaders RDNA 2 ; voir [docs/recherche/tombox.md](docs/recherche/tombox.md) |
| Xbox2Windows | [R0Y00/Xbox2Windows](https://github.com/R0Y00/Xbox2Windows) | MIT | Décodage BC7 et agencement GFX10 SW_4K_S portés en Rust (`rust/anyxboxx-texture`) ; voir [docs/recherche/xbox2windows.md](docs/recherche/xbox2windows.md) |

Aucun fichier de jeu, de console ou de SDK n'est inclus dans le dépôt.
