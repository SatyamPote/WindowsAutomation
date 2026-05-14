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
$mpvExe = Join-Path -Path $binDir -ChildPath "mpv.exe"
# Check if it's in the old subfolder and move it if found
$oldMpvDir = Join-Path -Path $binDir -ChildPath "mpv"
$oldMpvExe = Join-Path -Path $oldMpvDir -ChildPath "mpv.exe"
if (Test-Path $oldMpvExe) {
    Log "Found MPV in subfolder, moving to bin root..."
    Move-Item -Path $oldMpvExe -Destination $mpvExe -Force
}

if (-not (Test-Path $mpvExe)) {
    $retries = 2
    while ($retries -ge 0) {
        try {
            Log "Downloading MPV (discovering via GitHub API)..."
            $apiUrl = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
            $release = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing
            $asset = $release.assets | Where-Object { $_.name -match "mpv-x86_64-.*\.7z" -and $_.name -notmatch "v3" -and $_.name -notmatch "dev" } | Select-Object -First 1
            if (-not $asset) { throw "Could not find MPV asset in GitHub release" }
            
            $mpvUrl = $asset.browser_download_url
            $archivePath = "$env:TEMP\mpv.7z"
            Log "Downloading: $($asset.name)"
            # Use curl.exe for better reliability with large GitHub files
            curl.exe -L $mpvUrl -o $archivePath

            Log "Downloading 7zr.exe for extraction..."
            $7zrPath = "$env:TEMP\7zr.exe"
            Invoke-WebRequest -Uri "https://www.7-zip.org/a/7zr.exe" -OutFile $7zrPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop

            Log "Extracting MPV..."
            # Extract directly to bin directory (e = extract flat)
            $process = Start-Process -FilePath $7zrPath -ArgumentList "e `"$archivePath`" -o`"$binDir`" -y" -Wait -PassThru
            
            # Final check/move in case it's nested (though 'e' should prevent this)
            $extracted = Get-ChildItem -Path $binDir -Filter "mpv.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($extracted -and ($extracted.FullName -ne $mpvExe)) {
                Move-Item -Path $extracted.FullName -Destination $mpvExe -Force
            }
            
            Remove-Item $archivePath -Force -ErrorAction SilentlyContinue
            Remove-Item $7zrPath -Force -ErrorAction SilentlyContinue
            
            if (Test-Path $mpvExe) {
                Log "MPV installed successfully to $mpvExe"
                # Cleanup empty mpv dir if it exists
                if (Test-Path $oldMpvDir) {
                    if ((Get-ChildItem $oldMpvDir).Count -eq 0) { Remove-Item $oldMpvDir -Force }
                }
                break
            } else {
                throw "Extraction failed: mpv.exe not found in $binDir"
            }
        } catch {
            Log "Error: $_"
            $retries--
            if ($retries -ge 0) { Log "Retrying MPV download... ($retries left)" }
        }
    }
} else {
    Log "MPV already installed."
}
