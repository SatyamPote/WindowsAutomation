param (
    [string]$ModelName = ""
)

$logFile = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

if ($ModelName -eq "" -or $ModelName -eq "skip") {
    Log "Model download skipped by user."
    exit 0
}

Log "Setting up to download AI model: $ModelName"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Log "Starting Ollama service temporarily in background..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

$retries = 2
while ($retries -ge 0) {
    try {
        Log "Pulling model $ModelName... (This may take several minutes depending on your internet connection)"
        & ollama pull $ModelName 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
        
        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
            Log "Model $ModelName downloaded successfully to the default Ollama directory."
            break
        } else {
            throw "Ollama pull failed with exit code $LASTEXITCODE"
        }
    } catch {
        Log "Error: $_"
        $retries--
        if ($retries -ge 0) { Log "Retrying model download... ($retries left)" }
        Start-Sleep -Seconds 5
    }
}
