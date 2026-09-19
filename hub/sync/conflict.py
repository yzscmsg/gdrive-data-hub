"""Bidirectional conflict detector and non-destructive version branching manager."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from hub.core.database import Database


class ConflictManager:
    """Detects and safely resolves concurrent edits between LAN NAS and Google Drive."""

    def __init__(self, db: Database):
        self.db = db

    def check_conflict(
        self,
        file_id: int,
        lan_path: str,
        cloud_path: str,
        lan_sha256: str,
        cloud_sha256: str,
        lan_mtime: datetime,
        cloud_mtime: datetime,
        base_mtime: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[int]]:
        """
        Evaluate if a bidirectional edit conflict exists.
        Returns (is_conflict, conflict_id).
        """
        # If hashes match, they are identical -> no conflict
        if lan_sha256 == cloud_sha256:
            return False, None

        # If both LAN and Cloud modified after the baseline sync time
        # or if hashes diverge significantly
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sync_conflicts (
                    file_id, lan_source, cloud_source, lan_mtime, cloud_mtime,
                    lan_sha256, cloud_sha256, resolution
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
                RETURNING conflict_id
                """,
                (
                    file_id,
                    lan_path,
                    cloud_path,
                    lan_mtime.isoformat() if lan_mtime else None,
                    cloud_mtime.isoformat() if cloud_mtime else None,
                    lan_sha256,
                    cloud_sha256,
                ),
            )
            conflict_id = int(cursor.fetchone()["conflict_id"])
            return True, conflict_id

    def resolve_conflict(self, conflict_id: int, resolution: str) -> Dict[str, Any]:
        """
        Resolve conflict using specified strategy:
        - 'ACCEPT_LAN': LAN version becomes canonical; cloud version archived.
        - 'ACCEPT_CLOUD': Cloud version becomes canonical; LAN version updated.
        - 'BRANCH_BOTH': Both versions preserved side-by-side with clear origin tags.
        """
        if resolution not in ("ACCEPT_LAN", "ACCEPT_CLOUD", "BRANCH_BOTH"):
            raise ValueError(f"Invalid resolution strategy: {resolution}")

        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE sync_conflicts SET
                    resolution = ?,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE conflict_id = ?
                """,
                (resolution, conflict_id),
            )
            return {
                "conflict_id": conflict_id,
                "resolution": resolution,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }

    def generate_branch_names(self, original_filename: str) -> Tuple[str, str]:
        """Generate non-colliding branch filenames for concurrent versions."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if "." in original_filename:
            stem, ext = original_filename.rsplit(".", 1)
            return f"{stem}_lan_{ts}.{ext}", f"{stem}_gdrive_{ts}.{ext}"
        return f"{original_filename}_lan_{ts}", f"{original_filename}_gdrive_{ts}"
