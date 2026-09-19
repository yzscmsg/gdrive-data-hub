"""Database abstraction layer for gdrive-data-hub central catalog."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from hub.core.config import DEFAULT_DB_PATH, DEFAULTS, cast_value

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schema" / "schema.sql"
SEED_PATH = Path(__file__).resolve().parent.parent.parent / "schema" / "seed_config.sql"


class Database:
    """SQLite database manager for catalog, lineage, telemetry, and configuration."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize database tables and initial configuration seed if not present."""
        with self.connection() as conn:
            if SCHEMA_PATH.exists():
                conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            if SEED_PATH.exists():
                conn.executescript(SEED_PATH.read_text(encoding="utf-8"))

    # --------------------------------------------------------------------------
    # Configuration Queries
    # --------------------------------------------------------------------------

    def get_config(self, key: str, default: Any = None) -> Any:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT config_value, value_type FROM system_config WHERE config_key = ?",
                (key,),
            ).fetchone()
            if row:
                return cast_value(row["config_value"], row["value_type"])
            return default if default is not None else DEFAULTS.get(key)

    def get_all_config(self) -> Dict[str, Any]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT config_key, config_value, value_type, description FROM system_config"
            ).fetchall()
            result = dict(DEFAULTS)
            for row in rows:
                result[row["config_key"]] = cast_value(row["config_value"], row["value_type"])
            return result

    def set_config(self, key: str, value: Any, description: Optional[str] = None) -> None:
        val_str = str(value)
        val_type = "string"
        if isinstance(value, bool):
            val_type = "bool"
            val_str = "true" if value else "false"
        elif isinstance(value, int):
            val_type = "int"
        elif isinstance(value, float):
            val_type = "float"

        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO system_config (config_key, config_value, value_type, description, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(config_key) DO UPDATE SET
                    config_value = excluded.config_value,
                    value_type = excluded.value_type,
                    description = COALESCE(excluded.description, system_config.description),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, val_str, val_type, description),
            )

    # --------------------------------------------------------------------------
    # File & Instance Registration
    # --------------------------------------------------------------------------

    def register_file(
        self,
        sha256: str,
        file_name: str,
        canonical_gdrive_path: str,
        size_bytes: int,
        category: str,
        domain: str,
        fast_hash: Optional[str] = None,
        file_extension: Optional[str] = None,
        mime_type: Optional[str] = None,
        created_at: Optional[str] = None,
        modified_at: Optional[str] = None,
        gdrive_file_id: Optional[str] = None,
    ) -> int:
        """Register or update a canonical file record."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO files (
                    sha256, fast_hash, file_name, file_extension, canonical_gdrive_path,
                    size_bytes, mime_type, created_at, modified_at, gdrive_file_id,
                    category, domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_gdrive_path) DO UPDATE SET
                    sha256 = excluded.sha256,
                    fast_hash = excluded.fast_hash,
                    size_bytes = excluded.size_bytes,
                    modified_at = excluded.modified_at,
                    gdrive_file_id = COALESCE(excluded.gdrive_file_id, files.gdrive_file_id)
                RETURNING file_id
                """,
                (
                    sha256,
                    fast_hash,
                    file_name,
                    file_extension,
                    canonical_gdrive_path,
                    size_bytes,
                    mime_type,
                    created_at,
                    modified_at,
                    gdrive_file_id,
                    category,
                    domain,
                ),
            )
            row = cursor.fetchone()
            return int(row["file_id"])

    def add_source_instance(
        self,
        file_id: int,
        source_origin: str,
        source_path: str,
        is_canonical_source: bool = False,
    ) -> None:
        """Record physical or cloud location for a file instance."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO source_instances (
                    file_id, source_origin, source_path, is_canonical_source, last_seen_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (file_id, source_origin, source_path, int(is_canonical_source)),
            )

    def set_lifecycle(
        self,
        file_id: int,
        status: str,
        status_reason: Optional[str] = None,
        review_due_date: Optional[str] = None,
        owner: str = "administrator",
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO lifecycle (file_id, status, status_reason, review_due_date, owner, last_validated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_id) DO UPDATE SET
                    status = excluded.status,
                    status_reason = excluded.status_reason,
                    review_due_date = excluded.review_due_date,
                    last_validated_at = CURRENT_TIMESTAMP
                """,
                (file_id, status, status_reason, review_due_date, owner),
            )

    # --------------------------------------------------------------------------
    # Telemetry & Error Logging (Portal Support)
    # --------------------------------------------------------------------------

    def start_job(self, job_type: str) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO job_runs (job_type, started_at, status)
                VALUES (?, CURRENT_TIMESTAMP, 'RUNNING')
                RETURNING run_id
                """,
                (job_type,),
            )
            return int(cursor.fetchone()["run_id"])

    def finish_job(
        self,
        run_id: int,
        status: str,
        files_scanned: int = 0,
        files_ingested: int = 0,
        duplicates_detected: int = 0,
        bytes_transferred: int = 0,
        summary_message: Optional[str] = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE job_runs SET
                    finished_at = CURRENT_TIMESTAMP,
                    status = ?,
                    files_scanned = ?,
                    files_ingested = ?,
                    duplicates_detected = ?,
                    bytes_transferred = ?,
                    summary_message = ?
                WHERE run_id = ?
                """,
                (
                    status,
                    files_scanned,
                    files_ingested,
                    duplicates_detected,
                    bytes_transferred,
                    summary_message,
                    run_id,
                ),
            )

    def log_error(
        self,
        run_id: int,
        file_path: Optional[str],
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO job_errors (run_id, file_path, error_type, error_message, stack_trace)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, file_path, error_type, error_message, stack_trace),
            )

    def get_recent_runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT run_id, job_type, started_at, finished_at, status,
                       files_scanned, files_ingested, duplicates_detected,
                       bytes_transferred, summary_message
                FROM job_runs
                ORDER BY run_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_unresolved_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT error_id, run_id, file_path, error_type, error_message, occurred_at
                FROM job_errors
                WHERE is_resolved = 0
                ORDER BY error_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_storage_stats(self) -> Dict[str, Any]:
        """Aggregate file counts and byte sums by domain, category, and lifecycle status."""
        with self.connection() as conn:
            total_row = conn.execute(
                "SELECT COUNT(*) as file_count, COALESCE(SUM(size_bytes), 0) as total_bytes FROM files"
            ).fetchone()

            domain_rows = conn.execute(
                "SELECT domain, COUNT(*) as count, SUM(size_bytes) as bytes FROM files GROUP BY domain"
            ).fetchall()

            status_rows = conn.execute(
                """
                SELECT l.status, COUNT(*) as count, SUM(f.size_bytes) as bytes
                FROM files f
                JOIN lifecycle l ON f.file_id = l.file_id
                GROUP BY l.status
                """
            ).fetchall()

            dups_row = conn.execute(
                """
                SELECT COUNT(*) as dup_instances
                FROM source_instances
                WHERE is_canonical_source = 0
                """
            ).fetchone()

            return {
                "total_files": total_row["file_count"],
                "total_bytes": total_row["total_bytes"],
                "duplicate_instances_pruned": dups_row["dup_instances"],
                "by_domain": {r["domain"]: {"count": r["count"], "bytes": r["bytes"]} for r in domain_rows},
                "by_status": {r["status"]: {"count": r["count"], "bytes": r["bytes"]} for r in status_rows},
            }
