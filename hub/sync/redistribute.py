"""Weekly reverse redistribution engine placing cloud and remote files into designated LAN NAS nodes."""

from __future__ import annotations

from typing import Any, Dict, List
from hub.core.database import Database


class RedistributionPlanner:
    """Computes downstream tasks to copy cloud-added or relocated files to designated LAN NAS nodes."""

    def __init__(self, db: Database):
        self.db = db

    def generate_redistribution_plan(self) -> Dict[str, Any]:
        """
        Scan files in catalog and determine which files need to be synchronized down
        to their designated LAN NAS role.
        """
        doc_ip = self.db.get_config("lan_node_doc_ip", "10.65.1.53")
        media_ip = self.db.get_config("lan_node_media_ip", "192.168.0.167")
        movie_ip = self.db.get_config("lan_node_movie_ip", "192.168.0.69")

        with self.db.connection() as conn:
            # Fetch files that are in cloud or external source but missing on their target LAN role
            files = conn.execute(
                """
                SELECT f.file_id, f.file_name, f.canonical_gdrive_path, f.category, f.domain, f.size_bytes
                FROM files f
                """
            ).fetchall()

            doc_tasks: List[Dict[str, Any]] = []
            media_tasks: List[Dict[str, Any]] = []
            movie_tasks: List[Dict[str, Any]] = []

            for f in files:
                fid = f["file_id"]
                domain = f["domain"]
                category = f["category"]

                # Check instances on LAN
                instances = conn.execute(
                    "SELECT source_origin FROM source_instances WHERE file_id = ?",
                    (fid,),
                ).fetchall()
                origins = {inst["source_origin"] for inst in instances}

                # Rule 1: Business and LifeOS belong on Document NAS (Synology)
                if domain in ("business", "lifeos", "projects", "knowledge") and "LAN_SYNOLOGY" not in origins:
                    doc_tasks.append({
                        "file_id": fid,
                        "file_name": f["file_name"],
                        "gdrive_path": f["canonical_gdrive_path"],
                        "target_node": doc_ip,
                        "target_share": f"smb://{doc_ip}/data/{f['canonical_gdrive_path']}",
                        "size_bytes": f["size_bytes"],
                    })

                # Rule 2: Photos and Music belong on Media NAS
                elif category in ("photo", "music") and "LAN_TRUENAS_167" not in origins:
                    media_tasks.append({
                        "file_id": fid,
                        "file_name": f["file_name"],
                        "gdrive_path": f["canonical_gdrive_path"],
                        "target_node": media_ip,
                        "target_share": f"smb://{media_ip}/Share/Media/{category.title()}/{f['file_name']}",
                        "size_bytes": f["size_bytes"],
                    })

                # Rule 3: Movies belong on Cinema Vault (192.168.0.69)
                elif category == "movie" and "LAN_TRUENAS_069" not in origins:
                    movie_tasks.append({
                        "file_id": fid,
                        "file_name": f["file_name"],
                        "gdrive_path": f["canonical_gdrive_path"],
                        "target_node": movie_ip,
                        "target_share": f"smb://{movie_ip}/Movie/{f['file_name']}",
                        "size_bytes": f["size_bytes"],
                    })

            # Rule 4: TrueNAS 167 Satellite Edge Cache (Office B fast workspace)
            # Replicates:
            #   a) Active business/knowledge documents with lifecycle = 'fresh' (<180d)
            #   b) Curated operational tools/utilities (software category)
            # Main authoritative station remains Synology DS220+ (10.65.1.53)
            edge_tasks: List[Dict[str, Any]] = []
            edge_enabled = self.db.get_config("edge_167_cache_enabled", True)
            if edge_enabled:
                edge_include_tools = self.db.get_config("edge_167_include_tools", True)
                edge_quota_bytes = self.db.get_config("edge_167_max_quota_gb", 50) * (1024**3)
                current_edge_bytes = 0

                fresh_candidates = conn.execute(
                    """
                    SELECT f.file_id, f.file_name, f.canonical_gdrive_path, f.category, f.domain, f.size_bytes, l.status
                    FROM files f
                    JOIN lifecycle l ON f.file_id = l.file_id
                    WHERE (
                        (f.domain IN ('business', 'knowledge') AND l.status = 'fresh')
                        OR (? AND f.domain = 'software' AND f.category IN ('software', 'doc'))
                    )
                    ORDER BY f.modified_at DESC
                    """,
                    (1 if edge_include_tools else 0,),
                ).fetchall()

                for f in fresh_candidates:
                    fid = f["file_id"]
                    instances = conn.execute(
                        "SELECT source_origin FROM source_instances WHERE file_id = ?",
                        (fid,),
                    ).fetchall()
                    origins = {inst["source_origin"] for inst in instances}

                    if "LAN_TRUENAS_167_CACHE" not in origins:
                        if current_edge_bytes + f["size_bytes"] <= edge_quota_bytes:
                            edge_tasks.append({
                                "file_id": fid,
                                "file_name": f["file_name"],
                                "gdrive_path": f["canonical_gdrive_path"],
                                "target_node": media_ip,
                                "target_share": f"smb://{media_ip}/fast-workspace/{f['canonical_gdrive_path']}",
                                "size_bytes": f["size_bytes"],
                                "cache_reason": "Fresh Working Set (<180d)" if f["domain"] != "software" else "Curated Toolchain",
                            })
                            current_edge_bytes += f["size_bytes"]

            return {
                "total_redistribution_tasks": len(doc_tasks) + len(media_tasks) + len(movie_tasks) + len(edge_tasks),
                "doc_nas_tasks": doc_tasks,
                "media_nas_tasks": media_tasks,
                "cinema_vault_tasks": movie_tasks,
                "edge_167_cache_tasks": edge_tasks,
            }
