-- ==============================================================================
-- gdrive-data-hub: Central SQLite Metadata, Lineage & Governance Catalog Schema
-- ==============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Files Registry (Canonical Records in Google Drive)
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT NOT NULL,
    fast_hash TEXT,                              -- 64KB head/tail fast fingerprint
    file_name TEXT NOT NULL,
    file_extension TEXT,
    canonical_gdrive_path TEXT NOT NULL UNIQUE,  -- E.g. '01_BUSINESS/Accounting/2026_ledger.xlsx'
    size_bytes INTEGER NOT NULL,
    mime_type TEXT,
    created_at DATETIME,
    modified_at DATETIME,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    gdrive_file_id TEXT,                         -- Cloud-assigned Google Drive File ID
    category TEXT NOT NULL,                      -- 'doc', 'music', 'movie', 'photo', 'code', 'software', 'archive'
    domain TEXT NOT NULL,                        -- 'business', 'lifeos', 'projects', 'knowledge', 'system'
    is_cloud_synced BOOLEAN DEFAULT 0,
    cloud_synced_at DATETIME
);

-- 2. Multi-Host Provenance & Duplication Tracker (Tracks all physical and cloud instances)
CREATE TABLE IF NOT EXISTS source_instances (
    instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
    source_origin TEXT NOT NULL,                 -- 'LAN_SYNOLOGY', 'LAN_TRUENAS_167', 'LAN_TRUENAS_014', 'ICLOUD', 'DROPBOX', 'GDRIVE_EXISTING'
    source_path TEXT NOT NULL,
    is_canonical_source BOOLEAN DEFAULT 0,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'IN_SYNC' CHECK (sync_status IN ('IN_SYNC', 'PENDING_UPLOAD', 'PENDING_REDISTRIBUTION', 'CONFLICT'))
);

-- 3. Document Lifecycle & Validation Status
CREATE TABLE IF NOT EXISTS lifecycle (
    file_id INTEGER PRIMARY KEY REFERENCES files(file_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('fresh', 'stable', 'lack_of_update', 'obsolete')),
    status_reason TEXT,
    last_validated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    review_due_date DATETIME,
    retention_policy TEXT DEFAULT 'PERMANENT',
    owner TEXT DEFAULT 'administrator'
);

-- 4. Version Lineage Graph & Revision Tracking
CREATE TABLE IF NOT EXISTS version_lineage (
    lineage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_name TEXT NOT NULL,                   -- E.g. 'quarterly-report', 'scpoweb-linux'
    file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
    version_tag TEXT,                            -- E.g. 'v1.0', '2026-Q1', 'patch-2025.1.0.9'
    is_latest BOOLEAN DEFAULT 1,
    superseded_by_file_id INTEGER REFERENCES files(file_id) ON DELETE SET NULL,
    change_summary TEXT
);

