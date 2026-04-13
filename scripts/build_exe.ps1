# Сборка одного исполняемого файла: dist\gta-clothes-pack.exe
# Из корня проекта:
#   pip install -r requirements.txt -r requirements-build.txt
#   pip install -e .
#   .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install -q -r requirements.txt -r requirements-build.txt
python -m pip install -q -e .

if (-not (Test-Path "gta-clothes-pack.spec")) {
    Write-Host "Создайте gta-clothes-pack.spec (см. README) или выполните первую сборку PyInstaller."
    python -m PyInstaller --noconfirm --clean --onefile --console --name "gta-clothes-pack" `
        --collect-all fivefury --hidden-import gta_clothes_pack.cli entry_exe.py
} else {
    python -m PyInstaller --noconfirm --clean gta-clothes-pack.spec
}

Write-Host "Готово: $root\dist\gta-clothes-pack.exe"
