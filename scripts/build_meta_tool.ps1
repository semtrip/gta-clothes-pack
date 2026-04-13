# MetaTool from submodule tools/gta-toolkit (MSBuild + .NET Framework 4.7.2 targeting pack).
# Success output: tools/gta-toolkit/Tools/MetaTool/bin/Release/MetaTool.exe
# Skip MSBuild if MetaTool.exe exists: tools\MetaTool\bin\…, gta-toolkit\…\bin\…, tools\metatool\, env vars (see below).
# Rebuild: -Force or GTA_CLOTHES_FORCE_META_TOOL_REBUILD=1.
param(
    [switch]$SkipNet472Install,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Test-PathFile {
    param([string]$LiteralPath)
    if (-not $LiteralPath) { return $false }
    return [System.IO.File]::Exists($LiteralPath)
}

function Test-Net472DeveloperPack {
    foreach ($base in @(${env:ProgramFiles(x86)}, ${env:ProgramFiles})) {
        if (-not $base) { continue }
        $mscor = Join-Path $base "Reference Assemblies\Microsoft\Framework\.NETFramework\v4.7.2\mscorlib.dll"
        if (Test-Path -LiteralPath $mscor) { return $true }
    }
    return $false
}

# Офлайн-установщик NDP472 часто завершается раньше, чем доработает msiexec — ждём появления mscorlib на диске.
function Wait-Net472ReferenceAssemblies {
    param([int]$TimeoutSec = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $n = 0
    while ((Get-Date) -lt $deadline) {
        if (Test-Net472DeveloperPack) { return $true }
        if (($n % 5) -eq 0) {
            Write-Host "Waiting for .NET 4.7.2 reference assemblies (msiexec may still be running)... $([int]($deadline - (Get-Date)).TotalSeconds)s left"
        }
        $n++
        Start-Sleep -Seconds 2
    }
    return (Test-Net472DeveloperPack)
}

function Test-Administrator {
    $p = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Net472DeveloperPack {
    # Official Microsoft offline installer (Developer Pack = reference assemblies for MSBuild).
    $Fwlink = "https://go.microsoft.com/fwlink/?linkid=874338"
    $ExeName = "NDP472-DevPack-ENU.exe"
    $Out = Join-Path $env:TEMP $ExeName

    if (-not (Test-Path $Out)) {
        Write-Host "Downloading .NET Framework 4.7.2 Developer Pack (Microsoft)..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Fwlink -OutFile $Out -UseBasicParsing
    } else {
        Write-Host "Using cached installer: $Out"
    }
    $len = (Get-Item $Out).Length
    if ($len -lt 5MB) {
        Remove-Item $Out -Force -ErrorAction SilentlyContinue
        Write-Error "Download looks invalid (size $len bytes). Check network or download manually: $Fwlink"
    }

    $Args = @("/quiet", "/norestart")
    if (Test-Administrator) {
        Write-Host "Installing .NET Framework 4.7.2 Developer Pack (quiet)..."
        $p = Start-Process -FilePath $Out -ArgumentList $Args -Wait -PassThru
        $code = $p.ExitCode
    } else {
        Write-Host "Administrator rights required. UAC prompt for Developer Pack installer..."
        $p = Start-Process -FilePath $Out -ArgumentList $Args -Verb RunAs -Wait -PassThru
        $code = $p.ExitCode
    }

    # 0 = success; 3010 = success, reboot recommended. RunAs иногда даёт $null — всё равно ждём файлов на диске.
    if ($null -ne $code -and $code -ne 0 -and $code -ne 3010) {
        Write-Error "Developer Pack installer exited with code $code. Install manually: $Fwlink"
    }
    if ($code -eq 3010) {
        Write-Host "Installer reported exit 3010 (success, reboot may be recommended). Waiting for reference assemblies..."
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$MetaProj = Join-Path $RepoRoot "tools\gta-toolkit\Tools\MetaTool\MetaTool.csproj"
$ToolkitSln = Join-Path $RepoRoot "tools\gta-toolkit\Toolkit.sln"

$mustRebuild = $Force -or ($env:GTA_CLOTHES_FORCE_META_TOOL_REBUILD -eq "1")

function Get-ExistingMetaToolExePath {
    param([string]$Root)
    $candidates = @(
        (Join-Path $Root "tools\MetaTool\bin\Release\MetaTool.exe")
        (Join-Path $Root "tools\MetaTool\bin\Debug\MetaTool.exe")
        (Join-Path $Root "tools\gta-toolkit\Tools\MetaTool\bin\Release\MetaTool.exe")
        (Join-Path $Root "tools\gta-toolkit\Tools\MetaTool\bin\Debug\MetaTool.exe")
        (Join-Path $Root "tools\metatool\MetaTool.exe")
    )
    foreach ($p in $candidates) {
        if (Test-PathFile $p) {
            return $p
        }
    }
    return $null
}

# Уже есть готовый exe (часто кладут только в Debug или в tools\metatool\) — не гоняем MSBuild.
if (-not $mustRebuild) {
    foreach ($envKey in @("GTA_CLOTHES_META_TOOL", "META_TOOL_EXE")) {
        $ev = $null
        foreach ($scope in @(
                [EnvironmentVariableTarget]::Process,
                [EnvironmentVariableTarget]::User,
                [EnvironmentVariableTarget]::Machine)) {
            $ev = [Environment]::GetEnvironmentVariable($envKey, $scope)
            if ($ev) { break }
        }
        $ev = if ($ev) { $ev.Trim() } else { "" }
        if ($ev -and (Test-PathFile $ev)) {
            Write-Host "MetaTool already specified ($envKey). Skipping MSBuild."
            Write-Host "OK: $ev"
            Write-Host "To rebuild: -Force or `$env:GTA_CLOTHES_FORCE_META_TOOL_REBUILD=1"
            exit 0
        }
    }
    $found = Get-ExistingMetaToolExePath -Root $RepoRoot
    if ($null -ne $found) {
        Write-Host "MetaTool already present. Skipping MSBuild (and .NET 4.7.2 install if not needed)."
        Write-Host "OK: $found"
        Write-Host "Tip: Release is preferred for PyInstaller; copy bin\Release or full output here. To rebuild: -Force"
        exit 0
    }
}

if (-not (Test-Path -LiteralPath $MetaProj)) {
    Write-Error "Not found: $MetaProj. Run: git submodule update --init --recursive (or place MetaTool under tools\MetaTool\bin\Release and skip MSBuild)."
}

$ReleaseExe = Join-Path $RepoRoot "tools\gta-toolkit\Tools\MetaTool\bin\Release\MetaTool.exe"

$Skip = $SkipNet472Install -or ($env:GTA_CLOTHES_SKIP_NET472_INSTALL -eq "1")
if (-not $Skip) {
    if (-not (Test-Net472DeveloperPack)) {
        Install-Net472DeveloperPack
        if (-not (Wait-Net472ReferenceAssemblies -TimeoutSec 180)) {
            Write-Error @"
Reference assemblies for .NET Framework 4.7.2 are still missing after the installer finished.
The NDP472 wrapper often exits before msiexec finishes — this script now waits up to 3 minutes.
If UAC succeeded: run this script again; or reboot (especially if the installer needed a restart); or install the Developer Pack manually:
  https://go.microsoft.com/fwlink/?linkid=874338
Or run PowerShell as Administrator once so the installer does not use a separate elevated process.
"@
        }
        Write-Host "OK: .NET Framework 4.7.2 targeting pack detected."
    }
} else {
    Write-Host "Skipping automatic .NET 4.7.2 Developer Pack install (-SkipNet472Install or GTA_CLOTHES_SKIP_NET472_INSTALL=1)."
}

$Msbuild = $null
$Vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $Vswhere) {
    $Msbuild = & $Vswhere -latest -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" 2>$null | Select-Object -First 1
}
if (-not $Msbuild -or -not (Test-Path $Msbuild)) {
    $Fallback = @(
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
        "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
    )
    foreach ($f in $Fallback) {
        if (Test-Path $f) { $Msbuild = $f; break }
    }
}
if (-not $Msbuild -or -not (Test-Path $Msbuild)) {
    Write-Error "MSBuild not found. Install Visual Studio Build Tools or MSBuild."
}

Write-Host "MSBuild: $Msbuild"
Write-Host "Building MetaTool + dependencies (Release)..."
# Собираем через Toolkit.sln с платформой «Any CPU»: при прямом MetaTool.csproj MSBuild
# подсовывает DirectXTex.vcxproj Release|Win32 → MSB8013 (в проекте только Debug|x64 / Release|x64).
if (Test-Path -LiteralPath $ToolkitSln) {
    & $Msbuild $ToolkitSln /t:MetaTool /p:Configuration=Release /p:Platform="Any CPU" /m /v:m /restore
} else {
    & $Msbuild $MetaProj /p:Configuration=Release /p:Platform=AnyCPU /m /v:m /restore
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path $ReleaseExe) {
    Write-Host "OK: $ReleaseExe"
} else {
    Write-Warning "Expected $ReleaseExe - check project output path."
}
