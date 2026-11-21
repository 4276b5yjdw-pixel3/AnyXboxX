# Composants tiers

AnyXboxX est distribué sous [GNU LGPL 2.1 ou ultérieure](LICENSE). Les composants suivants gardent leur propre licence.

| Composant | Origine | Licence | Utilisation dans AnyXboxX |
| --- | --- | --- | --- |
| Module `Task` de libHttpClient | [microsoft/libHttpClient](https://github.com/microsoft/libHttpClient) | MIT | File de tâches du runtime GDK (`runtime/third_party/libhttpclient-task`) |
| Tests d'encodage AMDGPU de LLVM | [llvm/llvm-project](https://github.com/llvm/llvm-project), `llvm/test/MC/AMDGPU` | Apache 2.0 avec exception LLVM | Tables générées `PrototypeScarlett/emu/rdna2_ops.py` et `rdna2_shapes.py` (outils `tools/rdna2_*.py`) |
| `AMDGPUInstPrinter::printSwizzle` et constantes `Swizzle` (`SIDefines.h`) de LLVM | [llvm/llvm-project](https://github.com/llvm/llvm-project), `llvm/lib/Target/AMDGPU` | Apache 2.0 avec exception LLVM | Port en Python : `PrototypeScarlett/emu/rdna2_swizzle.py` (offset de `ds_swizzle_b32`) |
| TomBox | [drycheetah84/TomBox](https://github.com/drycheetah84/TomBox) | voir le dépôt | Projet d'origine de la suite ci-dessous |
| Suite de TomBox (DLL console en Rust, `tombox-xshader`) | [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator) | MIT ou Apache-2.0 (AnyXboxX l'utilise sous MIT) | Code et observations sur Direct3D 12.x, les bibliothèques console et les shaders RDNA 2 ; voir [docs/recherche/tombox.md](docs/recherche/tombox.md) |
| Xbox2Windows | [R0Y00/Xbox2Windows](https://github.com/R0Y00/Xbox2Windows) | MIT | Décodage BC7 et agencement GFX10 SW_4K_S portés en Rust (`rust/anyxboxx-texture`) ; voir [docs/recherche/xbox2windows.md](docs/recherche/xbox2windows.md) |
| Décodeur XMA2 / WMA Pro `xma` de TomBox, portage Rust de FFmpeg `libavcodec/wmaprodec.c` | [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator), [FFmpeg](https://ffmpeg.org) | LGPL-2.1 ou ultérieure | `rust/anyxboxx-audio` (son console) ; avis d'origine dans `third_party/tombox/crates/compat/xma/NOTICE` |

Aucun fichier de jeu, de console ou de SDK n'est inclus dans le dépôt.
