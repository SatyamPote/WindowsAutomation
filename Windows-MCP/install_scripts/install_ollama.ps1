$logFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Detection
function Check-Ollama {
    try {
        $ver = & ollama --version 2>$null
        return ($LASTEXITCODE -eq 0 -and $ver)
    } catch { return $false }
}

if (Check-Ollama) {
    Log "SKIP: Ollama already installed and responding."
    exit 0
}

Log "Installing Ollama (Critical Component)..."
$installerPath = "$env:TEMP\OllamaSetup.exe"

for ($attempt=1; $attempt -le 3; $attempt++) {
    try {
        Log "Downloading OllamaSetup.exe (Attempt $attempt/3)..."
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
        
        Log "Running Ollama installer silently..."
        $process = Start-Process -FilePath $installerPath -ArgumentList "/SILENT" -Wait -PassThru
        
        Log "Waiting 5 seconds for service initialization..."
        Start-Sleep -Seconds 5
        
        if (Check-Ollama) {
            Log "SUCCESS: Ollama installed and verified."
            Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
            exit 0
        } else {
            Log "WARNING: Ollama installed but not responding to command line yet."
        }
    } catch {
        Log "ERROR: $_"
    }
}

Log "FATAL: Ollama failed to install or start after multiple attempts."
exit 1
