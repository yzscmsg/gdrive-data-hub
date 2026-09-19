# 02 — Information Architecture & Google Drive Taxonomy

## 1. Google Drive Directory Standard

The target structure in Google Drive separates concerns, isolates automated systems, and organizes data into clean, permanent domain namespaces:

```
Google Drive Root /
├── 00_SYSTEM/                         # Operational metadata, tools, and indexes
│   ├── catalog.db                     # Central SQLite metadata, lineage & status database
│   ├── catalog_export.parquet         # Fast analytical dump of file index
│   ├── INDEX.md                       # Master human-readable index & overview
│   ├── manifests/                     # Dated migration & snapshot manifests (JSONL)
│   └── ai_cache/                      # Chunked text extracts & vector embeddings for RAG
├── 01_BUSINESS/                       # T1 Enterprise Records (Synology Authority + Dropbox Ingest)
│   ├── Accounting_Finance/            # P&L, invoices, tax, banking records
│   ├── HR_Legal/                      # Contracts, employee files, company registration
│   ├── Odoo_ERP/                      # Odoo filestores, attachments, exports
│   └── Operations_General/            # Common business docs, office management
├── 02_LIFEOS_FAMILY/                  # Personal & Household Core Data
│   ├── Evidence/                      # Critical identity, medical, legal records (WORM / stable)
│   ├── Financial_Personal/            # Personal investments, family banking
│   ├── Family_Archives/               # Consolidated Kelly Zeng & family records
│   └── Household_Ops/                 # Property, warranties, vehicle, home management
├── 03_PROJECTS_CODE/                  # Software Repositories & Engineering
│   ├── Git_Repositories/              # Canonical code bundles and project trees
│   ├── Architecture_ADRs/             # System blueprints, ADRs, network maps
│   └── Active_Workspaces/             # Current project documentation & design assets
├── 04_KNOWLEDGE_BASE/                 # Reference, Learning & Research
│   ├── Technical_Reference/           # Vendor manuals, API specs, whitepapers
│   ├── Training_Courses/              # SBD/JDA training materials, educational videos
│   └── Ebooks_Papers/                 # Curated ebooks, research papers, notes
├── 05_SOFTWARE_TOOLS/                 # Canonical, Deduplicated Software Library
│   ├── Dev_Tools_Utilities/           # Custom scripts, admin toolchains
│   ├── Enterprise_Patches/            # Oracle clients, JDA service updates (canonical only)
│   └── Curated_OS_Images/             # Gold-standard base images (strictly deduplicated)
├── 06_MEDIA/                          # Curated Media Center (NAS + iCloud Ingest)
│   ├── Photos/                        # Organized by YYYY/MM/Event (LAN photos + iCloud sync)
│   ├── Music/                         # Audio collection (Artist / Album)
│   ├── Personal_Video/                # Family video recordings & iCloud clips
│   └── Curated_Cinema/                # IMDb-curated top movies (score >= 7.8 / Top 250)
└── 07_ARCHIVE/                        # Frozen Historical Reference (Read-Only)
    ├── Legacy_NetBackup_2026/         # De-duplicated, archived snapshot of old NetBackup
    ├── Legacy_GDrive_Unsorted/        # Stale unclassified files from existing GDrive
    └── Stale_Quarantine/              # Stale exports pending final review
```

---

## 2. Invariant Taxonomy Rules

1. **No Mixed Dumping**: Software installers (ISOs) never mix into general document folders; cinema never mixes into personal photos.
2. **Immutable System Metadata**: `00_SYSTEM/` is reserved exclusively for `catalog.db`, indexing artifacts, and AI cache. No user-facing files are placed in `00_SYSTEM/`.
3. **Flat Depth Limit**: Max depth within any category is $\le 4$ levels to ensure instant mobile navigation and prevent path length issues across OS platforms.
4. **Case Normalization**: All directory names use PascalCase or Upper_Snake_Case for readability across Windows, Linux, macOS, and cloud web clients.
