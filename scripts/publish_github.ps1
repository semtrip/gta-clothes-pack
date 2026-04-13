# Публикация на GitHub: репозиторий + релиз с gta-clothes-pack.exe
# Требуется: gh auth login  (один раз)
# Использование:
#   .\scripts\publish_github.ps1 -RepoOwner "ВАШ_NICK" [-RepoName "gta-clothes-pack"] [-Version "0.1.0"]

param(
    [Parameter(Mandatory = $true)]
    [string] $RepoOwner,
    [string] $RepoName = "gta-clothes-pack",
    [string] $Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$gh = "gh"
if (Get-Command gh -ErrorAction SilentlyContinue) { }
elseif (Test-Path "C:\Program Files\GitHub CLI\gh.exe") {
    $gh = "C:\Program Files\GitHub CLI\gh.exe"
} else {
    Write-Error "Установите GitHub CLI: winget install GitHub.cli"
}

# Сборка exe
python -m pip install -q -r requirements.txt -r requirements-build.txt
python -m pip install -q -e .
python -m PyInstaller --noconfirm --clean gta-clothes-pack.spec

$exe = Join-Path $root "dist\gta-clothes-pack.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Не найден $exe"
}

# Убедиться что есть коммит
$st = git status --porcelain 2>$null
if ($st) {
    git add -A
    git commit -m "chore: prepare release $Version"
}

# Создать репозиторий на GitHub и запушить (если remote ещё нет)
$remotes = git remote 2>$null
if (-not ($remotes -match "origin")) {
    & $gh repo create "$RepoOwner/$RepoName" --public --source=. --remote=origin --push
} else {
    git push -u origin master 2>$null
    if ($LASTEXITCODE -ne 0) { git push -u origin main }
}

# Тег и релиз с вложением
$tag = "v$Version"
git tag -a $tag -m "Release $Version" 2>$null
git push origin $tag 2>$null

& $gh release create $tag $exe `
    --repo "$RepoOwner/$RepoName" `
    --title "gta-clothes-pack $Version" `
    --notes "Windows x64, one-file build (PyInstaller). See README."

Write-Host "Готово: https://github.com/$RepoOwner/$RepoName/releases/tag/$tag"
