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
('lan_node_movie_ip', '192.168.0.14', 'string', 'IP of designated LAN Cinema Vault (TrueNAS bulk movies)');
