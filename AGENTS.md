# AGENTS.md — AnyXboxX

Guide for AI coding agents and contributors working in this repository. Human contribution rules (fork, pull request, review) are in [CONTRIBUTING.md](CONTRIBUTING.md), in French.

## What the project is

AnyXboxX is a GPL-3.0-or-later prototype that runs Xbox Series X (GDK, "Scarlett") executables on Windows by high-level emulation: console system calls are served by a C++ runtime (native mode, Wine-style) or by Python handlers inside a Unicorn sandbox (isolated mode). A second track translates console RDNA 2 GPU shaders to HLSL/DXIL. It does not run commercial games.

## Layout

| Path | Content |
| --- | --- |
| `PrototypeScarlett/scarlett.py` | Command line entry point (`--rapport`, `--banc`, `--natif`, `--lancer`, `--rdna2`, `--carte`, `--traduction`…) |
| `PrototypeScarlett/emu/` | Python: PE loader, Unicorn machine, HLE handlers (`hle/`), native mode (`native/`), reports |
| `PrototypeScarlett/emu/rdna2*.py` | RDNA 2: decoder, operands, reference interpreter (`rdna2_exec*`), HLSL recompiler (`rdna2_hlsl*`), GPU runner glue (`rdna2_gpu.py`) |
| `PrototypeScarlett/emu/rdna2_ops.py`, `rdna2_shapes.py` | **Generated** from LLVM's public encoding tests by `tools/rdna2_mnemonics.py` and `tools/rdna2_shapes.py`. Never edit by hand. |
| `runtime/` | C++ runtime DLLs (`xgameruntime`, `xmem`, `d3d12_xs`, `kernelx`, `anyxboxx_tls`), native launcher `anyxboxx.exe`, GPU runner `anyxboxx_gpu_run.exe` |
| `rust/` | Rust workspace. `anyxboxx-rdna2` bridges to TomBox's RDNA 2 decoder; `anyxboxx-texture` decodes BC7 and GFX10 `SW_4K_S` tiles (ported from Xbox2Windows); `anyxboxx-audio` decodes XMA2 with TomBox's FFmpeg port. |
| `third_party/tombox/` | Git submodule: [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator) (TomBox continuation, GPL-3.0-or-later since its commit `51f5319`, MIT OR Apache-2.0 before), pinned commit. Do not edit; propose changes upstream. |
| `third_party/leonida-src/` | Git submodule: the whole [ItsNotRexed/Leonida](https://github.com/ItsNotRexed/Leonida) repository (GPL-3.0; static recompilation of the Xbox Series 1.0.2.1 build: `gta6rt` runtime, GDK shims, D3D12 → Vulkan, asset tools), pinned commit, advanced hourly by the `voisins` workflow. Do not edit; propose changes upstream. `third_party/leonida/` keeps the unchanged translator copies that `PrototypeScarlett` calls. |
| `tools/` | Generators and comparison tools (GDK interface table, kernelx exports, RDNA 2 tables, TomBox comparison) |
| `tests/` | pytest suite (about 220 tests) |
| `docs/` | Research notes and logs, in French. `docs/i18n/` holds the 7 README translations. |

## Setup and commands

Windows x64, Python 3.12, Visual Studio 2022/2026 (C++ workload, CMake), Windows SDK 10.0.26100 (provides `dxc`), Rust stable (MSVC).

```powershell
git submodule update --init
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
cmake -S runtime -B runtime/build -A x64
cmake --build runtime/build --config Release
cargo build --release --manifest-path rust/Cargo.toml
.\.venv\Scripts\python.exe -m pytest
```

- Tests needing the C++ runtime are skipped when it is not built, except in CI (`ANYXBOXX_REQUIRE_RUNTIME=1`).
- GPU tests (`tests/test_rdna2_hlsl.py`) need `dxc` and `anyxboxx_gpu_run.exe`; without a GPU they use WARP (`ANYXBOXX_GPU=warp` forces it).
- Lint used by the maintainers: `python -m ruff check --select W605,F,E9 PrototypeScarlett tests tools`.

## Rules

1. **No protected content.** Never add game files, console or SDK files, keys, dumps, extracted assets or shaders, or commercial executables, not even partial ones or in tests. The game package next to the repository is studied locally only. Build test inputs from source (`tests/pe_builder.py`, the encoders in `tests/test_rdna2_exec*.py`).
2. **Public sources only**: AMD's RDNA 2 ISA documentation, Microsoft Learn (GDK, Win32, D3D12), LLVM's tests, and open-source code under a compatible licence, credited in [THIRD_PARTY.md](THIRD_PARTY.md).
3. **No fake success.** An unimplemented function returns `E_NOTIMPL` (or the console's error) and is logged; an untranslated instruction raises an error that names it.
4. **Verify against an oracle.** Decoder changes are checked against the LLVM tables (`python tools/rdna2_mnemonics.py <llvm .s folder> --verifier`); every HLSL translation is checked against the reference interpreter, byte for byte, on GPU or WARP.
5. **Tests with every change.** New behaviour comes with a test that fails without it.
6. **README in 8 languages.** `README.md` (English) and `docs/i18n/README.*.md` must stay in sync: same table rows, same test count, same images. Image text is in English.
7. **Git**: `main` is protected; work on a branch and open a pull request; CI (`.github/workflows/tests.yml`) must pass. Commit messages: `type: description` (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`), written in French like the history.
8. **Code style**: small focused files (under about 400 lines), small functions, explicit error handling, no hidden mutation of shared state, constants instead of magic numbers where it helps reading.
9. **Native mode runs code unsandboxed.** Only run trusted test programs with `--natif` or `anyxboxx.exe`.

## Where to start

When a console executable becomes available, start with `python tools/jour_j.py <package folder>` ([docs/jour-j.md](docs/jour-j.md)): its report stays outside the repository.

Open issues list what remains, each with a "done when" checklist. Most console-library and Direct3D 12.x work is blocked on a legally usable Scarlett executable; RDNA 2 shader work (`emu/rdna2*`) and GDK runtime functions (`runtime/xgameruntime`) can progress from public documentation.
