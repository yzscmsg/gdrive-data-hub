"""Fast batch importer for Google Drive JSON catalogs into central SQLite database."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hub.core.database import Database
from hub.classifier.rules import classify_domain, classify_lifecycle
from hub.classifier.taxonomy import get_category_from_extension


def import_gdrive_catalog(
    json_path: Path | str,
    db: Database,
    batch_size: int = 2500,
) -> Dict[str, Any]:
    """
    Import an exported rclone lsjson file into catalog.db with full classification and lifecycle tagging.
    """
    json_file = Path(json_path)
    if not json_file.exists():
        raise FileNotFoundError(f"Catalog JSON not found at: {json_file}")

    print(f"[*] Loading Google Drive catalog from {json_file.name}...")
    raw = json_file.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        items = json.loads(raw.decode("utf-16"))
    elif raw.startswith(b"\xef\xbb\xbf"):
        items = json.loads(raw.decode("utf-8-sig"))
    else:
        items = json.loads(raw.decode("utf-8", errors="replace"))

    total_items = len(items)
    print(f"[*] Parsing {total_items:,} items from Google Drive...")

    fresh_days = db.get_config("lifecycle_fresh_days", 180)
    stale_days = db.get_config("lifecycle_stale_days", 365)

    run_id = db.start_job("AUDIT_GDRIVE")
    ingested = 0
    total_bytes = 0

    with db.connection() as conn:
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache

        # Process in batches
        files_batch = []
        for i, item in enumerate(items, 1):
            if item.get("IsDir", False):
                continue

            name = item.get("Name", "")
            if not name or name.startswith((".", "~$", "@eaDir", "#recycle")):
                continue

            path = item.get("Path", "")
            size = item.get("Size", 0)
            total_bytes += size
            mime_type = item.get("MimeType", "")
            gdrive_id = item.get("ID", "")
            mod_time_str = item.get("ModTime")

            mod_dt = None
            if mod_time_str:
                try:
                    # ISO format parsing
                    clean_str = mod_time_str.replace("Z", "+00:00")
                    mod_dt = datetime.fromisoformat(clean_str)
                except Exception:
                    pass

            ext = Path(name).suffix.lower()
            category = get_category_from_extension(ext)
            domain = classify_domain(path, name)
            canonical_path = f"lCE2026/{path}"

            hashes = item.get("Hashes") or {}
            sha256 = hashes.get("sha256") or hashes.get("md5") or hashes.get("sha1") or f"cloud_{gdrive_id}"
            fast_hash = hashes.get("md5") or sha256[:16]

            status, reason = classify_lifecycle(mod_dt, domain, name, fresh_days, stale_days)

            files_batch.append((
                sha256, fast_hash, name, ext, canonical_path, size, mime_type,
                mod_time_str, gdrive_id, category, domain,
                path, status, reason
            ))

            if len(files_batch) >= batch_size or i == total_items:
                # Execute batch insert
                for record in files_batch:
                    (
                        r_sha256, r_fast_hash, r_name, r_ext, r_canonical_path, r_size, r_mime,
                        r_mod_time, r_gdrive_id, r_category, r_domain,
                        r_source_path, r_status, r_reason
                    ) = record

                    # 1. Upsert files
                    cur = conn.execute(
                        """
                        INSERT INTO files (
                            sha256, fast_hash, file_name, file_extension, canonical_gdrive_path,
                            size_bytes, mime_type, modified_at, gdrive_file_id, category, domain,
                            is_cloud_synced, cloud_synced_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT(canonical_gdrive_path) DO UPDATE SET
                            sha256 = excluded.sha256,
                            fast_hash = excluded.fast_hash,
                            size_bytes = excluded.size_bytes,
                            modified_at = excluded.modified_at,
                            gdrive_file_id = excluded.gdrive_file_id,
                            is_cloud_synced = 1,
                            cloud_synced_at = CURRENT_TIMESTAMP
                        RETURNING file_id
                        """,
                        (
                            r_sha256, r_fast_hash, r_name, r_ext, r_canonical_path, r_size, r_mime,
                            r_mod_time, r_gdrive_id, r_category, r_domain
                        ),
                    )
                    file_id = cur.fetchone()["file_id"]

                    # 2. Source instance
                    conn.execute(
                        """
                        INSERT INTO source_instances (
                            file_id, source_origin, source_path, is_canonical_source, sync_status, last_seen_at
                        ) VALUES (?, 'GDRIVE_EXISTING', ?, 1, 'IN_SYNC', CURRENT_TIMESTAMP)
                        """,
                        (file_id, r_source_path),
                    )

                    # 3. Lifecycle
                    conn.execute(
                        """
                        INSERT INTO lifecycle (file_id, status, status_reason, last_validated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(file_id) DO UPDATE SET
                            status = excluded.status,
                            status_reason = excluded.status_reason,
                            last_validated_at = CURRENT_TIMESTAMP
                        """,
                        (file_id, r_status, r_reason),
                    )
                    ingested += 1

                conn.commit()
                print(f"    -> Progress: {ingested:,} / {total_items:,} files ingested ({(ingested/total_items)*100:.1f}%)")
                files_batch.clear()

    db.finish_job(
        run_id,
        status="SUCCESS",
        files_scanned=total_items,
        files_ingested=ingested,
        bytes_transferred=total_bytes,
        summary_message=f"Google Drive cloud catalog ingestion complete: {ingested:,} files registered ({total_bytes / (1024**3):.2f} GiB).",
    )

    print(f"[+] Google Drive Catalog successfully indexed into catalog.db!")
    print(f"    - Total Files: {ingested:,}")
    print(f"    - Total Volume: {total_bytes / (1024**3):.2f} GiB")
    return {
        "files_ingested": ingested,
        "total_bytes": total_bytes,
        "run_id": run_id,
    }


if __name__ == "__main__":
    db_inst = Database("data/catalog.db")
    json_p = Path("data/gdrive_lce2026.json")
    import_gdrive_catalog(json_p, db_inst)
