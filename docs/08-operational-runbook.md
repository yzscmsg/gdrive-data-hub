# 08 — Operational Runbook

## 1. Routine Operational Commands

### 1.1 Ingestion Runs
```bash
# Scan and catalog the primary Synology DS220+ Document NAS
gdrive-hub scan --path "/mnt/nas_synology/data" --origin "LAN_SYNOLOGY"

# Scan the TrueNAS Media NAS
gdrive-hub scan --path "/mnt/truenas_167/Share" --origin "LAN_TRUENAS_167"

# Scan Dropbox local sync folder
gdrive-hub scan --path "/home/user/Dropbox" --origin "DROPBOX"

# Scan iCloud Photos folder
gdrive-hub scan --path "/data/icloud_photos" --origin "ICLOUD"
```

### 1.2 Deduplication & Canonical Assignment
```bash
# Analyze duplicates and resolve canonical primary sources
gdrive-hub dedup --resolve
```

### 1.3 Reverse Redistribution (Weekly)
```bash
# Compute and review redistribution tasks for LAN NAS nodes
gdrive-hub redistribute --plan-only
```

### 1.4 Generating Indexes & Dashboard
```bash
# Refresh INDEX.md and static HTML dashboard
gdrive-hub index --out-md "INDEX.md" --out-html "dashboard.html"
```

### 1.5 Historical Document Verification
```bash
# Cross-reference a candidate document against verified historical baselines
gdrive-hub verify --input "new_supplier_contract_2026.pdf"
```

### 1.6 Starting the Management Portal
```bash
# Start web portal on port 8080
gdrive-hub portal --host 0.0.0.0 --port 8080
```

---

## 2. Monthly Disaster Recovery Drill

Every 30 days, verify end-to-end recovery:
1. Select 1 business folder (`01_BUSINESS/Accounting_Finance`), 1 family document, and 1 photo from Google Drive.
2. Download via rclone to an isolated scratch path: `rclone copy "gdrive:01_BUSINESS/Accounting_Finance" /tmp/restore_drill`.
3. Compute local SHA-256 and assert bit-for-bit identity against `catalog.db`:
   `sqlite3 data/catalog.db "SELECT sha256 FROM files WHERE canonical_gdrive_path LIKE '01_BUSINESS/Accounting_Finance/%'"`
4. Log the restore drill result in `job_runs`.
