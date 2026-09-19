"""Disaster recovery and one-click cloud re-hydration engine for replacement NAS nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hub.core.database import Database
from hub.scanner.hasher import compute_sha256


class NodeRestoreEngine:
    """Streams canonical files from Google Drive to re-hydrate a failed or replacement LAN NAS node."""

    def __init__(self, db: Database, remote_name: str = "gdrive:"):
        self.db = db
        self.remote_name = remote_name

    def plan_restore(self, role: str, target_dir: Path | str) -> Dict[str, Any]:
        """
        Compute the list of files to download from Google Drive to re-hydrate a specific node role.
        Supported roles: 'doc_nas', 'media_nas', 'all'.
        """
        target = Path(target_dir)

        domain_filter = []
        category_filter = []

        if role == "doc_nas":
            domain_filter = ["business", "lifeos", "projects", "knowledge"]
        elif role == "media_nas":
            category_filter = ["photo", "music"]
        elif role == "all":
            pass
        else:
            raise ValueError(f"Unknown node role: {role}. Must be doc_nas, media_nas, or all.")

        with self.db.connection() as conn:
            query = "SELECT file_id, file_name, canonical_gdrive_path, size_bytes, sha256, domain, category FROM files WHERE 1=1"
            params = []

            if domain_filter:
                placeholders = ",".join("?" * len(domain_filter))
                query += f" AND domain IN ({placeholders})"
                params.extend(domain_filter)

            if category_filter:
                placeholders = ",".join("?" * len(category_filter))
                query += f" AND category IN ({placeholders})"
                params.extend(category_filter)

            rows = conn.execute(query, params).fetchall()

            tasks = []
            total_bytes = 0
            for r in rows:
                total_bytes += r["size_bytes"]
                tasks.append({
                    "file_id": r["file_id"],
                    "file_name": r["file_name"],
                    "cloud_source": f"{self.remote_name}{r['canonical_gdrive_path']}",
                    "local_target": str(target / r["canonical_gdrive_path"]),
                    "size_bytes": r["size_bytes"],
                    "expected_sha256": r["sha256"],
                })

            return {
                "role": role,
                "target_directory": str(target),
                "total_files": len(tasks),
                "total_bytes": total_bytes,
                "tasks": tasks,
            }

    def verify_restored_file(self, local_path: Path | str, expected_sha256: str) -> bool:
        """Verify downloaded file matches the cryptographic hash recorded in catalog.db."""
        path = Path(local_path)
        if not path.exists():
            return False
        computed = compute_sha256(path)
        return computed == expected_sha256
