# ==============================================================================
# sync_fast_workspace.ps1
# Automated Daily Synchronization for TrueNAS 167 Satellite Edge Cache
# Source: Google Drive lCE2026/01 Clients (<180 days modified)
# Target: \\192.168.0.167\169ftpshare\fast-workspace\01 Clients
# ==============================================================================

$RcloneExe = "C:\Users\Administrator\.gemini\antigravity\scratch\bin\rclone.exe"
$Source = "gdrive:lCE2026/01 Clients"
$Destination = "\\192.168.0.167\169ftpshare\fast-workspace\01 Clients"
$LogFile = "C:\Users\Administrator\.gemini\antigravity\scratch\fast_workspace_sync.log"

Write-Output "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Fast-Workspace Sync..."

# Verify share accessibility
if (-not (Test-Path "\\192.168.0.167\169ftpshare\fast-workspace")) {
    Write-Error "[ERROR] Satellite cache destination \\192.168.0.167\169ftpshare\fast-workspace is unreachable!"
    exit 1
}

# Execute rclone copy with 180-day filter
& $RcloneExe copy $Source $Destination `
    --max-age 180d `
    --transfers 8 `
    --checkers 16 `
    --drive-chunk-size 32M `
    --stats 30s `
    --log-file $LogFile `
    --log-level INFO

if ($LASTEXITCODE -eq 0) {
    Write-Output "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Fast-Workspace Sync completed successfully."
} else {
    Write-Error "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Fast-Workspace Sync failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}
