# 05 — Multi-Cloud Ingestion (iCloud, Dropbox & Existing Google Drive)

## 1. External Cloud Ingestion Standard (Read-Only)

`gdrive-data-hub` treats external clouds as **ingest-only data sources**:
- Zero modifications, deletions, or write-backs are performed against iCloud or Dropbox.
- Files flow in one direction: External Cloud $\rightarrow$ Google Drive $\rightarrow$ Downstream LAN NAS Redistribution.

---

## 2. iCloud Photos & Home Videos

- **Ingestion Pipeline**: Automated via `icloudpd` (iCloud Photos Downloader) or local sync folder.
- **Handling**:
  * Downloads original master resolution images (`.HEIC`, `.JPG`, `.PNG`, `.RAW`).
  * Pairs Live Photo assets (matching image and `.MOV` video clip).
  * Extracts EXIF metadata (capture timestamps, GPS tags, camera details).
  * Lands in Google Drive at `06_MEDIA/Photos/` and `06_MEDIA/Personal_Video/`.
- **LAN Redistribution**: Automatically copied down to the **Media NAS** (`nas-tn-167`) during the weekly cycle so the local offline vault is complete.

---

## 3. Dropbox Documents

- **Ingestion Pipeline**: Connects via Dropbox API or local Dropbox directory.
- **Handling**:
  * Crawls documents (`.docx`, `.pdf`, `.xlsx`, `.pptx`).
  * Cross-deduplicates against LAN NAS shares (eliminates identical copies scattered between Dropbox and Synology).
  * Automatically maps into `01_BUSINESS/`, `02_LIFEOS_FAMILY/`, or `03_PROJECTS_CODE/`.
- **LAN Redistribution**: Automatically copied down to the **Document NAS** (Synology DS220+) during the weekly cycle.

---

## 4. Existing Google Drive Data Reconciliation

Google Drive already holds documents before this migration. The system handles them as follows:
1. **In-Place Discovery**: Crawls existing files, capturing file IDs, cloud MD5 hashes, and modification dates into `catalog.db` with `GDRIVE_EXISTING` origin.
2. **Hash Matching**: Avoids re-uploading identical files and preserves existing Google Drive sharing links.
3. **In-Place Restructuring**: Moves existing cloud files into the standardized taxonomy (`01_BUSINESS/`, etc.) using instant API folder moves (zero network transfer).
4. **Archival**: Unclassified or stale legacy items are safely placed in `07_ARCHIVE/Legacy_GDrive_Unsorted/`.
