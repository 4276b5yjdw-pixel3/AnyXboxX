# State of the `rust/full` branch

French version: [fr/rust-full-status.md](fr/rust-full-status.md). Plan: [architecture-rust.md](architecture-rust.md).

## Test it locally (Windows)

```powershell
git fetch origin
git checkout rust/full
git submodule update --init
cargo build --release --workspace

# Command line (replaced tools\lancer_victory.ps1: same options, same environment):
.\target\release\anyxboxx.exe run --game-dir "C:\Users\ANAKIN\Downloads\GTA6.Xbox.v1.0.2.1-CYBERLEEK" --xg-dll "C:\Users\ANAKIN\Downloads\GTA6.Xbox.v1.0.2.1-CYBERLEEK\dll\xg_xs.dll" --precompile

# Graphical launcher (double-click target\release\anyxboxx-launcher.exe, or):
.\target\release\anyxboxx-launcher.exe
```

- `anyxboxx run` first builds VIctory (`cargo build --profile diag -p victory --features diagnostics`), like the script, so the first launch takes several minutes. `--precompile` fills the shader cache before the game (about 4.5 minutes the first time, measured on 2026-11-25). The first cold launch may crash while pipelines compile; launch again once the cache is full.
- The PowerShell option names are accepted too (`--GameDir`, `--XgDll`, `--XgMode`, `--Precompile`, `--Dred`, `--NoTunedSettings`, `--SkipPipelines`, `--BatchCardRehash`). `anyxboxx run --help` lists them.
- One game at a time: close any running game first. The graphical launcher checks this itself.

### Linux (Proton)

