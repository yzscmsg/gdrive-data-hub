"""Google Drive synchronization engine interface utilizing rclone or API commands."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.core.database import Database


class GDriveSyncEngine:
    """Orchestrates verified binary transfers to Google Drive."""

    def __init__(self, db: Database, remote_name: str = "gdrive:"):
        self.db = db
        self.remote_name = remote_name

    def build_rclone_flags(self) -> List[str]:
        """Construct safety flags preventing format conversion and enforcing bandwidth limits."""
        day_limit = self.db.get_config("bandwidth_limit_day_mb", 5)
        night_limit = self.db.get_config("bandwidth_limit_night_mb", 50)

        # 08:00 to 19:00 = day_limit; 19:00 to 08:00 = night_limit
        bw_schedule = f"08:00,{day_limit}M 19:00,{night_limit}M"

        return [
            "--drive-import-formats=false",   # Crucial: prevents Google Doc auto-conversion
            "--fast-list",                    # Reduces API calls
            f"--bwlimit={bw_schedule}",       # Bandwidth throttling schedule
            "--checksum",                     # Verify hash integrity
            "--transfers=4",                  # Parallel transfer concurrency
            "--checkers=8",
            "--retries=3",
            "--low-level-retries=10",
        ]

    def build_sync_command(self, local_dir: str | Path, remote_folder: str) -> List[str]:
        """Generate the CLI command string to sync a local directory to a Google Drive destination."""
        flags = self.build_rclone_flags()
        target = f"{self.remote_name.rstrip('/')}/{remote_folder.lstrip('/')}"
        return ["rclone", "sync", str(local_dir), target] + flags
