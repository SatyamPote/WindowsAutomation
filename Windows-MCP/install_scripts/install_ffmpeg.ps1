$logFile = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

$binDir = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "bin"
if (-not (Test-Path $binDir)) { New-Item -ItemType Directory -Force -Path $binDir | Out-Null }

$ffmpegExe = Join-Path -Path $binDir -ChildPath "ffmpeg.exe"
if (Test-Path $ffmpegExe) {
    Log "FFmpeg is already installed."
    exit 0
}

$retries = 2
while ($retries -ge 0) {
    try {
        Log "Downloading FFmpeg..."
        $zipPath = "$env:TEMP\ffmpeg.zip"
        Invoke-WebRequest -Uri "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -OutFile $zipPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
        
        Log "Extracting FFmpeg..."
        Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\ffmpeg_extracted" -Force
        
        $extractedFolder = Get-ChildItem -Path "$env:TEMP\ffmpeg_extracted" | Select-Object -First 1
        Copy-Item -Path "$($extractedFolder.FullName)\bin\ffmpeg.exe" -Destination $binDir -Force
        Copy-Item -Path "$($extractedFolder.FullName)\bin\ffprobe.exe" -Destination $binDir -Force
        
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
        Remove-Item "$env:TEMP\ffmpeg_extracted" -Recurse -Force -ErrorAction SilentlyContinue
        Log "FFmpeg installed to bin directory."
        break
    } catch {
        Log "Error: $_"
        $retries--
        if ($retries -ge 0) { Log "Retrying FFmpeg install... ($retries left)" }
        Start-Sleep -Seconds 2
    }
}
