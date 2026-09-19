"""Dropbox read-only document ingestion connector."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hub.core.database import Database
from hub.scanner.hasher import hash_file_two_tiered
from hub.classifier.rules import classify_domain, build_canonical_gdrive_path, classify_lifecycle
from hub.classifier.taxonomy import get_category_from_extension


class DropboxIngestor:
    """Ingests documents from a local Dropbox folder or rclone Dropbox remote in read-only mode."""

    def __init__(self, db: Database):
        self.db = db

    def scan_dropbox_folder(self, folder_path: Path | str) -> Dict[str, Any]:
        """Crawl Dropbox tree, register files, and map them to Google Drive taxonomy."""
        base = Path(folder_path)
        if not base.exists():
            return {"error": f"Dropbox directory does not exist: {base}", "files_ingested": 0}

        run_id = self.db.start_job("DROPBOX_SYNC")
        scanned = 0
        ingested = 0

        try:
            for item in base.rglob("*"):
                if item.is_file() and not item.name.startswith((".", "~$")):
                    scanned += 1
                    try:
                        ext = item.suffix.lower()
                        category = get_category_from_extension(ext)
                        sha256, fast_hash, size = hash_file_two_tiered(item)
                        rel_path = str(item.relative_to(base))

                        domain = classify_domain(rel_path, item.name)
                        canonical_path = build_canonical_gdrive_path(rel_path, item.name, domain, category)

                        file_id = self.db.register_file(
                            sha256=sha256,
                            fast_hash=fast_hash,
                            file_name=item.name,
                            file_extension=ext,
                            canonical_gdrive_path=canonical_path,
                            size_bytes=size,
                            category=category,
                            domain=domain,
                        )

                        self.db.add_source_instance(
                            file_id=file_id,
                            source_origin="DROPBOX",
                            source_path=str(item),
                            is_canonical_source=False,
                        )

                        stat = item.stat()
                        mtime = item.stat().st_mtime
                        from datetime import datetime, timezone
                        mod_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        status, reason = classify_lifecycle(mod_dt, domain, item.name)
                        self.db.set_lifecycle(file_id, status, reason)

                        ingested += 1
                    except Exception as e:
                        self.db.log_error(run_id, str(item), "INGEST_ERROR", str(e))

            self.db.finish_job(
                run_id, "SUCCESS", files_scanned=scanned, files_ingested=ingested,
                summary_message=f"Dropbox ingest complete. Processed {ingested} files."
            )
            return {"files_scanned": scanned, "files_ingested": ingested}
        except Exception as e:
            self.db.finish_job(run_id, "FAILED", summary_message=str(e))
            raise
