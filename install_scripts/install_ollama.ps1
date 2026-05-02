$logFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\install.log"
function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Output $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

$resultsFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\system_check.json"
$results = @{}
if (Test-Path $resultsFile) { $results = Get-Content $resultsFile | ConvertFrom-Json }

if ($results.ollama_ok) {
    Log "SKIP: Ollama already installed ($($results.ollama_version))."
    exit 0
}

Log "PRIORITY: Installing Ollama (Critical Component)."
$retries = 2
while ($retries -ge 0) {
    try {
        Log "DOWNLOADING: OllamaSetup.exe..."
        $installerPath = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath -UseBasicParsing -TimeoutSec 600 -ErrorAction Stop
        
        Log "INSTALLING: Ollama silently. Please wait..."
        $process = Start-Process -FilePath $installerPath -ArgumentList "/SILENT" -Wait -PassThru
        Log "INSTALL: Ollama finished with exit code $($process.ExitCode)."
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Verify it works
        Log "VERIFY: Waiting for Ollama service to start..."
        Start-Sleep -Seconds 5
        $ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
        if (-not $ollamaProcess) {
            Log "VERIFY: Starting Ollama service manually..."
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 5
        }
        
        $verify = & ollama list 2>&1
        if ($LASTEXITCODE -eq 0 -or $verify -match "NAME") {
            Log "SUCCESS: Ollama installed and verified running."
            break
        } else {
            throw "Ollama command failed to run properly."
        }
    } catch {
        Log "ERROR: $_"
        $retries--
        if ($retries -ge 0) { Log "RETRYING: Ollama install ($retries left)..."; Start-Sleep -Seconds 3 }
        else { Log "FATAL: Ollama installation failed. The system requires Ollama."; exit 1 }
    }
}
