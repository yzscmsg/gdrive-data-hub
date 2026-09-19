"""Index generator producing browsable INDEX.md and static HTML dashboards."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from hub.core.database import Database


def human_bytes(value: int) -> str:
    num = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if num < 1024 or unit == "PB":
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


class IndexGenerator:
    """Generates human-readable Markdown index documents and static HTML dashboards."""

    def __init__(self, db: Database):
        self.db = db

    def generate_index_markdown(self, output_path: Path | str = "INDEX.md") -> str:
        """Generate master INDEX.md summarizing data taxonomy, metrics, and lifecycle status."""
        stats = self.db.get_storage_stats()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "# Google Drive Data Hub — Master Index & Governance Catalog",
            f"*Generated: {now}*",
            "",
            "## Storage & Consolidation Overview",
            f"- **Total Canonical Files Registered**: {stats['total_files']:,}",
            f"- **Total Staged Volume**: {human_bytes(stats['total_bytes'])} (Google Drive Pro 5 TB Quota)",
            f"- **Cross-Host Duplicates Pruned**: {stats['duplicate_instances_pruned']:,} instances",
            "",
            "## Domain Breakdown",
            "| Domain | Target Folder | Files | Volume |",
            "|---|---|---:|---:|",
        ]

        for domain, ddata in sorted(stats["by_domain"].items()):
            lines.append(f"| `{domain}` | `0{domain.upper()}` | {ddata['count']:,} | {human_bytes(ddata['bytes'])} |")

        lines += [
            "",
            "## Document Lifecycle & Validation Health",
            "| Status | Meaning | Files | Volume |",
            "|---|---|---:|---:|",
        ]

        descriptions = {
            "fresh": "Actively updated (<180 days)",
            "stable": "Finalized golden records / permanent contracts",
            "lack_of_update": "Unreviewed for >365 days (Action needed)",
            "obsolete": "Superseded / Deprecated / Staged for archive",
        }

        for status, sdata in sorted(stats["by_status"].items()):
            desc = descriptions.get(status, "General")
            lines.append(f"| **`{status}`** | {desc} | {sdata['count']:,} | {human_bytes(sdata['bytes'])} |")

        lines += [
            "",
            "## LAN Node Specialization Matrix",
            "- **Document NAS** (`10.65.1.53`, Synology DS220+): T1 Business, LifeOS evidence, and project repositories.",
            "- **Media NAS** (`192.168.0.167`, TrueNAS bare-metal): Curated photos, personal music, and home video.",
            "- **Cinema Vault** (`192.168.0.14`, TrueNAS mass storage): Bulk movie library and torrent downloads.",
            "",
            "---",
            "*Managed continuously by `gdrive-data-hub`*",
        ]

        content = "\n".join(lines)
        Path(output_path).write_text(content, encoding="utf-8")
        return content

    def generate_static_html_dashboard(self, output_path: Path | str = "dashboard.html") -> str:
        """Generate self-contained static HTML dashboard for cloud inspection."""
        stats = self.db.get_storage_stats()
        recent_runs = self.db.get_recent_runs(limit=10)
        recent_errors = self.db.get_unresolved_errors(limit=10)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        quota_bytes = self.db.get_config("gdrive_storage_quota_bytes", 5 * 1024**4)
        used_bytes = stats["total_bytes"]
        used_pct = (used_bytes / quota_bytes * 100) if quota_bytes > 0 else 0

        fresh_count = stats["by_status"].get("fresh", {}).get("count", 0)
        stale_count = stats["by_status"].get("lack_of_update", {}).get("count", 0)
        golden_count = stats["by_status"].get("stable", {}).get("count", 0)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Drive Data Hub — Management Portal</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        .badge {{ background: #22c55e; color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; }}
        .card h3 {{ margin-top: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; }}
        .card .value {{ font-size: 28px; font-weight: bold; color: #38bdf8; margin: 8px 0; }}
        .progress-bar {{ background: #334155; border-radius: 4px; height: 12px; overflow: hidden; margin-top: 8px; }}
        .progress-fill {{ background: #38bdf8; height: 100%; width: {min(used_pct, 100):.1f}%; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; font-size: 14px; }}
        th {{ color: #94a3b8; font-weight: 600; }}
        .status-fresh {{ color: #4ade80; }}
        .status-stable {{ color: #38bdf8; }}
        .status-stale {{ color: #facc15; }}
        .status-obsolete {{ color: #f87171; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 style="margin:0;">Data Hub Management Portal</h1>
                <div style="color: #94a3b8; margin-top: 4px;">Google Drive (5TB Pro) &amp; LAN NAS Governance</div>
            </div>
            <span class="badge">Operational</span>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Google Drive 5TB Quota</h3>
                <div class="value">{human_bytes(used_bytes)} / {human_bytes(quota_bytes)}</div>
                <div class="progress-bar"><div class="progress-fill"></div></div>
                <div style="color: #94a3b8; font-size: 12px; margin-top: 6px;">{used_pct:.1f}% used &bull; {human_bytes(max(0, quota_bytes - used_bytes))} free headroom</div>
            </div>
            <div class="card">
                <h3>Canonical Files Cataloged</h3>
                <div class="value">{stats['total_files']:,}</div>
                <div style="color: #94a3b8; font-size: 12px;">{stats['duplicate_instances_pruned']:,} duplicate instances pruned</div>
            </div>
            <div class="card">
                <h3>Document Health (Fresh vs Stale)</h3>
                <div class="value" style="color: #4ade80;">{fresh_count:,} <span style="font-size: 16px; color: #94a3b8;">fresh</span></div>
                <div style="color: #facc15; font-size: 12px;">{stale_count:,} unreviewed &bull; {golden_count:,} golden</div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 24px;">
            <h3>Recent Job Executions</h3>
            <table>
                <thead>
                    <tr>
                        <th>Job Run ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Started At</th>
                        <th>Files Processed</th>
                        <th>Bytes Transferred</th>
                    </tr>
                </thead>
                <tbody>
"""
        if recent_runs:
            for r in recent_runs:
                html += f"""
                    <tr>
                        <td>#{r['run_id']}</td>
                        <td><code>{r['job_type']}</code></td>
                        <td><strong>{r['status']}</strong></td>
                        <td>{r['started_at']}</td>
                        <td>{r['files_ingested']:,}</td>
                        <td>{human_bytes(r['bytes_transferred'])}</td>
                    </tr>
                """
        else:
            html += "<tr><td colspan='6' style='text-align:center; color:#64748b;'>No recent runs logged. System standing by.</td></tr>"

        html += f"""
                </tbody>
            </table>
        </div>

        <div style="text-align: center; color: #64748b; font-size: 12px;">
            Last updated: {now} &bull; Generated by gdrive-data-hub
        </div>
    </div>
</body>
</html>
"""
        Path(output_path).write_text(html, encoding="utf-8")
        return html
