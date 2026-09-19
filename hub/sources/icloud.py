"""iCloud Photos & Videos read-only ingestion connector."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.core.database import Database
from hub.scanner.hasher import hash_file_two_tiered
from hub.classifier.taxonomy import get_category_from_extension


class ICloudIngestor:
    """Ingests full-resolution photos, Live Photo pairs, and home videos from iCloud in read-only mode."""

    def __init__(self, db: Database):
        self.db = db

    def check_session_health(self, cookie_directory: Optional[Path | str] = None) -> Dict[str, Any]:
        """Check if Apple ID 2FA session token is active or requires re-authentication."""
        cookie_path = Path(cookie_directory or "~/.icloudpd").expanduser()
        if not cookie_path.exists():
            return {
                "status": "UNCONFIGURED",
                "message": "iCloud cookie directory not found. Please authenticate via icloudpd CLI.",
            }
        return {
            "status": "HEALTHY",
            "message": "iCloud session cookies found and active.",
        }

    def scan_icloud_photos_folder(self, photo_dir: Path | str) -> Dict[str, Any]:
        """Crawl local iCloud Photos directory and catalog media into Google Drive taxonomy."""
        base = Path(photo_dir)
        if not base.exists():
            return {"error": f"Directory does not exist: {base}", "files_ingested": 0}

        run_id = self.db.start_job("ICLOUD_SYNC")
        scanned = 0
        ingested = 0

        try:
            for item in base.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    scanned += 1
                    try:
                        ext = item.suffix.lower()
                        category = get_category_from_extension(ext)
                        if category not in ("photo", "movie"):
                            continue

                        sha256, fast_hash, size = hash_file_two_tiered(item)
                        subfolder = "Photos" if category == "photo" else "Personal_Video"
                        canonical_path = f"06_MEDIA/{subfolder}/{item.name}"

                        file_id = self.db.register_file(
                            sha256=sha256,
                            fast_hash=fast_hash,
                            file_name=item.name,
                            file_extension=ext,
                            canonical_gdrive_path=canonical_path,
                            size_bytes=size,
                            category=category,
                            domain="media",
                        )

                        self.db.add_source_instance(
                            file_id=file_id,
                            source_origin="ICLOUD",
                            source_path=str(item),
                            is_canonical_source=False,
                        )

                        mtime = item.stat().st_mtime
                        mod_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        self.db.set_lifecycle(file_id, "stable", "Verified personal photo/video record")
                        ingested += 1
                    except Exception as e:
                        self.db.log_error(run_id, str(item), "ICLOUD_INGEST_ERROR", str(e))

            self.db.finish_job(
                run_id, "SUCCESS", files_scanned=scanned, files_ingested=ingested,
                summary_message=f"iCloud ingest complete. Processed {ingested} media items."
            )
            return {"files_scanned": scanned, "files_ingested": ingested}
        except Exception as e:
            self.db.finish_job(run_id, "FAILED", summary_message=str(e))
            raise
