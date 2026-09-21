-- ==============================================================================
-- Seed Initial Operational Configuration Parameters
-- ==============================================================================

INSERT OR REPLACE INTO system_config (config_key, config_value, value_type, description) VALUES
('imdb_rating_threshold', '7.8', 'float', 'Minimum IMDb score required for a movie to sync to Google Drive Curated Cinema'),
('imdb_votes_threshold', '25000', 'int', 'Minimum number of user votes on IMDb required for non-classic releases'),
('imdb_top250_force_include', 'true', 'bool', 'Whether all IMDb Top 250 films are automatically synced to Google Drive'),
('ingest_schedule_cron', '0 2 * * *', 'string', 'Nightly ingest schedule from LAN NAS to Google Drive (02:00 daily)'),
('redistribute_schedule_cron', '0 3 * * 0', 'string', 'Weekly reverse redistribution schedule (Google Drive to LAN NAS, Sunday 03:00)'),
('bandwidth_limit_day_mb', '5', 'int', 'Maximum upload bandwidth in MB/s during business hours (08:00 - 19:00)'),
('bandwidth_limit_night_mb', '50', 'int', 'Maximum upload bandwidth in MB/s off-peak (19:00 - 08:00)'),
('lifecycle_fresh_days', '180', 'int', 'Days since modification for a document to be classified as fresh'),
('lifecycle_stale_days', '365', 'int', 'Days without modification or validation before flagging lack_of_update'),
('gdrive_storage_quota_bytes', '5497558138880', 'int', 'Total Google Drive Pro quota limit (5 TB in bytes)'),
('gdrive_warning_threshold_pct', '75', 'int', 'Storage percentage threshold triggering a warning in the portal (3.75 TB)'),
('gdrive_critical_threshold_pct', '85', 'int', 'Storage percentage threshold triggering a critical alarm (4.25 TB)'),
('conflict_resolution_policy', 'BRANCH_BOTH', 'string', 'Default action on concurrent edit conflict: BRANCH_BOTH, ACCEPT_LAN, ACCEPT_CLOUD'),
('lan_node_doc_ip', '10.65.1.53', 'string', 'IP of designated LAN Document NAS (Synology DS220+)'),
('lan_node_media_ip', '192.168.0.167', 'string', 'IP of designated LAN Media NAS (TrueNAS Photos & Music)'),
('lan_node_movie_ip', '192.168.0.69', 'string', 'IP of designated LAN Cinema Vault (TrueNAS nas-tn-069, replacing inactive .014)'),
('edge_167_cache_enabled', 'true', 'bool', 'Enable Satellite Edge Cache on TrueNAS 167 for Office B fast access'),
('edge_167_freshness_days', '180', 'int', 'Max age in days for active business documents to be cached on 167'),
('edge_167_include_tools', 'true', 'bool', 'Mirror curated IT software tools & utilities to 167 edge workspace'),
('edge_167_max_quota_gb', '50', 'int', 'Maximum disk quota in GB allocated to 167 edge workspace cache'),
('inbox_auto_quarantine_days', '30', 'int', 'Days before unclaimed 00_Inbox files are moved to 07_Quarantine/Unsorted');

-- 7 Root Folder Archetypes (Lean Solo-Operator Governance)
INSERT OR REPLACE INTO folder_policies (folder_prefix, archetype, tier, authority_node, replica_target, rpo_hours, rto_hours, retention_days, sync_frequency, auto_quarantine_days, description) VALUES
('00_Inbox', 'QUARANTINE', 'T2-temp', 'SHARED_DROPZONE', 'NONE', 24, 4, 30, 'HOURLY', 30, 'Temporary file dropzone with 30-day auto-quarantine triage'),
('01_Business', 'ACTIVE_WORKSPACE', 'T1', 'SYNOLOGY_PRIMARY', 'TRUENAS_167_CACHE', 1, 1, 30, 'HOURLY', 0, 'Daily operational business, accounting, and corporate documents'),
('02_Projects', 'PROJECT_WORKSPACE', 'T2', 'SYNOLOGY_PRIMARY', 'NONE', 24, 4, 90, 'DAILY', 0, 'Technical projects, development repositories, and specifications'),
('03_Software', 'TOOLCHAIN_CURATED', 'T3', 'GDRIVE_CANONICAL', 'TRUENAS_167_CACHE', 168, 8, 365, 'WEEKLY', 0, 'Curated utilities, runtime installers, and diagnostic tools'),
('04_Archive', 'COLD_ARCHIVE', 'T3', 'SYNOLOGY_PRIMARY', 'NONE', 720, 24, 3650, 'MONTHLY', 0, 'Permanent historical records and closed client files (read-only)'),
('05_Media', 'MEDIA_VAULT', 'T2', 'TRUENAS_167', 'TRUENAS_069_VAULT', 168, 8, 365, 'WEEKLY', 0, 'Photos and music on 167; Movies on 069 with IMDb score filtering'),
('06_Platform', 'PLATFORM_DATA', 'T1', 'LOCAL_ISOLATED', 'NONE', 24, 4, 30, 'DAILY', 0, 'App data, system configurations, and hypervisor backups');

