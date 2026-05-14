param(
    [string]$ModelName = ""
)

# ── Paths ──
$LogDir  = Join-Path $env:PROGRAMDATA "Lotus\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir "install.log"

function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# ── Guard ──
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

if ([string]::IsNullOrWhiteSpace($ModelName) -or $ModelName -eq "skip") {
    Log "SKIP: No model specified."
    exit 0
}

# ── Wait for Ollama to be ready ──
Log "Checking Ollama availability..."
$ready = $false
for ($i = 1; $i -le 6; $i++) {
    $test = & ollama list 2>&1
    if ($LASTEXITCODE -eq 0) {
        Log "Ollama is ready."
        $ready = $true
        break
    }
    Log "Ollama not responding (attempt $i/6). Waiting 5 seconds..."
    Start-Sleep -Seconds 5
}

if (-not $ready) {
    Log "ERROR: Ollama is not responding. Cannot download model."
    exit 1
}

# ── Pull model with retries ──
$shortName = ($ModelName -split ":")[0].Trim()   # strip :latest for matching
$success   = $false

for ($attempt = 1; $attempt -le 3; $attempt++) {
    Log "PULLING: $ModelName  (attempt $attempt / 3)"
    Log "----------------------------------------------------"

    # Capture stdout and stderr into temp files, then append to log
    $stdOut = "$env:TEMP\lotus_pull_out.txt"
    $stdErr = "$env:TEMP\lotus_pull_err.txt"

    $proc = Start-Process -FilePath "ollama" `
        -ArgumentList "pull", $ModelName `
        -NoNewWindow -PassThru `
        -RedirectStandardOutput $stdOut `
        -RedirectStandardError  $stdErr
    $proc.WaitForExit()

    foreach ($f in @($stdOut, $stdErr)) {
        if (Test-Path $f) {
            Get-Content $f | Add-Content -Path $LogFile -Encoding UTF8
        }
    }

    Log "----------------------------------------------------"
    Log "VERIFYING: running 'ollama list'..."

    $list = & ollama list 2>&1
    if ($list -match [regex]::Escape($shortName)) {
        Log "SUCCESS: $ModelName verified in 'ollama list'."
        $success = $true
        break
    }
    Log "WARNING: $ModelName not found after pull. Will retry."
}

if ($success) { exit 0 }
Log "FATAL: $ModelName download failed after all attempts."
exit 1
