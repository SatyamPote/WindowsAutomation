$logFile = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

$binDir = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "bin"
if (-not (Test-Path $binDir)) { New-Item -ItemType Directory -Force -Path $binDir | Out-Null }

# yt-dlp
$ytdlpExe = Join-Path -Path $binDir -ChildPath "yt-dlp.exe"
if (-not (Test-Path $ytdlpExe)) {
    $retries = 2
    while ($retries -ge 0) {
        try {
            Log "Downloading yt-dlp..."
            Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile $ytdlpExe -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
            Log "yt-dlp downloaded successfully."
            break
        } catch {
            Log "Error: $_"
            $retries--
            if ($retries -ge 0) { Log "Retrying yt-dlp download... ($retries left)" }
        }
    }
} else {
    Log "yt-dlp already installed."
}

# mpv
$mpvDir = Join-Path -Path $binDir -ChildPath "mpv"
$mpvExe = Join-Path -Path $mpvDir -ChildPath "mpv.exe"
if (-not (Test-Path $mpvExe)) {
    $retries = 2
    while ($retries -ge 0) {
        try {
            Log "Downloading MPV..."
            if (-not (Test-Path $mpvDir)) { New-Item -ItemType Directory -Force -Path $mpvDir | Out-Null }
            
            $mpvUrl = "https://sourceforge.net/projects/mpv-player-windows/files/64bit/mpv-x86_64-20231210-git-b77c8e9.7z/download"
            $archivePath = "$env:TEMP\mpv.7z"
            Invoke-WebRequest -Uri $mpvUrl -OutFile $archivePath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop

            Log "Downloading 7zr.exe for extraction..."
            $7zrPath = "$env:TEMP\7zr.exe"
            Invoke-WebRequest -Uri "https://www.7-zip.org/a/7zr.exe" -OutFile $7zrPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop

            Log "Extracting MPV..."
            $process = Start-Process -FilePath $7zrPath -ArgumentList "x `"$archivePath`" -o`"$mpvDir`" -y" -Wait -PassThru
            
            Remove-Item $archivePath -Force -ErrorAction SilentlyContinue
            Remove-Item $7zrPath -Force -ErrorAction SilentlyContinue
            Log "MPV installed successfully."
            break
        } catch {
            Log "Error: $_"
            $retries--
            if ($retries -ge 0) { Log "Retrying MPV download... ($retries left)" }
        }
    }
} else {
    Log "MPV already installed."
}
