param (
    [string]$ModelName = ""
)

$logFile = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

if ($ModelName -eq "" -or $ModelName -eq "skip") {
    Log "Model download skipped by user."
    exit 0
}

# Ensure Path is updated (Ollama was just installed)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# ---------------------------------------------------------------------------
# 1. Connect to Ollama Service
# ---------------------------------------------------------------------------
Log "Connecting to Ollama service..."
$connRetries = 3
$connected = $false

while ($connRetries -gt 0) {
    try {
        $ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
        if (-not $ollamaProcess) {
            Log "Starting Ollama service in background..."
            Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 5
        }
        
        # Test connection
        $test = & ollama list 2>&1
        if ($LASTEXITCODE -eq 0 -or $test -match "NAME") {
            Log "Ollama detected and responding."
            $connected = $true
            break
        }
    } catch {
        Log "Ollama not responding -> retrying..."
    }
    
    $connRetries--
    if ($connRetries -gt 0) { 
        Log "Retrying connection to Ollama... ($connRetries left)"
        Start-Sleep -Seconds 3
    }
}

if (-not $connected) {
    Log "FATAL: Could not connect to Ollama service after multiple attempts."
    exit 1
}

# ---------------------------------------------------------------------------
# 2. Download Model
# ---------------------------------------------------------------------------
$downloadRetries = 2
$success = $false

while ($downloadRetries -ge 0) {
    try {
        Log "Downloading AI model: $ModelName (Streaming output...)"
        Log "--------------------------------------------------------"
        # We use Start-Process to capture the stream effectively if needed, 
        # but the user requested piping directly. 
        # Note: 'ollama pull' output contains carriage returns for progress bars.
        & ollama pull $ModelName 2>&1 | Tee-Object -FilePath $logFile -Append
        Log "--------------------------------------------------------"
        
        # ---------------------------------------------------------------------------
        # 3. Verify Model
        # ---------------------------------------------------------------------------
        Log "Verifying model $ModelName..."
        $list = & ollama list 2>&1
        if ($list -match $ModelName) {
            Log "Model $ModelName installed successfully and verified."
            $success = $true
            break
        } else {
            throw "Verification failed: Model $ModelName not found in 'ollama list'."
        }
    } catch {
        Log "Error during model download: $_"
        $downloadRetries--
        if ($downloadRetries -ge 0) {
            Log "Retrying download... ($downloadRetries attempts left)"
            Start-Sleep -Seconds 5
        }
    }
}

if ($success) {
    exit 0
} else {
    Log "Model download failed. You can retry later by running 'ollama pull $ModelName' in a terminal."
    exit 1 
}
