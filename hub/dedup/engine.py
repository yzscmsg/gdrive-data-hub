"""Cross-host deduplication engine and canonical instance selector."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from hub.core.database import Database

HOST_PRIORITY = {
    "LAN_SYNOLOGY": 1,        # Top authority: DS220+ T1 Business / Home
    "LAN_TRUENAS_167": 2,     # High-capacity primary general node
    "LAN_TRUENAS_069": 3,     # Replica / backup node
    "LAN_TRUENAS_101": 4,     # VM scratch / tools
    "LAN_TRUENAS_014": 5,     # Mass download / movie vault
    "DROPBOX": 6,             # External cloud doc
    "ICLOUD": 7,              # External cloud photo
    "GDRIVE_EXISTING": 8,     # Pre-existing cloud file
}


class DedupEngine:
    """Detects identical files via SHA-256 and selects canonical primary instances."""

    def __init__(self, db: Database):
        self.db = db

    def analyze_duplicates(self) -> Dict[str, Any]:
        """Analyze all registered files and return duplicate groups and reclaimable bytes."""
        with self.db.connection() as conn:
            # Find all SHA-256 hashes with more than 1 instance
            query = """
                SELECT f.sha256, f.file_name, f.size_bytes, COUNT(si.instance_id) as instance_count
                FROM files f
                JOIN source_instances si ON f.file_id = si.file_id
                GROUP BY f.sha256
                HAVING COUNT(si.instance_id) > 1
                ORDER BY f.size_bytes * (COUNT(si.instance_id) - 1) DESC
            """
            rows = conn.execute(query).fetchall()

            duplicate_groups = []
            total_reclaimable_bytes = 0

            for r in rows:
                sha = r["sha256"]
                size = r["size_bytes"]
                count = r["instance_count"]
                potential_savings = size * (count - 1)
                total_reclaimable_bytes += potential_savings

                instances = conn.execute(
                    "SELECT source_origin, source_path, is_canonical_source FROM source_instances WHERE file_id IN (SELECT file_id FROM files WHERE sha256 = ?)",
                    (sha,),
                ).fetchall()

                duplicate_groups.append({
                    "sha256": sha,
                    "file_name": r["file_name"],
                    "size_bytes": size,
                    "instance_count": count,
                    "reclaimable_bytes": potential_savings,
                    "instances": [dict(inst) for inst in instances],
                })

            return {
                "duplicate_groups_count": len(duplicate_groups),
                "total_reclaimable_bytes": total_reclaimable_bytes,
                "groups": duplicate_groups,
            }

    def resolve_canonical_sources(self) -> int:
        """
        Evaluate all multi-instance files and set the authoritative canonical source.
        Returns the number of resolved groups.
        """
        with self.db.connection() as conn:
            # Fetch all distinct files with instances
            file_rows = conn.execute("SELECT file_id FROM files").fetchall()
            resolved_count = 0

            for f in file_rows:
                fid = f["file_id"]
                instances = conn.execute(
                    "SELECT instance_id, source_origin, source_path FROM source_instances WHERE file_id = ?",
                    (fid,),
                ).fetchall()

                if not instances:
                    continue

                # Sort instances by host priority: lowest score is highest priority
                sorted_inst = sorted(
                    instances,
                    key=lambda x: (HOST_PRIORITY.get(x["source_origin"], 99), len(x["source_path"])),
                )

                canonical_id = sorted_inst[0]["instance_id"]

                # Mark canonical winner
                conn.execute(
                    "UPDATE source_instances SET is_canonical_source = 1 WHERE instance_id = ?",
                    (canonical_id,),
                )
                # Mark all others non-canonical
                conn.execute(
                    "UPDATE source_instances SET is_canonical_source = 0 WHERE file_id = ? AND instance_id != ?",
                    (fid, canonical_id),
                )
                resolved_count += 1

            return resolved_count
