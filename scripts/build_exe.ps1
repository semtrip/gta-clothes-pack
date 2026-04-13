# Build single-file exe: dist\gta-clothes-pack.exe
# From repo root: pip install -r requirements.txt -r requirements-build.txt; pip install -e .; .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$metaPaths = @(
    (Join-Path $root "tools\MetaTool\bin\Release\MetaTool.exe")
    (Join-Path $root "tools\MetaTool\bin\Debug\MetaTool.exe")
    (Join-Path $root "tools\gta-toolkit\Tools\MetaTool\bin\Release\MetaTool.exe")
    (Join-Path $root "tools\gta-toolkit\Tools\MetaTool\bin\Debug\MetaTool.exe")
    (Join-Path $root "tools\metatool\MetaTool.exe")
)
$metaFound = $false
foreach ($mp in $metaPaths) {
    if (Test-Path -LiteralPath $mp) { $metaFound = $true; break }
}
if (-not $metaFound) {
    Write-Warning "MetaTool.exe not found (build scripts\build_meta_tool.ps1 first). PyInstaller exe will not bundle MetaTool; use env GTA_CLOTHES_META_TOOL or place MetaTool.exe next to the app."
}

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
