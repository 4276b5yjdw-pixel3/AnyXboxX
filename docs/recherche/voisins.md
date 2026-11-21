# Projets voisins : où ils sont en avance et comment les rattraper

État au 21 novembre 2026. AnyXboxX est en GPL-3.0 ou ultérieure : le code des trois projets peut
être repris avec crédit dans [THIRD_PARTY.md](../../THIRD_PARTY.md). Aucun des trois ne démarre
encore un jeu commercial Series X (TomBox atteint le salon de Fortnite, d'après leurs notes).
Détails par projet : [tombox.md](tombox.md), [xbox2windows.md](xbox2windows.md).

| Projet | Licence | Taille du travail | Leur meilleure avance |
| --- | --- | --- | --- |
| [Leonida](https://github.com/ItsNotRexed/Leonida) | GPL-3.0 | traducteur RDNA 2 → SPIR-V de 6 580 lignes | shaders : toutes les familles d'un jeu, contrôle de flux structuré, descripteurs GFX10 |
| [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator) (TomBox) | MIT ou Apache 2.0 | `d3d12_xs` de 32 400 lignes (Rust) | D3D12.X (194/200 méthodes), traduction RDNA 2 → HLSL, bibliothèques console |
| [Xbox2Windows](https://github.com/R0Y00/Xbox2Windows) | MIT | environ 100 tests ctest | mémoire ERA et alias GPU, recompilation CPU, retarget DXIL, banc GPU |

## Ce qu'il faut reprendre, par ordre d'impact

| # | Domaine | Source | Ce que nous avons | Issue | Effort |
| --- | --- | --- | --- | --- | --- |
| 1 | Textures : descripteurs T#/S#, formats GFX10, `image_sample` | Leonida `runtime/src/gfx10_descriptors.h`, `tools/gfx10_formats.json` ; LLVM ; Mesa | BC7 et SW_4K_S en Rust | #21 | 15-25 h |
| 2 | D3D12.X complet (device, listes de commandes, ESRAM) | TomBox `compat/d3d12_xs`, `d3d12_x` (lien de DLL, déjà en place pour `d3d12_xs`) | sérialisation des root signatures | #18, #22 | 8-15 h |
| 3 | Mémoire ERA, alias CPU/GPU, table d'adresses titre, `XMemVirtualQuery` | Xbox2Windows `src/era_*.cpp` | `XMemAllocDefault` sans attributs | #13, #22 | 12-18 h |
| 4 | Sémantique RDNA 2 manquante (SDWA, `v_perm_b32`, f16, `v_cvt_pkrtz`, `v_mul_legacy`…) et fixtures `.asm` | Leonida `docs/design.md`, `runtime/test/shaders/` | 520/1 444 encodages exécutés | #21 | 60-100 h |
| 5 | Contrôle de flux structuré et masques de lanes (compilation dxc rapide, waves de pixels) | Leonida `tools/cfg_structure.py`, `tools/lane_masks.py` | `while` + `switch (pc)` | #68 | 12-35 h |
| 6 | Second traducteur de comparaison | TomBox `tombox-xshader` (pont Rust existant) | pont du décodeur | #21 | 10-20 h |
| 7 | Retarget du DXIL console vers le DXIL du PC, inventaire des PSO | Xbox2Windows `tools/dxil_retarget.py`, `pso_readiness.py` | aucun | #69 | 10-16 h |
| 8 | Bibliothèques console supplémentaires et audio (`xaudio2_9`, `xapu`, `opus`) | TomBox | `xg_xs`, `xmem`, `xma` liés | #26 | 9-18 h |
| 9 | Banc GPU partagé (BVH, DXR, wave64, rapport par carte) | Xbox2Windows `tools/gpu-check` | `--banc`, `anyxboxx_gpu_run.exe` | #70 | 14-20 h |
| 10 | Recompilation statique du code CPU (AOT) | Xbox2Windows `tools/cpu_*_aot.py` | exécution native et Unicorn | #71 | 25-40 h |

Le point 10 n'est utile que si l'exécution native échoue, puisque le processeur de la console a
le même jeu d'instructions que le PC.

## Ce qui n'est pas repris

Tout ce qui est propre à un jeu : formats d'archives et de ressources (RPF, AWC, TTPF, XBCH,
FSSM), noms de fichiers, hachages, inventaires de shaders, modules en ligne de jeux précis,
cas Bink et FFX de Xbox2Windows. AnyXboxX reste une plateforme générique (règle 1 d'AGENTS.md).
