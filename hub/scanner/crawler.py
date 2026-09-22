"""Filesystem crawler indexing LAN NAS shares and mapping them to Google Drive catalog."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.core.database import Database
from hub.scanner.hasher import hash_file_two_tiered
from hub.classifier.rules import classify_domain, build_canonical_gdrive_path, classify_lifecycle
from hub.classifier.taxonomy import get_category_from_extension
from hub.media.imdb import parse_movie_title_and_year, fetch_movie_rating, evaluate_cloud_placement


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

        fresh_days = self.db.get_config("lifecycle_fresh_days", 180)
        stale_days = self.db.get_config("lifecycle_stale_days", 365)

        try:
            with self.db.connection() as conn:
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
                            if domain == "media" and category in ("movie", "photo", "music"):
                                rel_clean = rel_path.replace("\\", "/")
                                if category == "movie":
                                    canonical_path = f"06_MEDIA/Curated_Cinema/{rel_clean}"
                                elif category == "photo":
                                    canonical_path = f"06_MEDIA/Photos/{rel_clean}"
                                else:
                                    canonical_path = f"06_MEDIA/Music/{rel_clean}"
                            else:
                                canonical_path = build_canonical_gdrive_path(rel_path, item.name, domain, category)

                            cur = conn.execute(
                                """
                                INSERT INTO files (
                                    sha256, fast_hash, file_name, file_extension, canonical_gdrive_path,
                                    size_bytes, category, domain
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(canonical_gdrive_path) DO UPDATE SET
                                    sha256 = excluded.sha256,
                                    fast_hash = excluded.fast_hash,
                                    size_bytes = excluded.size_bytes
                                RETURNING file_id
                                """,
                                (sha256, fast_hash, item.name, ext, canonical_path, size, category, domain),
                            )
                            file_id = cur.fetchone()["file_id"]

                            existing_inst = conn.execute(
                                "SELECT instance_id FROM source_instances WHERE source_origin = ? AND source_path = ?",
                                (source_origin, str(item)),
                            ).fetchone()
                            if existing_inst:
                                conn.execute(
                                    "UPDATE source_instances SET file_id = ?, last_seen_at = CURRENT_TIMESTAMP WHERE instance_id = ?",
                                    (file_id, existing_inst["instance_id"]),
                                )
                            else:
                                conn.execute(
                                    """
                                    INSERT INTO source_instances (
                                        file_id, source_origin, source_path, is_canonical_source, last_seen_at
                                    ) VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                                    """,
                                    (file_id, source_origin, str(item)),
                                )

                            mtime = item.stat().st_mtime
                            mod_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                            status, reason = classify_lifecycle(mod_dt, domain, item.name, fresh_days, stale_days)
                            conn.execute(
                                """
                                INSERT INTO lifecycle (file_id, status, status_reason, last_validated_at)
                                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                                ON CONFLICT(file_id) DO UPDATE SET
                                    status = excluded.status,
                                    status_reason = excluded.status_reason,
                                    last_validated_at = CURRENT_TIMESTAMP
                                """,
                                (file_id, status, reason),
                            )

                            if category == "movie":
                                title, year = parse_movie_title_and_year(item.name)
                                rating_data = fetch_movie_rating(title, year)
                                tier, _ = evaluate_cloud_placement(rating_data.get("rating", 6.5), rating_data.get("votes", 1000))
                                existing_movie = conn.execute(
                                    "SELECT movie_id FROM movie_curation WHERE file_id = ?", (file_id,)
                                ).fetchone()
                                if existing_movie:
                                    conn.execute(
                                        """
                                        UPDATE movie_curation SET
                                            title = ?, release_year = ?, imdb_id = ?, imdb_rating = ?, imdb_votes = ?,
                                            genres = ?, synopsis = ?, tier_location = ?
                                        WHERE movie_id = ?
                                        """,
                                        (title, year, rating_data.get("imdb_id"), rating_data.get("rating", 6.5),
                                         rating_data.get("votes", 1000), rating_data.get("genres", "Unknown"),
                                         rating_data.get("synopsis", ""), tier, existing_movie["movie_id"]),
                                    )
                                else:
                                    conn.execute(
                                        """
                                        INSERT INTO movie_curation (
                                            file_id, title, release_year, imdb_id, imdb_rating, imdb_votes,
                                            genres, synopsis, tier_location
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """,
                                        (file_id, title, year, rating_data.get("imdb_id"), rating_data.get("rating", 6.5),
                                         rating_data.get("votes", 1000), rating_data.get("genres", "Unknown"),
                                         rating_data.get("synopsis", ""), tier),
                                    )

                            ingested += 1

                            if ingested % 100 == 0:
                                conn.commit()
                                print(f"    -> Ingested {ingested} files ({total_bytes / (1024**2):.1f} MB)...", flush=True)

                        except Exception as e:
                            self.db.log_error(run_id, str(item), "CRAWL_ERROR", str(e))

                conn.commit()

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
