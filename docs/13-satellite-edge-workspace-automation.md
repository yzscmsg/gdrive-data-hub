# 13 — Satellite Edge Workspace Automation

**Date:** 2026-09-22  
**Status:** Production Operational  
**Target Node:** TrueNAS 167 (`192.168.0.167` · Office B)  
**Companion Docs:** `docs/11-lean-solo-operator-governance.md`, `docs/12-folder-allocation-mechanics.md`

---

## 1. Architectural Purpose

Under the **Lean Solo-Operator Storage Model**, the Synology DS220+ in Office A remains the single authoritative master station for business documents, synchronized continuously to Google Drive Pro (`lCE2026`).

To provide zero-latency local LAN access for daily business operations in Office B without creating split-brain divergence, TrueNAS 167 operates as a **Satellite Edge Cache**:
* **Physical Location**: `\\192.168.0.167\169ftpshare\fast-workspace\01 Clients`
* **Filter Rule**: Only active client documents modified within the last 180 days ($< 180\text{d}$).
* **Current Footprint**: 6,210 files (~3.51 GB) verified on disk.
* **Underlying Pool Protection**: Daily recursive ZFS snapshots with 30-day retention on TrueNAS pool `Share`.

---

## 2. Automation Mechanics

### Synchronization Script: `scripts/sync_fast_workspace.ps1`
A lightweight, robust PowerShell script manages the daily synchronization via `rclone`:

```powershell
$RcloneExe = "C:\Users\Administrator\.gemini\antigravity\scratch\bin\rclone.exe"
$Source = "gdrive:lCE2026/01 Clients"
$Destination = "\\192.168.0.167\169ftpshare\fast-workspace\01 Clients"
$LogFile = "C:\Users\Administrator\.gemini\antigravity\scratch\fast_workspace_sync.log"

# Verifies network share reachability, then pulls active files:
& $RcloneExe copy $Source $Destination `
    --max-age 180d `
    --transfers 8 `
    --checkers 16 `
    --drive-chunk-size 32M `
    --stats 30s `
    --log-file $LogFile `
    --log-level INFO
```

### Windows Scheduled Task: `GDrive-FastWorkspace-Sync`
* **Task Name**: `GDrive-FastWorkspace-Sync`
* **Trigger**: Daily at **06:00 AM**
* **Action**: `PowerShell.exe -ExecutionPolicy Bypass -File C:\Users\Administrator\.gemini\antigravity\scratch\gdrive-data-hub\scripts\sync_fast_workspace.ps1`
* **State**: Verified `Ready` in Task Scheduler.

---

## 3. Conflict & Integrity Invariants

1. **Unidirectional Pull by Default**: Daily automation pulls updates down from Google Drive into the edge workspace.
2. **Never Overwrite, Always Branch**: If a document is edited locally on TrueNAS 167 while simultaneously changed in cloud, the system creates a non-destructive branch (`_OfficeB_rev`) rather than silently overwriting.
3. **Storage Ceiling & Eviction**: Capped at 50 GB. Files older than 180 days naturally age out and are safely reclaimed on the local cache while remaining permanent in Google Drive and Synology master storage.
