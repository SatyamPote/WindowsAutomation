param(
    [string]$OutFile = ""
)

if ([string]::IsNullOrWhiteSpace($OutFile)) { exit 1 }

# Refresh PATH so ollama is found
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

# Remove old results file
if (Test-Path $OutFile) { Remove-Item $OutFile -Force }

try {
    $ver = & ollama --version 2>&1
    if ($LASTEXITCODE -ne 0) { exit 1 }

    $list = & ollama list 2>&1
    if ($LASTEXITCODE -ne 0) { exit 1 }

    $lines  = $list -split "`r?`n"
    $models = @()

    foreach ($line in $lines) {
        $line = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($line))  { continue }
        if ($line -match "^NAME")                  { continue }
        $parts = $line -split "\s+"
        if ($parts.Count -gt 0 -and $parts[0] -ne "") {
            $models += $parts[0]
        }
    }

    if ($models.Count -gt 0) {
        $models | Out-File -FilePath $OutFile -Encoding UTF8
        exit 0
    }

    exit 2   # Ollama OK but no models installed
} catch {
    exit 1
}
