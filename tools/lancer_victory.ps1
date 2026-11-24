<#
.SYNOPSIS
  Builds (if needed) and launches VIctory (third_party/victory) on the user's own game folder.

.PARAMETER GameDir
  Folder of the game package (kept outside this repository). It must contain game_scarlett_master.exe.

.PARAMETER SkipPipelines
  Optional. Passed unchanged to VICTORY_SKIP_PIPELINES when given.

.EXAMPLE
  .\tools\lancer_victory.ps1 -GameDir D:\Games\MyPackage
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$GameDir,
    [string]$SkipPipelines
)

$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$victory = Join-Path $repo 'third_party\victory'
$manifest = Join-Path $victory 'Cargo.toml'

if (-not (Test-Path -LiteralPath $manifest)) {
    throw "third_party/victory is empty: run 'git submodule update --init third_party/victory'."
}

$gameExe = Join-Path $GameDir 'game_scarlett_master.exe'
if (-not (Test-Path -LiteralPath $gameExe)) {
    throw "game_scarlett_master.exe not found in '$GameDir'."
}

# The submodule is its own Cargo workspace: its target folder is third_party\victory\target
# unless CARGO_TARGET_DIR is set.
$target = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { Join-Path $victory 'target' }
$exe = Join-Path $target 'diag\victory.exe'

if (-not (Test-Path -LiteralPath $exe)) {
    Write-Host 'Building VIctory (diag profile, diagnostics feature)...'
    & cargo build --profile diag -p victory --features diagnostics --manifest-path $manifest
    if ($LASTEXITCODE -ne 0) { throw "cargo build failed (exit code $LASTEXITCODE)." }
}

# No victory.toml is needed: VIctory reads the game folder from VICTORY_GAME_DIR.
$env:VICTORY_GAME_DIR = $GameDir
# Dynamic descriptor range sized for NVIDIA's capped heap (262,144 slots).
$env:VICTORY_CAPPED_DYNAMIC = '262144'
# Translated shader loops stop after 32 iterations.
$env:VICTORY_SHADER_LOOP_LIMIT = '32'
if ($PSBoundParameters.ContainsKey('SkipPipelines') -and $SkipPipelines) {
    $env:VICTORY_SKIP_PIPELINES = $SkipPipelines
}

& $exe run $gameExe --execute
exit $LASTEXITCODE
