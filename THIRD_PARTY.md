# Composants tiers

AnyXboxX est distribué sous [GNU GPL 3.0 ou ultérieure](LICENSE). Les composants suivants gardent leur propre licence.

Jusqu'au 21 novembre 2026, AnyXboxX était sous LGPL 2.1 ou ultérieure. La clause « ou ultérieure » permet de passer à la GPL 3.0, et l'auteur du projet en était le seul contributeur. Ce passage permet de reprendre du code GPL-3.0, comme celui de Leonida. Les composants ci-dessous sont tous compatibles avec la GPL 3.0 : MIT, Apache 2.0 et LGPL 2.1 ou ultérieure.

| Composant | Origine | Licence | Utilisation dans AnyXboxX |
| --- | --- | --- | --- |
| Module `Task` de libHttpClient | [microsoft/libHttpClient](https://github.com/microsoft/libHttpClient) | MIT | File de tâches du runtime GDK (`runtime/third_party/libhttpclient-task`) |
| Tests d'encodage AMDGPU de LLVM | [llvm/llvm-project](https://github.com/llvm/llvm-project), `llvm/test/MC/AMDGPU` | Apache 2.0 avec exception LLVM | Tables générées `PrototypeScarlett/emu/rdna2_ops.py` et `rdna2_shapes.py` (outils `tools/rdna2_*.py`) |
| `AMDGPUInstPrinter::printSwizzle`, `printExpSrcN`, `printExpTgt`, `Exp::getTgtName` et constantes `Swizzle`/`Exp` (`SIDefines.h`) de LLVM | [llvm/llvm-project](https://github.com/llvm/llvm-project), `llvm/lib/Target/AMDGPU` | Apache 2.0 avec exception LLVM | Ports en Python : `PrototypeScarlett/emu/rdna2_swizzle.py` (offset de `ds_swizzle_b32`) et `rdna2_exp.py` (exports EXP) |
| TomBox | [drycheetah84/TomBox](https://github.com/drycheetah84/TomBox) | voir le dépôt | Projet d'origine de la suite ci-dessous |
| Suite de TomBox (DLL console en Rust, `tombox-xshader`) | [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator) | MIT ou Apache-2.0 (AnyXboxX l'utilise sous MIT) | Code et observations sur Direct3D 12.x, les bibliothèques console et les shaders RDNA 2 ; voir [docs/recherche/tombox.md](docs/recherche/tombox.md) |
| Xbox2Windows | [R0Y00/Xbox2Windows](https://github.com/R0Y00/Xbox2Windows) | MIT | Décodage BC7 et agencement GFX10 SW_4K_S portés en Rust (`rust/anyxboxx-texture`) ; voir [docs/recherche/xbox2windows.md](docs/recherche/xbox2windows.md) |
| Descripteurs GFX10 (T#, S#) de Leonida, `runtime/src/gfx10_descriptors.h`, et sa table `tools/gfx10_formats.json` | [ItsNotRexed/Leonida](https://github.com/ItsNotRexed/Leonida) | GPL-3.0 | Positions des champs T#/S# portées en Python (`PrototypeScarlett/emu/rdna2_image.py`) ; table des formats copiée (`PrototypeScarlett/emu/data/gfx10_formats.json`) |
| Traducteur RDNA 2 → SPIR-V de Leonida (`tools/rdna2spirv.py` et ses modules), commit `8bd0087d2d` | [ItsNotRexed/Leonida](https://github.com/ItsNotRexed/Leonida) | GPL-3.0 | Copié sans modification dans `third_party/leonida/` (voir son README), appelé par `PrototypeScarlett/emu/rdna2_spirv.py` |
| Registres de Mesa (`src/amd/registers/gfx10-rsrc.json`, `ac_descriptors.c`), source des champs de Leonida | [Mesa](https://gitlab.freedesktop.org/mesa/mesa) | MIT | Positions et valeurs des champs T#/S# (via Leonida) |
| Encodage MIMG gfx10 (`SIInstrFormats.td`, classe `MIMGe_gfx10`) de LLVM | [llvm/llvm-project](https://github.com/llvm/llvm-project) | Apache 2.0 avec exception LLVM | Champs de l'instruction `image_sample` (`rdna2_image.instruction_fields`) |
| Décodeur XMA2 / WMA Pro `xma` de TomBox, portage Rust de FFmpeg `libavcodec/wmaprodec.c` | [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator), [FFmpeg](https://ffmpeg.org) | LGPL-2.1 ou ultérieure | `rust/anyxboxx-audio` (son console) ; avis d'origine dans `third_party/tombox/crates/compat/xma/NOTICE` |

Aucun fichier de jeu, de console ou de SDK n'est inclus dans le dépôt.
