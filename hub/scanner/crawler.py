"""Filesystem crawler indexing LAN NAS shares and mapping them to Google Drive catalog."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.core.database import Database
from hub.scanner.hasher import hash_file_two_tiered
from hub.classifier.rules import classify_domain, build_canonical_gdrive_path, classify_lifecycle
from hub.classifier.taxonomy import get_category_from_extension


class NASCrawler:
    """Recursively crawls LAN NAS shares, computes cryptographic hashes, and updates catalog."""

    def __init__(self, db: Database):
        self.db = db

    def scan_path(
        self,
        base_dir: Path | str,
        source_origin: str,
        job_type: str = "INGEST_LAN",
    ) -> Dict[str, Any]:
        """
        Crawl a directory or mounted share, hash files, and record into database.
        """
        base = Path(base_dir)
        if not base.exists():
            return {"error": f"Path does not exist: {base}", "files_ingested": 0}

        run_id = self.db.start_job(job_type)
        scanned = 0
        ingested = 0
        total_bytes = 0

        try:
            for item in base.rglob("*"):
                if item.is_file() and not item.name.startswith((".", "~$", "@eaDir", "#recycle")):
                    scanned += 1
                    try:
                        ext = item.suffix.lower()
                        category = get_category_from_extension(ext)
                        sha256, fast_hash, size = hash_file_two_tiered(item)
                        total_bytes += size

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
                            source_origin=source_origin,
                            source_path=str(item),
                            is_canonical_source=False,
                        )

                        mtime = item.stat().st_mtime
                        mod_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        fresh_days = self.db.get_config("lifecycle_fresh_days", 180)
                        stale_days = self.db.get_config("lifecycle_stale_days", 365)
                        status, reason = classify_lifecycle(mod_dt, domain, item.name, fresh_days, stale_days)
                        self.db.set_lifecycle(file_id, status, reason)

                        ingested += 1
                    except Exception as e:
                        self.db.log_error(run_id, str(item), "CRAWL_ERROR", str(e))

            self.db.finish_job(
                run_id, "SUCCESS", files_scanned=scanned, files_ingested=ingested,
                bytes_transferred=total_bytes,
                summary_message=f"Crawl complete for {source_origin}. Ingested {ingested} files."
            )
            return {
                "source_origin": source_origin,
                "files_scanned": scanned,
                "files_ingested": ingested,
                "total_bytes": total_bytes,
            }
        except Exception as e:
            self.db.finish_job(run_id, "FAILED", summary_message=str(e))
            raise
