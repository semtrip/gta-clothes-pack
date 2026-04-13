# Build single-file exe: dist\gta-clothes-pack.exe
# From repo root: pip install -r requirements.txt -r requirements-build.txt; pip install -e .; .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install -q -r requirements.txt -r requirements-build.txt
python -m pip install -q -e .

if (-not (Test-Path "gta-clothes-pack.spec")) {
    Write-Host "Create gta-clothes-pack.spec (see README) or run a first PyInstaller build."
    python -m PyInstaller --noconfirm --clean --onefile --console --name "gta-clothes-pack" `
        --collect-all fivefury --hidden-import gta_clothes_pack.cli entry_exe.py
} else {
    python -m PyInstaller --noconfirm --clean gta-clothes-pack.spec
}

Write-Host "Done: $root\dist\gta-clothes-pack.exe"