Native Linux builds are not supported: VIctory, which the root workspace uses through `victory-hle`, only builds for Windows (`victory-gpu` uses its `#[cfg(windows)]` modules unconditionally). Cross-build both workspaces for Windows instead, with an MSVC CRT and SDK on Linux (for example [xwin](https://github.com/Jake-Shadle/xwin)) and `lld-link`:

```bash
cargo build --release --workspace --target x86_64-pc-windows-msvc \
    --exclude anyxboxx-kernelx --exclude anyxboxx-d3d12-xs
(cd third_party/victory && cargo build --profile diag -p victory --features diagnostics --target x86_64-pc-windows-msvc)
```

- `kernelx` and `d3d12_xs` need MSVC's `lib.exe` to make the `.exp` of their forwarder table (`anyxboxx-forwarders::link`); `llvm-lib /DEF` writes only the `.lib`. Not blocking: the game runs through VIctory, which does not load these DLLs.
- There is no cargo inside Proton, so `anyxboxx.exe run` takes the cross-built VIctory with `--victory-exe` and skips the build (the repository is then not needed). Run it with Proton's `wine` and the Wine prefix of your choice, paths written as `Z:\…`:

```bash
VKD3D_CONFIG=descriptor_heap "$PROTON/files/bin/wine" target/x86_64-pc-windows-msvc/release/anyxboxx.exe run \
    --victory-exe 'Z:\…\third_party\victory\target\x86_64-pc-windows-msvc\diag\victory.exe' \
    --game-dir 'Z:\…\your game folder'
```

- `anyxboxx run` sets the Windows tuned set (`TUNED`), not the `linux-amd` profile, which only the graphical launcher reads. Wine passes the Linux environment on, so export `VKD3D_CONFIG=descriptor_heap` (the title's view heap is larger than vkd3d-proton's default cap) and, for the `linux-amd` values, add `--no-tuned-settings` and export them yourself.
- The graphical launcher has no `--victory-exe` yet: its Play and Shaders pages start with the cargo build, which fails under Proton.

### Graphical launcher (`crates/anyxboxx-launcher`)

It is built with egui through eframe 0.34: pure Rust, no C++ binding, no installer. The window has four pages with progress bars, a log and a few dialogs, which immediate-mode egui draws in a few hundred lines. Raw Win32 would have meant hand-written message loops and layout for the same pages. The logic lives in plain modules that the window only calls, so the 80 tests never open a window.

| Page | What it does | Limits |
| --- | --- | --- |
| Setup | Checks the Rust toolchain, `d3d12.dll`, the VC++ runtime (present, version not checked), `dxc` from the Windows SDK, and the GPU through DXGI. Links to official pages only; nothing is downloaded. | Driver version shows "unknown": the repository records no minimum yet. |
| Files | Game folder (typed path): presence, empty files, PE section bounds (a truncated exe or DLL), RPF7 header table bounds, and a SHA-256 manifest of the required files and top-level `.rpf`, computed locally. Nothing is copied or uploaded. | There are no reference hashes, so the manifest is a record, not proof. An archive cut after intact tables is not detected. The RPF7 layout was not checked against a real file. |
| Shaders | `victory translate --cache --pipelines --used-pipelines … --jobs N` on `shaders.rpf`, the exe and its two DLLs only, with the game's environment (the cache key depends on it). Progress is read from VIctory's "N of M containers (x%)" lines. It refuses to run while `victory.exe` or the game is running. | |
| Play | Profile chosen by OS and GPU (`profiles.toml`), overrides in the advanced panel, optional `xg_xs.dll` (real or compare), build then launch through the same steps as `anyxboxx run`, saves location, clean shader cache (asks for confirmation; only a folder named `cache` can be deleted). | VIctory prints fps only in its window title, so there is no fps line to show. The saves path shown is VIctory's data folder, not the per-title subfolder. |

Profiles (`crates/anyxboxx-launcher/profiles.toml`, one test each):

- **Windows + NVIDIA:** your working set (the six `TUNED` values of `anyxboxx run`, no DRED, no relay). Measured: 2-3 fps on `main` after PR #199, 5-7 fps on the fork at `80d58f8`. Setting PR #199's switches to `0` did not change the `main` figure, so the profile leaves them at VIctory's defaults.
- **Linux (Proton) + AMD:** the values of PR #199's run (RX 9070 XT, RADV, GE-Proton11-12):
  - `SHADER_LOOP_LIMIT=256`, `LATE_WAIT=0`, `WIDE_BACK=0`, `PIPELINE_WAIT_MS=50`
  - `TEXTURE_BUDGET_MB=8192` (sized for a 16 GB card), `TEXTURE_NO_WAIT=1`
  - `CARD_BUFFERS_MIN_MB=1`, `CARD_BUFFERS_MB=1024`
  - `VKD3D_CONFIG=descriptor_heap`
- **Windows + AMD, Intel, others:** VIctory's defaults, marked "unmeasured".

## Component by component

| Component (before) | Now on `rust/full` | Parity check | Old code |
| --- | --- | --- | --- |
| `tools/lancer_victory.ps1` (PowerShell) | `anyxboxx run` (`crates/anyxboxx`) | same calls, `VICTORY_*` environment and exit codes as the script, with a fake cargo and victory.exe | **deleted**; `tests/test_anyxboxx_run.py` keeps the expectations |
| `emu/loader.py` (PE loader) | `crates/anyxboxx-pe` (on `victory-pe`) | `tests/test_rust_pe_parity.py`: 13 images, same JSON and page protections | kept (the Python sandbox still uses it) |
| `--rapport` (`emu/report.py`, `config.py`) | `anyxboxx rapport` (`crates/anyxboxx-report`) | `tests/test_rust_rapport_parity.py`: same text on 7 targets, same refusals on 5 | kept (used by the Python CLI and tools) |
| `--traduction` | `anyxboxx traduction` | `tests/test_rust_traduction_parity.py`: same table, byte-identical SVG on 6 setups | kept |
| `--carte` | `anyxboxx carte` | `tests/test_rust_carte_parity.py`: byte-identical SVG and badges on 5 cases plus 3 synthetic GDK tables | kept |
| `tools/jour_j.py` | `anyxboxx jour-j` | `tests/test_rust_jour_j_parity.py`: static part of `rapport.md` byte-identical on 5 cases | kept: the Unicorn and native launch sections are stated as not available in Rust (D2, D4), so the port is partial |
| `--banc` | `anyxboxx banc` | `tests/test_rust_banc_parity.py`: Module, Imports and Resolved columns and the footer | kept: the load/init columns need the Unicorn sandbox (D2) and show `n/d` |
| `rust/` (texture, audio, RDNA 2 bridge) | `crates/` (one workspace) | existing tests unchanged | `rust/Cargo.toml` deleted |
| `runtime/xcrdapi` | `crates/anyxboxx-xcrdapi` | `test_xcrdapi.py`, identical export table | **deleted** |
| `runtime/kernelx` | `crates/anyxboxx-kernelx` (2,661 forwarders) | `test_kernelx.py`, identical export table | **deleted** (the forwarder table moved into the crate) |
| `runtime/d3d12_xs` | `crates/anyxboxx-d3d12-xs` | `test_d3d12_virtual_memory.py`, `test_runtime_cpp.py`, identical export table | **deleted** |
| `runtime/tls` (`anyxboxx_tls.dll`) | `crates/anyxboxx-tls`, a `no_std` cdylib | `test_native_tls.py`, `test_native_tls_callbacks.py`, identical export table | **deleted** |
| `runtime/xmem` | `crates/anyxboxx-xmem` (ERA attributes shared with VIctory's xmem module) | `test_xmem_era.py`, `test_xmem_virtual.py`, `test_runtime_cpp.py`, identical export table | **deleted** |
| `runtime/xgameruntime` | `crates/anyxboxx-xgameruntime` (task queue = VIctory's `xasync`) | 66 of the 90 GDK tests pass against it | kept: saves, store, platform (HDR, networking), gamer picture and the DXGI frame counter are not ported yet |
| Graphical launcher | `crates/anyxboxx-launcher` (new) | 80 Rust tests | |

How the Rust runtime DLLs reach the runtime folder: `cargo build --release` builds them, and `runtime/CMakeLists.txt` copies them from `target/release` into `runtime/build/bin` (`rust_dlls.cmake`; a missing one stops the build with the command to run). So `cargo build --release` now comes before `cmake` (CI, AGENTS.md, READMEs).

TLS carrier finding: as a `no_std` cdylib, its TLS block holds exactly the carrier (262,208 bytes, no Rust std thread-locals). The game's template therefore shares it as with the C++ DLL. `no_std` needs `panic = "abort"`, which Cargo only accepts for the whole release profile, so the root workspace's release profile now aborts on panic.

**Still C++:**

- `runtime/xgameruntime` (24 of its 90 tests still fail with the Rust DLL).
- `runtime/launcher` (`anyxboxx.exe`): decision D4 deletes it, but its native-mode tests have no Rust counterpart yet.
- `runtime/gpu_runner`: phase 4.
- `runtime/third_party/libhttpclient-task`: goes with xgameruntime.

**Still Python:**

- The Unicorn sandbox and its HLE handlers (dropped in the end state, D2).
- `emu/modules.py`, `emu/loader.py`, `report.py`, `status_map.py`, `translation.py`, `bench.py`, `tools/jour_j.py`: they have Rust ports with parity, but other Python code (the CLI, the GUI window, the sandbox) still imports them. They go together with the sandbox.
- RDNA 2 (`emu/rdna2*.py`, phase 4). Until then, `anyxboxx traduction` reads the RDNA 2 coverage from `crates/anyxboxx-report/data/rdna2-coverage.txt`; a test fails when that table drifts from the Python measure, and `python tests/test_rust_traduction_parity.py` regenerates it.
- `tools/*.py` and the pytest suite (the oracle).

## Checks on this branch (2026-11-25, Windows 11, Rust 1.98.1, Python 3.12)

```
python -m pytest                       → 1251 passed, 11 skipped
python -m ruff check --select W605,F,E9 PrototypeScarlett tests tools → All checks passed!
cargo test --release --workspace       → 198 passed, 0 failed
cargo clippy --release --workspace --all-targets → 0 warnings
cargo fmt --check                      → clean
```

The runtime was built from this branch (cargo, then CMake). With `ANYXBOXX_REQUIRE_RUNTIME=1`, the TomBox DLL tests also need `python tools/build_tombox.py`.

## Findings along the way

- VIctory does not compile without its `diagnostics` feature at this commit (`victory_gpu::queue::presented` is gated by it but used outside it). The root workspace depends on `victory-hle` with that feature, the way VIctory is always built.
- VIctory writes fps only to its window title. A stdout fps line in VIctory would let both launchers show it.
- VIctory's test `a_read_in_place_never_meets_the_gap_of_a_remapping` (victory-hle, xmem) is flaky: it fails about 3 times in 8 on the unmodified file.
- The Windows+NVIDIA profile was corrected after the maintainer's test: PR #199's switches at `0` made no difference (2-3 fps on `main`, 5-7 fps on the fork at `80d58f8`).
