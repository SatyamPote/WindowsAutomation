# build_installer.ps1
# Compiles installer.iss with Inno Setup → installer_output/LotusSetup.exe
# Used by GitHub Actions and locally on Windows dev machines.

[CmdletBinding()]
param(
    [string]$IssFile = "installer.iss",
    [string]$OutDir  = "installer_output"
)

$ErrorActionPreference = "Stop"
Write-Host "[build_installer] Starting Inno Setup compile..." -ForegroundColor Cyan

# Resolve repo root (parent of scripts/) and run from there
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
Write-Host "[build_installer] Working dir: $repoRoot"

if (-not (Test-Path $IssFile)) {
    throw "Cannot find $IssFile in $repoRoot"
}

# Locate ISCC.exe (Inno Setup compiler)
$candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe"
)

$iscc = $null
foreach ($c in $candidates) {
    if ($c -and (Test-Path $c)) { $iscc = $c; break }
}

if (-not $iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}

if (-not $iscc) {
    throw "Inno Setup (ISCC.exe) not found. Install via: choco install innosetup -y"
}
Write-Host "[build_installer] Using compiler: $iscc"

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

# Pre-flight: confirm PyInstaller outputs exist
foreach ($exe in @("dist\Lotus.exe", "dist\LotusTray.exe")) {
    if (-not (Test-Path $exe)) {
        throw "Missing $exe - run build.bat first."
    }
}

& $iscc "/Q" "/O$OutDir" $IssFile
if ($LASTEXITCODE -ne 0) {
    throw "ISCC.exe exited with code $LASTEXITCODE"
}

$setup = Join-Path $OutDir "LotusSetup.exe"
if (-not (Test-Path $setup)) {
    # Inno may name output by AppName/AppVersion — pick newest .exe
    $newest = Get-ChildItem $OutDir -Filter *.exe | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newest) {
        Rename-Item $newest.FullName "LotusSetup.exe"
        $setup = Join-Path $OutDir "LotusSetup.exe"
    }
}

if (-not (Test-Path $setup)) {
    throw "LotusSetup.exe was not produced."
}

$size = "{0:N1} MB" -f ((Get-Item $setup).Length / 1MB)
Write-Host "[build_installer] ✅ Built $setup ($size)" -ForegroundColor Green
