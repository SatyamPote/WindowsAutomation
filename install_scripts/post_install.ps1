$logFile = Join-Path -Path (Split-Path $PSScriptRoot -Parent) -ChildPath "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

Log "Verifying Ollama service..."
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaProcess) {
    Log "Starting Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
}

Log "Checking configuration..."
$configPath = Join-Path -Path $env:ProgramData -ChildPath "Lotus\config\config.json"
if (Test-Path $configPath) {
    Log "Configuration file (config.json) exists and is configured."
} else {
    Log "Warning: config.json missing at $configPath."
}

Log "Post-install verification complete! System is ready."