-- 5. IMDb Movie Curation & Placement Policy
CREATE TABLE IF NOT EXISTS movie_curation (
    movie_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(file_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    release_year INTEGER,
    imdb_id TEXT,
    imdb_rating REAL,
    imdb_votes INTEGER,
    genres TEXT,
    synopsis TEXT,
    manual_override TEXT DEFAULT 'AUTO' CHECK (manual_override IN ('FORCE_CLOUD', 'FORCE_LOCAL', 'AUTO')),
    tier_location TEXT NOT NULL CHECK (tier_location IN ('CLOUD_AND_LOCAL', 'LOCAL_VAULT_ONLY'))
);

-- 6. AI Insights, Extracted Text & Ground-Truth Verification Anchors
CREATE TABLE IF NOT EXISTS ai_insights (
    file_id INTEGER PRIMARY KEY REFERENCES files(file_id) ON DELETE CASCADE,
    text_content_preview TEXT,
    ai_summary TEXT,
    key_topics_json TEXT,                        -- JSON array of extracted key concepts
    entities_json TEXT,                          -- JSON array of entities (counterparties, dates, amounts)
    embedding_status TEXT DEFAULT 'pending' CHECK (embedding_status IN ('pending', 'extracted', 'skipped')),
    historical_fact_anchor TEXT                  -- Immutable facts used to verify future incoming data
);

-- 7. Bidirectional Conflict Registry
CREATE TABLE IF NOT EXISTS sync_conflicts (
    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(file_id) ON DELETE CASCADE,
    lan_source TEXT NOT NULL,
    cloud_source TEXT NOT NULL,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    lan_mtime DATETIME,
    cloud_mtime DATETIME,
    lan_sha256 TEXT,
    cloud_sha256 TEXT,
    resolution TEXT DEFAULT 'PENDING' CHECK (resolution IN ('PENDING', 'ACCEPT_LAN', 'ACCEPT_CLOUD', 'BRANCH_BOTH')),
    resolved_at DATETIME
);

-- 8. Operational Telemetry: Job Runs (Last X Days History)
CREATE TABLE IF NOT EXISTS job_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL CHECK (job_type IN ('INGEST_LAN', 'REDISTRIBUTE_LAN', 'ICLOUD_SYNC', 'DROPBOX_SYNC', 'AUDIT_GDRIVE', 'FULL_SWEEP')),
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'WARNING', 'FAILED')),
    files_scanned INTEGER DEFAULT 0,
    files_ingested INTEGER DEFAULT 0,
    duplicates_detected INTEGER DEFAULT 0,
    bytes_transferred INTEGER DEFAULT 0,
    summary_message TEXT
);

-- 9. Granular Job Error Inspector
CREATE TABLE IF NOT EXISTS job_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES job_runs(run_id) ON DELETE CASCADE,
    file_path TEXT,
    error_type TEXT NOT NULL,                    -- 'API_RATE_LIMIT', 'AUTH_EXPIRED', 'CHECKSUM_MISMATCH', 'IO_TIMEOUT'
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    is_resolved BOOLEAN DEFAULT 0,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 10. Dynamic Portal Configuration Parameters
CREATE TABLE IF NOT EXISTS system_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    value_type TEXT DEFAULT 'string' CHECK (value_type IN ('string', 'int', 'float', 'bool', 'json')),
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 11. Folder Archetype Governance Policies (Lean Solo-Operator Model)
CREATE TABLE IF NOT EXISTS folder_policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_prefix TEXT NOT NULL UNIQUE,          -- E.g. '01_Business', '00_Inbox', '04_Archive'
    archetype TEXT NOT NULL,                     -- 'ACTIVE_WORKSPACE', 'PROJECT_WORKSPACE', 'TOOLCHAIN_CURATED', 'COLD_ARCHIVE', 'MEDIA_VAULT', 'PLATFORM_DATA', 'QUARANTINE'
    tier TEXT NOT NULL,                          -- 'T1', 'T2', 'T3', 'T2-temp'
    authority_node TEXT NOT NULL,                -- 'SYNOLOGY_PRIMARY', 'TRUENAS_167', 'TRUENAS_069', 'GDRIVE'
    replica_target TEXT,                         -- 'TRUENAS_167_CACHE', 'NONE'
    rpo_hours INTEGER DEFAULT 24,
    rto_hours INTEGER DEFAULT 4,
    retention_days INTEGER DEFAULT 30,
    sync_frequency TEXT DEFAULT 'DAILY',
    auto_quarantine_days INTEGER DEFAULT 0,      -- 30 for 00_Inbox, 0 for others
    description TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_fast_hash ON files(fast_hash);
CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);
CREATE INDEX IF NOT EXISTS idx_files_domain ON files(domain);
CREATE INDEX IF NOT EXISTS idx_instances_file_id ON source_instances(file_id);
CREATE INDEX IF NOT EXISTS idx_instances_origin ON source_instances(source_origin);
CREATE INDEX IF NOT EXISTS idx_lifecycle_status ON lifecycle(status);
CREATE INDEX IF NOT EXISTS idx_lineage_family ON version_lineage(family_name);
CREATE INDEX IF NOT EXISTS idx_movie_imdb ON movie_curation(imdb_rating);
CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_folder_policies_prefix ON folder_policies(folder_prefix);
