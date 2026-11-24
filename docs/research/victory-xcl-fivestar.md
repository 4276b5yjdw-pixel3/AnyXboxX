> Français : [victory-xcl-fivestar.md](../fr/recherche/victory-xcl-fivestar.md)

# VIctory, xcl and five-star-recomp: the three neighbours tracked since 24 November

State on 24 November 2026, after the deletion of Leonida. Rule 2 of [AGENTS.md](../../AGENTS.md) applies: only export names, slots, shapes, flags/HRESULT and counts, each labelled "measured"; no addresses, bytes, strings, shader names or hashes, no logs of the game. Overview of the other neighbours: [neighbors.md](neighbors.md).

| Project | Language, licence | What it does |
| --- | --- | --- |
| [Marvisak/VIctory](https://github.com/Marvisak/VIctory) | Rust, GPL-3.0 or later | Runs the title's x86-64 code inside the process, HLE platform, RDNA 2 shaders translated to DXIL on first use |
| [ivall/xcl](https://github.com/ivall/xcl) | Rust, GPL-2.0-only | Generic Xbox Series to Windows compatibility layer, RDNA 2 shaders to HLSL to DXIL, runs wave64 programs on GPUs with 32-lane waves in two halves (their `docs/wave64-on-wave32.md`) |
| [ThatRecompDev/five-star-recomp](https://github.com/ThatRecompDev/five-star-recomp) | C# / .NET 10, GPL-3.0 or later | Formats, shader translation, offline console runtime; the `fivestar setup` preparation takes 1 hour to several hours and more than 100 GB |

Licence note: xcl is GPL-2.0-only, which is not compatible with our GPL-3.0 or later for copied code. Read its approach, do not copy its files; VIctory and five-star-recomp can be reused with credit in [THIRD_PARTY.md](../../THIRD_PARTY.md).

## Measured on our machine (2026-11-24)

Setup: i7-13700KF, RTX 4070 SUPER, Windows 11. VIctory `main` plus its pull request #89. All lines below are **measured**.

- Measured: menus, first-run screens, legal screens, the title card of mission 1 and the pause menu are reached at 30 fps. The CPU instructions specific to AMD are emulated correctly on Intel.
- Measured: without PR #89, two 16-bit render targets (DXGI formats B5G5R5A1 and B4G4R4A4) are refused by the NVIDIA driver.
- Measured: in the world, 1 to 2 frames per second, then `DXGI_ERROR_DEVICE_HUNG` about 2 minutes later; DRED places the stop on a `DispatchMesh`.
- Measured: the D3D12 debug layer counts 119 compute shaders refused because they ask for 64-lane waves (the driver maximum is 32), 117 barriers with a wrong "before" state and 74 vertex buffers still in UAV state.
- Measured: 351 programs are not yet translated by VIctory in the world. Main reasons (counts): select on an untracked mask 82, lane mask read as data 76, address in an SGPR outside a root parameter 35, structured buffer of unknown stride 31, scalar load read as data 24.

## What it means for AnyXboxX

Our issues [#68](https://github.com/LooperSalty/AnyXboxX/issues/68) (structured control flow and lane masks) and [#70](https://github.com/LooperSalty/AnyXboxX/issues/70) (wave64) are exactly these gaps: lane masks read as data and selects on untracked masks are #68; the 119 refused compute shaders are #70. We reuse instead of rewriting, following the "what to take" approach of [neighbors.md](neighbors.md): xcl's wave64-on-wave32 approach (two halves, read as a design, not copied because of the licence) and VIctory's pull requests #223 and #233 (GPL-3.0 or later, reusable with credit).
