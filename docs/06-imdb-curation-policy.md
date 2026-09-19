# 06 — IMDb Cinema Curation Policy

## 1. The Cinema Storage Problem

The local movie library across TrueNAS `.014` and `.101` exceeds 2.4 TB. Syncing all raw movie files to Google Drive would consume over half of the 5 TB total quota, leaving insufficient room for business growth and high-resolution family photos.

---

## 2. Two-Tier Cinema Architecture

To balance cloud accessibility with storage economics:

```
  ┌─────────────────────────────────────────────────────────────┐
  │                   TWO-TIER CINEMA ARCHITECTURE              │
  ├───────────────────┬─────────────────────────────────────────┤
  │ Tier 1: Cloud     │ IMDb >= 7.8, Top 250, or Tagged Favorite│
  │ Curated Cinema    │ Stored in Google Drive (06_MEDIA/Cinema)│
  │                   │ & LAN Cinema Vault. (~400–600 GB)       │
  ├───────────────────┼─────────────────────────────────────────┤
  │ Tier 2: Local     │ IMDb < 7.8, unrated, screeners, bulk    │
  │ Cinema Vault      │ Stored EXCLUSIVELY on LAN NAS (.014).   │
  │                   │ Zero Google Drive quota consumed.       │
  └───────────────────┴─────────────────────────────────────────┘
```

---

## 3. Automated Evaluation & Metadata Enrichment

1. **Title & Year Extraction**: Release names (e.g. `Blade.Runner.2049.2017.PROPER.2160p.US.BluRay.REMUX...mkv`) are parsed into clean titles (`Blade Runner 2049`) and release years (`2017`).
2. **IMDb / OMDb Query**: The engine queries the rating, votes, genre, and plot summary.
3. **Threshold Evaluation**:
   - Default rating threshold: **7.8** (configurable in Management Portal).
   - Default vote threshold: **25,000** votes (ensures rating statistical validity).
   - IMDb Top 250: Automatically included.
4. **Manual Portal Overrides**:
   - **FORCE_CLOUD**: Force sync to Google Drive regardless of rating (e.g. personal favorite or documentary).
   - **FORCE_LOCAL**: Force local-only retention regardless of high rating.
