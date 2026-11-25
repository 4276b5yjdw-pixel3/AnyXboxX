"""`anyxboxx run` (crates/anyxboxx): builds VIctory, then launches it on the user's own game folder.

It replaced tools/lancer_victory.ps1 after passing a parity test against it (same calls, same
environment, same exit codes); these are the expectations of that test, kept without the script.
The launcher runs against a fake repository and game, with a fake cargo on the PATH and a fake
victory.exe already built; the fake tool logs every call and the VICTORY_* variables it sees.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BINARY = REPO / "target" / "release" / "anyxboxx.exe"
CARGO_FAILURE, VICTORY_EXIT = 101, 7
TUNED = ("VICTORY_CARD_BUFFERS_MB=1024", "VICTORY_CARD_BUFFERS_MIN_MB=1", "VICTORY_DSTORAGE_NOTIFY=1",
         "VICTORY_LATE_WAIT=3", "VICTORY_SHADER_LOOP_LIMIT=256", "VICTORY_WIDE_BACK=1")
BUILD = r"cargo build --profile diag -p victory --features diagnostics --manifest-path <root>\depot\third_party\victory\Cargo.toml | "
GAME = r"victory run <root>\game\game_scarlett_master.exe --execute | "
TRANSLATE = (r"victory translate --cache --pipelines --used-pipelines <root>\game\shaders.rpf "
             r"<root>\game\game_scarlett_master.exe <root>\game\XboxBvhBuilder.dll "
             r"<root>\game\amd_fidelityfx_upscaler_xbox.dll | ")
GAME_DIR = r"VICTORY_GAME_DIR=<root>\game"

# Fake console tool (.NET Framework, compiled by Windows PowerShell), copied as cargo.exe and victory.exe. Its exit
# code comes from FAKE_TOOL_EXIT_<NAME>_<FIRST ARGUMENT>, else FAKE_TOOL_EXIT_<NAME>, else 0.
FAKE_TOOL = r"""
using System; using System.IO; using System.Linq; using System.Collections;
public static class FakeTool {
    public static int Main(string[] args) {
        string name = Path.GetFileNameWithoutExtension(System.Reflection.Assembly.GetEntryAssembly().Location);
        var env = Environment.GetEnvironmentVariables().Cast<DictionaryEntry>()
            .Select(e => (string)e.Key).Where(k => k.StartsWith("VICTORY_")).OrderBy(k => k, StringComparer.Ordinal)
            .Select(k => k + "=" + Environment.GetEnvironmentVariable(k));
        File.AppendAllText(Environment.GetEnvironmentVariable("FAKE_TOOL_LOG"),
                           name + " " + string.Join(" ", args) + " | " + string.Join(";", env) + Environment.NewLine);
        string key = "FAKE_TOOL_EXIT_" + name.ToUpperInvariant();
        string code = Environment.GetEnvironmentVariable(args.Length > 0 ? key + "_" + args[0].ToUpperInvariant() : key)
                      ?? Environment.GetEnvironmentVariable(key);
        return string.IsNullOrEmpty(code) ? 0 : int.Parse(code);
    }
}
"""


@pytest.fixture(scope="module")
def fake_tool(tmp_path_factory):
    if sys.platform != "win32" or not shutil.which("powershell"):
        pytest.skip("the fake tools are .NET programs compiled by Windows PowerShell")
    folder = tmp_path_factory.mktemp("fake-tool")
    source, exe = folder / "FakeTool.cs", folder / "FakeTool.exe"
    source.write_text(FAKE_TOOL, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Add-Type -Path '{source}' -OutputAssembly '{exe}' -OutputType ConsoleApplication"],
                   check=True, capture_output=True, timeout=120)
    return exe


@pytest.fixture(scope="module")
def binary():
    if not BINARY.is_file():
        if os.environ.get("ANYXBOXX_REQUIRE_RUNTIME") == "1":
            pytest.fail(f"{BINARY} absent: cargo build --release (root workspace).")
        pytest.skip("anyxboxx not built (cargo build --release at the root)")
    return BINARY


def launch(tmp_path, fake_tool, binary, options=(), *, cargo_exit=0, game_exe=True, precompile_inputs=False):
    """Runs `anyxboxx run` in a fake repository; returns (process, calls with <root> for tmp_path)."""
    manifest = tmp_path / "depot" / "third_party" / "victory" / "Cargo.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("", encoding="utf-8")
    game = tmp_path / "game"
    game.mkdir()
    if game_exe:
        (game / "game_scarlett_master.exe").write_bytes(b"")
    if precompile_inputs:
        for name in ("shaders.rpf", "XboxBvhBuilder.dll", "amd_fidelityfx_upscaler_xbox.dll"):
            (game / name).write_bytes(b"")
    (tmp_path / "target" / "diag").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    shutil.copy(fake_tool, tmp_path / "target" / "diag" / "victory.exe")
    shutil.copy(fake_tool, tmp_path / "tools" / "cargo.exe")
    (tmp_path / "xg_xs.dll").write_bytes(b"")
    log = tmp_path / "calls.log"
    env = {k: v for k, v in os.environ.items() if not k.startswith("VICTORY_")}
    env.update({"PATH": f"{tmp_path / 'tools'}{os.pathsep}{os.environ['PATH']}",
                "CARGO_TARGET_DIR": str(tmp_path / "target"), "FAKE_TOOL_LOG": str(log),
                "FAKE_TOOL_EXIT_CARGO": str(cargo_exit), "FAKE_TOOL_EXIT_VICTORY_RUN": str(VICTORY_EXIT)})
    options = [o.replace("{xg}", str(tmp_path / "xg_xs.dll")) for o in options]
    command = [str(binary), "run", "--repo", str(tmp_path / "depot"), "--game-dir", str(game), *options]
    done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
    calls = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    return done, [call.replace(str(tmp_path), "<root>") for call in calls]


def test_default_launch_builds_then_runs_with_the_tuned_settings(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary)
    assert calls == [BUILD, GAME + ";".join(sorted((GAME_DIR, *TUNED)))], done.stderr
    assert done.returncode == VICTORY_EXIT


def test_opt_in_switches_and_no_tuned_settings(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary,
                         ["--no-tuned-settings", "--dred", "--batch-card-rehash", "--skip-pipelines", "5"])
    expected = (GAME_DIR, "VICTORY_CARD_REHASH_RUNS=1", "VICTORY_D3D12_DRED=1", "VICTORY_SKIP_PIPELINES=5")
    assert calls == [BUILD, GAME + ";".join(sorted(expected))], done.stderr


def test_the_users_xg_library_is_passed_with_its_mode(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, ["--no-tuned-settings", "--xg-dll", "{xg}", "--xg-mode", "compare"])
    expected = (GAME_DIR, r"VICTORY_XG_DLL=<root>\xg_xs.dll", "VICTORY_XG_MODE=compare")
    assert calls == [BUILD, GAME + ";".join(sorted(expected))], done.stderr


def test_a_missing_xg_library_stops_after_the_build(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, ["--xg-dll", "missing.dll"])
    assert calls == [BUILD] and done.returncode == 1
    assert "xg_xs.dll not found" in done.stderr


def test_precompile_translates_with_the_game_environment_first(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, ["--no-tuned-settings", "--precompile"], precompile_inputs=True)
    assert calls == [BUILD, TRANSLATE + GAME_DIR, GAME + GAME_DIR], done.stderr
    assert done.returncode == VICTORY_EXIT


def test_precompile_needs_the_shader_archive(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, ["--precompile"])
    assert calls == [BUILD] and done.returncode == 1
    assert "shaders.rpf" in done.stderr


def test_a_failed_build_stops_the_launch(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, cargo_exit=CARGO_FAILURE)
    assert calls == [BUILD] and done.returncode == 1
    assert f"cargo build failed (exit code {CARGO_FAILURE})" in done.stderr


def test_a_missing_game_stops_before_building(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, game_exe=False)
    assert calls == [] and done.returncode == 1
    assert "game_scarlett_master.exe not found" in done.stderr


def test_powershell_option_names_still_work(tmp_path, fake_tool, binary):
    done, calls = launch(tmp_path, fake_tool, binary, ["--NoTunedSettings", "--Dred"])
    assert calls == [BUILD, GAME + ";".join(sorted((GAME_DIR, "VICTORY_D3D12_DRED=1")))], done.stderr
