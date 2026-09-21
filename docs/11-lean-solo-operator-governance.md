# 11 — Lean Solo-Operator Governance Model

**Date:** 2026-09-21  
**Status:** Approved & Active  
**Reference:** Aligned with `nas-arch/docs/07-lean-solo-operator-model.md` and `docs/08-solo-operator-execution-roadmap.md`

---

## 1. Governance Principles

This system is engineered for a **one-person company** requiring a rock-solid, zero-maintenance data governance model.
It rejects enterprise bureaucracy and focuses on **automated, set-and-forget primitives**:

1. **ZFS Periodic Snapshots** (Daily, 30-day retention) via TrueNAS GUI for bulletproof ransomware protection.
2. **Canonical Cloud Truth** in Google Drive Pro (5 TB) synchronized via `rclone`.
3. **7 Root Folder Archetypes** with path-based downward policy inheritance.
4. **Unidirectional Satellite Edge Cache** on TrueNAS 167 (`fast-workspace`) holding active T1 docs (<180d) and curated software tools.
5. **30-Day Auto-Quarantine** on `00_Inbox` to prevent stale dumping grounds.

---

## 2. The 7 Root Folder Archetypes

| Folder Prefix | Archetype | Tier | Authority Station | Edge Cache (167) | Sync Cadence | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `00_Inbox` | `QUARANTINE` | T2-temp | SHARED_DROPZONE | ❌ No | Hourly | Dropzone; items $> 30\text{d}$ auto-move to Quarantine |
| `01_Business` | `ACTIVE_WORKSPACE` | T1 | Synology Master | ✅ `< 180\text{d}` | Hourly | Core corporate, client files, and financial ledgers |
| `02_Projects` | `PROJECT_WORKSPACE` | T2 | Synology Master | ❌ No | Daily | Code repos, architectural specs, technical docs |
| `03_Software` | `TOOLCHAIN_CURATED` | T3 | Google Drive | ✅ Mirrored | Weekly | Curated utilities, OS images, and runtime installers |
| `04_Archive` | `COLD_ARCHIVE` | T3 | Synology Master | ❌ No | Monthly | Historical records, past clients (read-only) |
| `05_Media` | `MEDIA_VAULT` | T2 | TrueNAS 167 | TrueNAS 069 | Weekly | Photos on 167; Movies on 069 (IMDb $\ge 7.8$ to cloud) |
| `06_Platform` | `PLATFORM_DATA` | T1 | Local Host | ❌ No | Daily | Container volumes, app data, system configs |

---

## 3. Database Schema Implementation

The `catalog.db` database manages policies in the `folder_policies` table:

```sql
SELECT folder_prefix, archetype, tier, authority_node, replica_target, sync_frequency
FROM folder_policies;
```

Files inherit lifecycle, RPO, and replication rules based on the folder path prefix.

---

## 4. Conflict Resolution Strategy

- **Rule**: *"Never Overwrite, Always Branch"*
- If an Office B user edits a file directly on the TrueNAS 167 edge cache:
  1. The SHA-256 mismatch is detected during scan.
  2. The local edit is saved as `Filename_OfficeB_rev.ext` (or placed in `--backup-dir`).
  3. The conflict is recorded in `sync_conflicts` with `resolution = 'PENDING'`.
  4. The Management Portal (`http://localhost:8081`) displays a 1-click promotion button to merge back into Synology.
