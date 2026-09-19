# 04 — Deduplication & Version Lineage

## 1. Cryptographic Deduplication

To eliminate the 2,856 duplicate groups identified across the estate without risking false positives:

1. **Tier 1 (Fast Fingerprinting)**:
   - Size + First 64 KiB + Last 64 KiB hash.
   - Eliminates 95% of non-duplicates in milliseconds without reading multi-gigabyte ISOs or videos.
2. **Tier 2 (Full Cryptographic Verification)**:
   - Full streaming SHA-256 computation over 1 MB blocks.
   - Files are only consolidated if `sha256_A == sha256_B`.
3. **Canonical Selection Hierarchy**:
   When identical files exist across multiple hosts, the canonical primary instance is chosen via:
   - `LAN_SYNOLOGY` (Rank 1: Primary Document authority)
   - `LAN_TRUENAS_167` (Rank 2: Primary Media authority)
   - `LAN_TRUENAS_069` (Rank 3: Replica node)
   - `LAN_TRUENAS_101` (Rank 4: VM scratch)
   - `LAN_TRUENAS_014` (Rank 5: Cinema Vault)
   - `DROPBOX` / `ICLOUD` (Rank 6/7)
   - `GDRIVE_EXISTING` (Rank 8)

All physical and cloud locations are preserved in `source_instances` table, allowing instant discovery of where copies reside without duplicating bytes in Google Drive.

---

## 2. Version Lineage & Revision Graph

Files that evolve over time are linked in a version family:
- Semantic version detection (e.g. `v1.0`, `v2.0`, `2025.1.0.1` vs `2025.1.0.9`, `Contract_Draft` vs `Contract_Final`).
- `catalog.db` tracks:
  * `family_name`: E.g. `scpoweb-linux` or `corporate-bylaws`.
  * `is_latest`: Boolean flag identifying the active canonical version.
  * `superseded_by_file_id`: Pointer linking previous drafts to the active release.
