$logFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\install.log"
function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Output $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
$reqPath = Join-Path (Split-Path $PSScriptRoot -Parent) "requirements.txt"

if (-not (Test-Path $reqPath)) {
    Log "WARN: requirements.txt not found! Skipping."
    exit 0
}

Log "Checking PIP availability..."
& python -m pip --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Log "WARN: pip not found. Attempting to install via ensurepip..."
    & python -m ensurepip --upgrade 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log "UPGRADING: PIP to latest version..."
& python -m pip install --upgrade pip 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8

$retries = 2
while ($retries -ge 0) {
    try {
        Log "INSTALLING: Python packages from requirements.txt (This will skip already installed packages)..."
        & python -m pip install -r "$reqPath" 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) { throw "Pip returned exit code $LASTEXITCODE" }
        
        Log "SUCCESS: Python requirements installed."
        break
    } catch {
        Log "ERROR: pip install failed - $_"
        $retries--
        if ($retries -ge 0) { Log "RETRYING: Python requirements ($retries left)..."; Start-Sleep -Seconds 2 }
        else { Log "WARN: Failed to install all python requirements."; exit 1 }
    }
}
