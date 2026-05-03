$logFile = Join-Path (Split-Path $PSScriptRoot -Parent) "logs\install.log"
function Log { param([string]$msg) Write-Output "[$((Get-Date).ToString('HH:mm:ss'))] $msg" | Tee-Object -FilePath $logFile -Append }

param(
    [string]$AppDir
)

Log "Adding Windows Defender Exclusions for Lotus..."

try {
    $programDataLotus = Join-Path $env:ProgramData "Lotus"
    
    # Exclude both the App installation directory and the ProgramData directory
    Add-MpPreference -ExclusionPath $AppDir, $programDataLotus -ErrorAction Stop
    Log "Successfully added Windows Defender exclusions for:"
    Log " - $AppDir"
    Log " - $programDataLotus"
} catch {
    Log "WARNING: Failed to add Windows Defender exclusions. You may need to do this manually."
    Log "Error details: $_"
}
