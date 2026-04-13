# Публикация через GitHub CLI (локальная сборка exe + релиз)
# 1) winget install GitHub.cli
# 2) gh auth login
# Запуск из корня репозитория:
#   .\scripts\publish_github.ps1 -Repo "username/gta-clothes-pack" -Version "0.1.0"

param(
    [Parameter(Mandatory = $true)]
    [string] $Repo,
    [string] $Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    $candidates = @(
        "C:\Program Files\GitHub CLI\gh.exe",
        "$env:ProgramFiles\GitHub CLI\gh.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $gh = @{ Source = $c }
            break
        }
    }
}
if (-not $gh) {
    Write-Error "Установите GitHub CLI: winget install GitHub.cli"
}

$ghExe = if ($gh.Source) { $gh.Source } else { "gh" }

python -m pip install -q -r requirements.txt -r requirements-build.txt
python -m pip install -q -e .
python -m PyInstaller --noconfirm --clean gta-clothes-pack.spec

$exe = Join-Path $root "dist\gta-clothes-pack.exe"
if (-not (Test-Path $exe)) { Write-Error "Не найден $exe" }

$remotes = git remote
if (-not ($remotes -match "origin")) {
    & $ghExe repo create $Repo --public --source=. --remote=origin --push
} else {
    git push -u origin main
}

$tag = "v$Version"
git tag -a $tag -m "Release $Version" 2>$null
git push origin $tag

& $ghExe release create $tag $exe --repo $Repo --title "gta-clothes-pack $Version" --generate-notes

Write-Host "Релиз: https://github.com/$Repo/releases/tag/$tag"
