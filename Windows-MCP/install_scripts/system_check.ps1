param([string]$LogFile = "")

if ($LogFile -eq "") {
    $LogFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\install.log"
}

function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Output $line | Out-File -FilePath $LogFile -Append -Encoding utf8
}

$resultsFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\system_check.json"

$results = @{
    python_ok      = $false
    python_version = ""
    pip_ok         = $false
    ollama_ok      = $false
    ollama_version = ""
    ffmpeg_ok      = $false
    ytdlp_ok       = $false
    mpv_ok         = $false
    is_admin       = $false
    has_internet   = $false
    disk_gb_free   = 0
}

# Admin check
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]$identity
$results.is_admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($results.is_admin) { Log "ADMIN: Running as administrator." }
else { Log "WARN: Not running as administrator." }

# Internet check
try {
    $null = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
    $results.has_internet = $true
    Log "INTERNET: Connection OK."
} catch {
    $results.has_internet = $false
    Log "WARN: No internet connection detected."
}

# Disk space
$drive = (Get-Item $env:SystemDrive).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB, 2)
$results.disk_gb_free = $freeGB
if ($freeGB -lt 10) { Log "WARN: Low disk space: ${freeGB} GB free. Recommend 10GB+." }
else { Log "DISK: ${freeGB} GB free - OK." }

# Python
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        $results.python_version = "$major.$minor"
        if ($major -ge 3 -and $minor -ge 11) {
            $results.python_ok = $true
            Log "PYTHON: Found $pyVer - OK (>= 3.11)."
        } else {
            Log "PYTHON: Found $pyVer but needs upgrade to 3.11+."
        }
    }
} catch { Log "PYTHON: Not found." }

# pip
try {
    $null = & python -m pip --version 2>&1
    if ($LASTEXITCODE -eq 0) { $results.pip_ok = $true; Log "PIP: Found - OK." }
} catch { Log "PIP: Not found." }

# Ollama
try {
    $ollamaVer = & ollama --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $results.ollama_ok = $true
        $results.ollama_version = "$ollamaVer"
        Log "OLLAMA: Found $ollamaVer - OK."
    }
} catch { Log "OLLAMA: Not found." }

# FFmpeg (PATH or bin dir)
$binDir = Join-Path (Split-Path $PSScriptRoot -Parent) "bin"
$ffmpegBin = Join-Path $binDir "ffmpeg.exe"
if ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -or (Test-Path $ffmpegBin)) {
    $results.ffmpeg_ok = $true
    Log "FFMPEG: Found - OK."
} else { Log "FFMPEG: Not found." }

# yt-dlp
$ytdlpExe = Join-Path $binDir "yt-dlp.exe"
if (Test-Path $ytdlpExe) {
    $results.ytdlp_ok = $true
    Log "YT-DLP: Found at $ytdlpExe - OK."
} else { Log "YT-DLP: Not found." }

# mpv
$mpvExe = Join-Path $binDir "mpv\mpv.exe"
if (Test-Path $mpvExe) {
    $results.mpv_ok = $true
    Log "MPV: Found at $mpvExe - OK."
} else { Log "MPV: Not found." }

# Write results
$results | ConvertTo-Json | Out-File -FilePath $resultsFile -Encoding utf8
Log "SYSCHECK: Complete. Results written to $resultsFile"
