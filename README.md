# gdrive-data-hub

**Continuous Data Governance & Hybrid Storage Hub bridging LAN NAS and Google Drive Pro (5 TB)**

`gdrive-data-hub` is a living, bidirectional data management system designed for multi-site LAN NAS environments (Synology and TrueNAS across Office A & Office B) connected to a central 5 TB Google Drive cloud hub.

---

## Key Architecture & Capabilities

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
│     LAN Node 1: DOC NAS         │   │     LAN Node 2: MEDIA NAS       │   │    LAN Node 3: CINEMA VAULT     │
│ (Synology DS220+ / RAID1 Btrfs) │   │ (TrueNAS Bare-metal e.g. .167)  │   │ (TrueNAS Bare-metal .069)       │
│                                 │   │                                 │   │                                 │
│ - T1 Business & Finance         │   │ - Curated Photos (LAN + iCloud) │   │ - Bulk Cinema Library (>2.4 TB) │
│ - LifeOS Personal & Evidence    │   │ - Music & Audio Libraries       │   │ - Raw Video Dumps & Torrents    │
│ - Project Repositories & Code   │   │ - Personal & Family Home Videos │   │ - Active replacement for .014   │
│ - Dropbox Ingested Docs         │   │                                 │   │                                 │
└─────────────────────────────────┘   └─────────────────────────────────┘   └─────────────────────────────────┘
```

1. **Hybrid Living Ecosystem**: Users work against fast local LAN NAS shares for low latency. Google Drive maintains the authoritative, deduplicated cloud ground truth.
2. **Specialized LAN NAS Roles**:
   - **Document NAS** (`10.65.1.53`, Synology DS220+ RAID1): Authoritative home for business documents, LifeOS evidence, and code repositories.
   - **Media NAS** (`192.168.0.167`, TrueNAS): Authoritative home for curated photos, music, and home videos.
   - **Cinema & Bulk Vault** (`192.168.0.69`, TrueNAS bare-metal `nas-tn-069`): Local bulk storage for cinema library (>2.4 TB) and download staging (active replacement for offline `.014`).
3. **IMDb-Curated Cinema Tiering**:
   - Only films with IMDb rating $\ge 7.8$, Top 250 classics, or tagged "Favorites" sync to Google Drive (~400–600 GB). All bulk movies stay on the local Cinema Vault.
4. **Bidirectional Sync with Version Branching**:
   - "Never Overwrite, Always Branch" conflict resolution preserves both LAN and cloud concurrent edits.
5. **Multi-Cloud Ingestion (Read-Only)**:
   - Ingests iCloud (photos/videos) and Dropbox (documents) without write-backs.
6. **AI Ground Truth**:
   - Extracted text, entity anchors, and summaries in `catalog.db` enable historical document verification and RAG queries.
7. **Web Management Portal**:
   - Real-time 5 TB storage gauge, interactive policy sliders, error logs, and one-click retry.

---

## Quick Start

### 1. Installation
```bash
git clone https://github.com/yzscmsg/gdrive-data-hub.git
cd gdrive-data-hub

# Core engine runs on pure Python 3.10+ standard library.
# Optional dependencies for web portal:
pip install -r requirements.txt
```

### 2. Basic CLI Operations

```bash
# Initialize and scan a LAN NAS share
python -m hub.cli scan --path "/mnt/nas_synology/data" --origin "LAN_SYNOLOGY"

# Detect and resolve cross-host duplicates
python -m hub.cli dedup --resolve

# Preview weekly reverse redistribution down to LAN nodes
python -m hub.cli redistribute --plan-only

# Generate master INDEX.md and static HTML dashboard
python -m hub.cli index --out-md "INDEX.md" --out-html "dashboard.html"

# Verify a candidate document against historical baselines
python -m hub.cli verify --input "sample_contract.pdf"

# Start the Web Management Portal
python -m hub.cli portal --port 8080
```

---

## Documentation

Detailed architectural and operational documentation is available in [`docs/`](docs/):

- [01 — Architecture Overview](docs/01-architecture-overview.md)
- [02 — Information Architecture & Taxonomy](docs/02-information-architecture.md)
- [03 — Lifecycle & Validation Classification](docs/03-lifecycle-and-classification.md)
- [04 — Deduplication & Version Lineage](docs/04-deduplication-and-lineage.md)
- [05 — Multi-Cloud Ingestion (iCloud & Dropbox)](docs/05-multi-cloud-ingestion.md)
- [06 — IMDb Cinema Curation Policy](docs/06-imdb-curation-policy.md)
- [07 — Web Management Portal](docs/07-management-portal.md)
- [08 — Operational Runbook](docs/08-operational-runbook.md)
- [09 — Risk Analysis & Mitigation Matrix](docs/09-risk-matrix.md)

---

## License

Private repository for internal infrastructure and data governance.
