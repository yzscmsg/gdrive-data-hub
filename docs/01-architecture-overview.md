# 01 — Architecture Overview

## 1. Executive Summary

`gdrive-data-hub` is a hybrid cloud and on-premises continuous data governance platform. It bridges the storage estates of Office A and Office B with a central 5 TB Google Drive Pro cloud hub.

Rather than treating the cloud transition as a one-off "lift-and-shift" migration, this platform establishes a living, bidirectional data lifecycle:
1. **Low-Latency Daily Operations**: Users continue to work primarily against local LAN NAS shares (Synology and TrueNAS).
2. **Central Canonical Ground Truth**: Google Drive maintains the authoritative, deduplicated, and cataloged file repository.
3. **Continuous Ingest & Redistribution Loop**:
   - **Nightly Ingest (LAN -> Cloud)**: Changed and new files stream to Google Drive; cryptographic checksums and lifecycle statuses are recorded in `catalog.db`.
   - **Weekly Reverse Redistribution (Cloud -> LAN)**: Remote and mobile uploads (e.g. smartphone photos, remote Dropbox docs) are automatically distributed down to their designated physical NAS nodes.
4. **AI Ground Truth**: Extracted text, keywords, financial/contract anchors, and summaries are cataloged to enable semantic querying and verification of incoming data against historical baselines.
5. **Interactive Management Portal**: A web-based control plane (`gdrive-hub-portal`) exposes operational telemetry, IMDb movie curation sliders, bandwidth scheduling, and conflict resolution tools.

---

## 2. Physical & Cloud Role Topology

```
┌────────────────────────┐      ┌────────────────────────┐
│   iCloud (Photos/Video)│      │    Dropbox (Documents) │
│   [Ingest-Only Source] │      │   [Ingest-Only Source] │
└───────────┬────────────┘      └───────────┬────────────┘
            │ (Read-Only)                   │ (Read-Only)
            └───────────────┬───────────────┘
                            ▼
      ┌────────────────────────────────────────────────────────┐
      │               Google Drive Pro (5 TB)                  │
      │           CENTRAL CANONICAL NERVOUS SYSTEM             │
      │                                                        │
      │  ├── 00_SYSTEM/ (catalog.db, AI Embeddings, Index)     │
      │  ├── 01_BUSINESS/        ├── 02_LIFEOS_FAMILY/         │
      │  ├── 03_PROJECTS_CODE/   ├── 04_KNOWLEDGE_BASE/        │
      │  ├── 05_SOFTWARE_TOOLS/  ├── 06_MEDIA/ (Curated IMDB)  │
      │  └── 07_ARCHIVE/                                       │
      └──────────────────────────┬─────────────────────────────┘
                                 │
           ┌─────────────────────┴─────────────────────┐
           │  Bidirectional Sync, Deduplication,       │
           │  Version Control & IMDB Rating Filter     │
           └─────────────────────┬─────────────────────┘
                                 │
 ┌───────────────────────────────┼───────────────────────────────┐
 │ (Routine Ingest Flow ▲)       │                               │ (Weekly Redistribution ▼)
 ▼                               ▼                               ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     LAN Node 1: DOC NAS         │   │     LAN Node 2: MEDIA NAS       │   │    LAN Node 3: MOVIE VAULT      │
│ (Synology DS220+ / RAID1 Btrfs) │   │ (TrueNAS Bare-metal e.g. .167)  │   │  (TrueNAS Mass Storage e.g. .014│
│                                 │   │                                 │   │                                 │
│ - T1 Business & Finance         │   │ - Curated Photos (LAN + iCloud) │   │ - Bulk Cinema Library (>2.4 TB) │
│ - LifeOS Personal & Evidence    │   │ - Music & Audio Libraries       │   │ - Raw Video Dumps & Torrents    │
│ - Project Repositories & Code   │   │ - Personal & Family Home Videos │   │ - Low-priority / Unranked Films │
│ - Dropbox Ingested Docs         │   │                                 │   │                                 │
└─────────────────────────────────┘   └─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## 3. The 5 TB Capacity Decision & Triage

The observed raw storage across the 5 LAN NAS nodes is roughly 8.8–9.0 TB. To fit safely into the 5 TB Google Drive Pro plan with $>30\%$ operational headroom ($\approx 3.2\text{ TB}$ target payload):

1. **VM & PVE Backups Excluded**: `vmback` (1.0 TB) and raw PVE dumps are excluded because they are already backed up by the Proxmox Backup Server (PBS `pbs-temp`, 192.168.88.5, doc 06) with 4.46x deduplication.
2. **Cross-Host Deduplication**: SHA-256 deduplication eliminates ~1.3 TB of redundant ISOs, duplicate movies, and scattered backup zips.
3. **Cinema Tiering**: Only high-scoring IMDb movies ($\ge 7.8$) and Top 250 classics sync to Google Drive (~400–600 GB). Bulk movies remain preserved on the local LAN Cinema Vault.
4. **Target Cloud Payload**: Approximately **1.2 – 1.6 TB**, leaving $>68\%$ free headroom in Google Drive.
