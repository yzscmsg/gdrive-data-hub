# 09 — Risk Analysis & Mitigation Matrix

## 1. Risk Register

| Risk ID | Risk Scenario | Impact | Severity | Engineering Mitigation |
|---|---|---|:---:|---|
| **RSK-01** | **Google Drive Daily Upload Limits**: Google enforces a ~750 GB/day upload quota per account. | Bulk synchronization jobs freeze or throw HTTP 403 rate-limit errors. | **Medium** | Staged wave uploads capped at $\le 500\text{ GB/day}$; rclone exponential backoff and retry mechanisms. |
| **RSK-02** | **Silent Document Mutation**: Google Drive auto-converts `.docx` or `.xlsx` into Google Docs format. | File binary hashes change; data integrity verification fails. | **High** | Forced binary upload via `--drive-import-formats=false` flag in sync engine. |
| **RSK-03** | **iCloud 2FA Session Expiration**: Apple ID authentication cookies expire every 30–90 days. | Background iCloud photo ingest fails silently. | **Medium** | Dedicated session health check daemon in `hub/sources/icloud.py` alerting the portal when re-auth is needed. |
| **RSK-04** | **Bidirectional Sync Race Condition**: A file is edited concurrently on LAN NAS and Google Drive. | Silent overwrite or data loss under naive "last write wins" sync. | **High** | **"Never Overwrite, Always Branch"** protocol: branches into `<file>_lan_<ts>` and `<file>_gdrive_<ts>`, records version lineage in `catalog.db`, and alerts in portal. |
| **RSK-05** | **Storage Quota Drift**: Accumulation of raw 4K video, downloads, and unpruned snapshots pushes usage past 5 TB. | Cloud storage fills up; email and cloud services locked. | **Medium** | Automated portal alarms at **75% (3.75 TB)** and **85% (4.25 TB)**; monthly audit recommending eviction candidates to LAN-only storage. |
| **RSK-06** | **Office WAN Uplink Saturation**: Daytime large-file sync consumes all outbound internet bandwidth. | Degrades office video calls, VoIP, and ERP responsiveness. | **Medium** | Time-aware bandwidth scheduler: $5\text{ MB/s}$ during work hours (08:00–19:00), uncapped ($50\text{ MB/s}$) off-peak. |
| **RSK-07** | **Bit Rot & Transfer Corruption**: Silent bit flips during transmission across VPN or network links. | Corrupted copies stored in cloud. | **High** | End-to-end cryptographic checksum verification: verifies Google Drive MD5 against pre-upload SHA-256 before marking synced. |
