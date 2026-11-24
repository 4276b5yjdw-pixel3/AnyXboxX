> Français : [lancer-gta6.md](fr/lancer-gta6.md)

# Running GTA VI (Xbox Series 1.0.2.1 build) with AnyXboxX

This guide installs and starts the project, and lists everything you need to repeat our tests on the Xbox Series 1.0.2.1 build of GTA VI, up to where we are today: the first cutscene. It does not provide the game and does not explain how to get it: you bring your own copy. Never put game files in this repository or attach them to an issue.

The launch goes through [VIctory](https://github.com/Marvisak/VIctory) (Marvisak, GPL-3.0 or later), tracked here as the `third_party/victory` submodule (fork `LooperSalty/victory`, branch `anyxboxx/stable`). The script `tools/lancer_victory.ps1` builds it and starts it on your game folder.

## What you get today

Measured on 2026-11-24 on an i7-13700KF + RTX 4070 SUPER, Windows 11, with the stable integration:

- Boot, profile screen, first-run settings, legal screens, loading and the pause menu work, at 30 fps in the menus.
- The first cutscene (opening credits of mission 1) is reached.
- The 3D scene behind the credits is black.
- In the world the game runs at 0.3 to 0.6 frames per second.
- It is not playable.

The section below describes a more advanced state, measured the same afternoon on a local integration branch that is not yet what `third_party/victory` pins.

## State on 24 November (afternoon)

Measured by running our own copy of the 1.0.2.1 build under VIctory, on a local integration branch (VIctory `main` + about 40 pull requests + local fixes not yet published), i7-13700KF + RTX 4070 SUPER. Nothing here comes from reading the game's code: these are run measurements (fps, timings, counts) and the output of `victory translate` on the shaders of our own copy.

- **World reached, character controllable (observed).** The tutorial "Move / Move the camera" (L / R) is displayed. The interface is composed over a 3D image that is still black.
- **Speed in the world (measured): 0.2 fps, then 2.3 to 2.5 fps.** Causes and fixes:
  - `VICTORY_D3D12_DRED=1` cost about 2.5x (text formatting and a `VirtualQuery` per draw). Only turn it on to investigate a device removed.
  - The copy back to the title spent 66% of the submission thread in `WriteProcessMemory`, itself in `NtQueryVirtualMemory` (about 2 ms per call). A direct `NtWriteVirtualMemory` brings it from 1.5 s to 0.13 s per frame.
  - Copies no longer call `VirtualQuery` first; the texture snapshot, comparison and hashing are spread over a thread pool.
  - What remains per frame (about 410 ms): GPU about 145 ms, copy back about 73 ms, hashing 20 to 60 ms, snapshot about 50 ms.
- **Untranslated shaders in game: 456 in the morning, about 170 in the afternoon (measured by the in-game count).** On the game's corpus (26,084 programs, `victory translate`) the emitted programs are: VS/PS 13,480 of 14,038, CS 2,212, MS 8,654 of 8,765 (counts as printed by the tool). Patterns solved during the day: descriptor read as data, scalar memory read as data, buffer of unknown stride, wave prefix in divergent flow (the InstanceCulling passes), mask kept in a VGPR lane, `readfirstlane` of a uniform address (ColorDownsample). What remains is mostly lane masks: "lane mask read as data" (586 programs) and "holding lanes elsewhere" (282) on the corpus.
- **Ray tracing.** The title's BVH builder causes a TDR (GPU timeout recovery); it is skipped with `VICTORY_SKIP_BVH_BUILDER=1`. The new local diagnostic option `VICTORY_RT_MISS=1` makes every ray miss: 36 of 47 ray-tracing containers are emitted instead of 18. A Codex analysis found that `ConstructBVH4` contains a bounded polling loop (256 iterations) on a value another pass produces.
- **Final composition.** As in VIctory #841, the scene exists at 2560x1440 but the presented target stays zero.

### Useful variables

All are diagnostics: they need the `diag` build (the `diagnostics` feature). Provenance, checked in the code of the integration worktree and against VIctory `main` on 2026-11-24:

| Variable | Effect | Where it comes from |
| --- | --- | --- |
| `VICTORY_KEYS` | Scripted key presses (see below). | VIctory `main` |
| `VICTORY_SHADER_LOOP_LIMIT=32` | Translated loops stop after that many iterations (decimal or `0x` hex, at least 1). | VIctory `main` |
| `VICTORY_D3D12_DRED=1` | Device-removed data. **Warning: any value turns it on, and it slows the world by about 2.5x; use it only to investigate a device removed.** | VIctory `main` |
| `VICTORY_SHOW_TARGET=busiest` | Shows the busiest render target instead of the final image. | Open pull request #638 (`Marvisak/VIctory`), in our integration |
| `VICTORY_CAPTURE_BUSY=<draws>[,<count>]` | Captures frames busier than that many draws (2 frames by default). | Open pull request #638 |
| `VICTORY_PRODUCERS=1` | Logs a pass that reads what only dropped (untranslated or skipped) work writes, with the dropped shader. | Open pull request #638 |
| `VICTORY_CAPPED_DYNAMIC=262144` | More dynamic descriptor slots on a capped heap (NVIDIA), at the cost of the title's highest slots. | Local experiment, published only on our fork (`anyxboxx/essai`, `anyxboxx/stable`) |
| `VICTORY_SKIP_BVH_BUILDER=1` | Leaves out the shaders of the title's BVH builder. | Our fork only (`anyxboxx/essai`), not proposed upstream |
| `VICTORY_PROFILE=<ms>` | Sampling profiler of the whole process; logs the busiest call stacks every 5 s (sampling period in ms, 4 by default). | Local, not published |
| `VICTORY_RT_MISS=1` | Every ray misses (ray-tracing diagnostic, off by default). | Local, not published |

## State on 24 November (evening)

Measured by running our own copy of the 1.0.2.1 build under VIctory, on the local integration branch (VIctory `main` + pull requests + local fixes not all published), i7-13700KF + RTX 4070 SUPER. These are run measurements (fps, counts, traces) and the output of `victory translate`; nothing comes from reading the game's code.

- **Series S mode is faster (measured).** `victory run --console series-s ...` gives about 3.1 to 3.3 fps in the world, against about 2.0 to 2.4 fps in Series X mode (about +50%), with the same image symptom. The game then renders internally at 1280x720 and presents at 1920x1080. Recommended for iterating.
- **Black image diagnosis (measured).** The geometry exists in the G-buffer: the characters of the cutscene are visible in 1440p and 720p. The final colour is a uniform tint that darkens over time (exposure), with the subtitles drawn on top. Almost all deferred lighting passes are translated and bound. A per-pass trace (local option `VICTORY_INDIRECT_TRACE`, not published) shows that about 379 mesh `ExecuteIndirect` calls start with zero arguments, because the GPU passes that produce those arguments are not translated yet: the translator refuses them with "an address from a phi" and "a lane mask holding lanes elsewhere read as data". This is the current work item.
- **Translation (measured).** Untranslated shaders in game: about 130 to 170 (in-game count). On the corpus (26,084 programs, `victory translate`): VS/PS 13,780 emitted of 14,038, CS 2,212, MS 8,654 of 8,765 (counts as printed by the tool).
- **Fixes published upstream** (`Marvisak/VIctory`): #1215 (speed: direct `NtWriteVirtualMemory` write, copies without `VirtualQuery`, profiler), #1225 (`readfirstlane` of a uniform address: ColorDownsample), #1231 (uniform loop counter: light probes). Measurement comments were also added on #497, #320, #1074, #1198 and #841.
- **Community.** The project has a Discord server (link at the top of the README).

Variable added to the table above (diagnostic, `diag` build):

| Variable | Effect | Where it comes from |
| --- | --- | --- |
| `VICTORY_INDIRECT_TRACE` | Per-pass trace of `ExecuteIndirect` calls and their arguments. | Local, not published |

## Requirements

- Windows 10 or 11, x64.
- A CPU with AVX2. Intel is fine: the instructions specific to AMD are emulated.
- A Direct3D 12 GPU with shader model 6.6 and mesh shaders (NVIDIA RTX 20 series or newer, AMD RDNA 2 or newer).
- 32 GB of RAM recommended, and a large enough Windows paging file: the game commits several GiB at startup. If it does not, `crashes.log` reports Windows error 1455: close other applications or enlarge the paging file.
- Your own copy of the Xbox Series 1.0.2.1 build: a folder that contains `game_scarlett_master.exe`. Not provided, not explained here.
- Free disk space for the shader cache (it grows as you play; see the status page for the figures to plan for).

## Install

1. [Git](https://git-scm.com/).
2. Rust through [rustup](https://rustup.rs/). The exact toolchain is pinned by the submodule's `rust-toolchain.toml` and is installed automatically on the first `cargo` command.
3. Visual Studio 2022 or 2026 Build Tools with the "Desktop development with C++" workload (MSVC).
4. Windows SDK 10.0.26100 (provides `dxc`).
5. Optional: the Windows optional feature "Graphics Tools" (D3D12 debug layer, needed only for `VICTORY_D3D12_DEBUG`).
6. Python 3.12, only for the AnyXboxX test suite (see Tests).

Get the code with its submodule:

```powershell
git clone --recurse-submodules https://github.com/LooperSalty/AnyXboxX.git
cd AnyXboxX
# or, in an existing clone:
git submodule update --init third_party/victory
```

## Build

```powershell
cargo build --profile diag -p victory --features diagnostics --manifest-path third_party/victory/Cargo.toml
```

The `diag` profile is required for the scripted keys, the frame captures and the diagnostic options below. The first build downloads and compiles all dependencies, so expect several minutes. The executable is `third_party\victory\target\diag\victory.exe` (or `%CARGO_TARGET_DIR%\diag\victory.exe` if you set that variable). `tools/lancer_victory.ps1` runs this build for you when the executable is missing.

## Run

```powershell
.\tools\lancer_victory.ps1 -GameDir <game folder>
```

The script sets three variables and then runs `victory.exe run <game folder>\game_scarlett_master.exe --execute`:

| Variable | Value | Why |
| --- | --- | --- |
| `VICTORY_GAME_DIR` | your game folder | No `victory.toml` is needed. |
| `VICTORY_CAPPED_DYNAMIC` | `262144` | NVIDIA caps the descriptor heap at 1,000,000 entries. With the default dynamic range, about 720 indirect draws per frame were dropped; with 262,144 slots they are not. |
| `VICTORY_SHADER_LOOP_LIMIT` | `32` | Translated shader loops were almost endless; with a limit of 32 iterations the GPU is about 6 times faster. |

`-SkipPipelines <hash,...>` is passed to `VICTORY_SKIP_PIPELINES` (see below).

Where things are kept:

- Saves, settings and `crashes.log`: `%LOCALAPPDATA%\victory\data`.
- Derived data (shader and pipeline caches): `%LOCALAPPDATA%\victory\cache`.

Both are outside the repository on purpose. Delete the cache folder to start from a clean cache; keep the data folder if you want to keep your save.

## Getting to the first cutscene

The window caption shows the frame rate. The window must have the focus.

1. Profile screen: press Enter.
2. First-run settings: press Enter on each screen.
3. Legal notices: move down to "Next", wait for the countdown of the photosensitivity warning to end, tick the two boxes, then "Confirm".
4. Loading, then the first cutscene (opening credits).
5. Escape opens the pause menu.

Keyboard or pad. With no XInput pad connected, the keyboard acts as a pad while the title's window has focus:

| Keys | Pad |
| --- | --- |
| Enter, Backspace, X, Y | A, B, X, Y |
| Arrows | D-pad |
| W A S D / I J K L | left stick / right stick |
| Q / E, Z / C | shoulders, triggers |
| F / H | stick clicks |
| Escape | Menu |
| Tab | View |

Hold each key for a moment: the game reads its input at 30 Hz, so a very short tap can be missed. Later launches resume directly from the save.

## Scripted runs and diagnostics

These need the `diag` build.

| Variable | Effect |
| --- | --- |
| `VICTORY_KEYS=40:Enter,55:Enter,70:Enter` | Presses the keys at those seconds, with or without focus. |
| `VICTORY_CAPTURE=<folder>` and `VICTORY_CAPTURE_FRAMES=<list>` | Saves the presented frames (those frame numbers). |
| `VICTORY_SHOW_TARGET=busiest` | Shows the busiest render target instead of the final image (for example the G-buffer). |
| `VICTORY_D3D12_DRED=1` | On a GPU failure, reports the commands in flight. It slows the world by about 2.5x: turn it on only to investigate a device removed. |
| `VICTORY_D3D12_DEBUG=1` | D3D12 debug layer (Graphics Tools required). |
| `VICTORY_GPU_TIMING=1` | Times each command list and logs the slow ones. |
| `VICTORY_SKIP_PIPELINES=<hash,...>` | Omits the draws and dispatches that use the listed 16-digit shader hashes. |
| `VICTORY_LOG=<target>=debug,...` | Debug and trace output. |

To stop the game: `taskkill /F /IM victory.exe`. The `timeout` command of Git Bash does not kill the executable.

## Experimental branch

```powershell
git -C third_party/victory fetch origin anyxboxx/essai
git -C third_party/victory checkout FETCH_HEAD
```

This is the fork's `anyxboxx/essai` branch: the stable one plus root UAV support and byte and half-word LDS accesses. Start it with `VICTORY_SKIP_BVH_BUILDER=1`: the game's ray-tracing BVH builder, only half translated, blocked the GPU at the start of the cutscene. Without this option, `DXGI_ERROR_DEVICE_HUNG` is certain at that moment. When you are done, go back to the stable branch (`git -C third_party/victory checkout anyxboxx/stable`).

## Safety

- On NVIDIA, staying in the world for a long time can reset the display driver (every monitor goes black for a moment), and one tester got a blue screen (0x119). Stop the game after a few minutes in the world.
- Run one instance at a time.

## Tests

```powershell
cargo test -p victory-gpu -p victory-shader --manifest-path third_party/victory/Cargo.toml
```

AnyXboxX itself (see the Setup section of [AGENTS.md](../AGENTS.md)):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check --select W605,F,E9 PrototypeScarlett tests tools
```

## Where to report

Open an issue on [AnyXboxX](https://github.com/LooperSalty/AnyXboxX/issues) or on [VIctory](https://github.com/Marvisak/VIctory/issues) (issue #264 collects the NVIDIA GPU hangs). Describe the symptom, your GPU and driver, and the relevant lines of `crashes.log`. Never attach a game file.
