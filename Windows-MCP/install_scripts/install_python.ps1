$logFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\install.log"
function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Output $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

$resultsFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\system_check.json"
$results = @{}
if (Test-Path $resultsFile) { $results = Get-Content $resultsFile | ConvertFrom-Json }

if ($results.python_ok) {
    Log "SKIP: Python already installed ($($results.python_version)) and meets requirement."
    exit 0
}

$retries = 2
while ($retries -ge 0) {
    try {
        Log "DOWNLOADING: Python 3.11.9 installer..."
        $installerPath = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installerPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
        
        Log "INSTALLING: Python 3.11.9 silently. Please wait..."
        $process = Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait -PassThru
        Log "INSTALL: Python finished with exit code $($process.ExitCode)."
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Log "SUCCESS: Python 3.11 installed."
        break
    } catch {
        Log "ERROR: $_"
        $retries--
        if ($retries -ge 0) { Log "RETRYING: Python install ($retries left)..."; Start-Sleep -Seconds 2 }
        else { Log "FATAL: Python installation failed after all retries."; exit 1 }
    }
}
