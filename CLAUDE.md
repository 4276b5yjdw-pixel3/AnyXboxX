# CLAUDE.md

@AGENTS.md

## For Claude Code

- Follow AGENTS.md: it holds the layout, commands and rules of this repository.
- Talk to the maintainer in French; code identifiers, README and image text stay in English, research notes in `docs/` in French.
- Before a pull request: run the full pytest suite and the ruff check from AGENTS.md, rebuild `runtime/` with CMake when C++ changed, and `cargo build --release --manifest-path rust/Cargo.toml` when Rust changed.
- Regenerate `PrototypeScarlett/emu/rdna2_ops.py` and `rdna2_shapes.py` with the tools instead of editing them; the LLVM test files are downloaded locally from `llvm/test/MC/AMDGPU` and never committed.
- When a README table row changes, update all 8 languages in the same commit, and regenerate `docs/images/carte-avancee.svg` and `traduction.svg` with `scarlett.py --carte ..` and `--traduction ..` when the counts move.
- Never read, copy or commit files from the game package in the parent folder beyond the static, local analyses already documented in `docs/recherche/`.
