# Полная сборка: подмодули (опционально), зависимости Python, PyInstaller exe.
# MetaTool в сборку не входит — при необходимости: .\scripts\build_meta_tool.ps1
# From repo root:
#   .\scripts\build_all.ps1
#   .\build_all.bat
param(
    [switch]$SkipSubmodule,
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

Write-Step "Repository: $RepoRoot"

if (-not $SkipSubmodule) {
    if (Test-Path (Join-Path $RepoRoot ".git")) {
        Write-Step "Git submodules"
        git submodule update --init --recursive
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "No .git directory; skip submodule init."
    }
} else {
    Write-Host "Skip: git submodules (-SkipSubmodule)."
}

if (-not $SkipPyInstaller) {
    Write-Step "Python package + PyInstaller (see scripts\build_exe.ps1)"
    $exeScript = Join-Path $PSScriptRoot "build_exe.ps1"
    & $exeScript
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
    Write-Host "EXE: $RepoRoot\dist\gta-clothes-pack.exe" -ForegroundColor Green
} else {
    Write-Step "Python dependencies and editable install only"
    python -m pip install -q -r requirements.txt -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    python -m pip install -q -e .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Skip: PyInstaller (-SkipPyInstaller)."
}

Write-Host ""
Write-Host "Build finished." -ForegroundColor Green
