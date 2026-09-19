"""Configuration manager loading and updating operational parameters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_DB_PATH = Path("data/catalog.db")

DEFAULTS = {
    "imdb_rating_threshold": 7.8,
    "imdb_votes_threshold": 25000,
    "imdb_top250_force_include": True,
    "ingest_schedule_cron": "0 2 * * *",
    "redistribute_schedule_cron": "0 3 * * 0",
    "bandwidth_limit_day_mb": 5,
    "bandwidth_limit_night_mb": 50,
    "lifecycle_fresh_days": 180,
    "lifecycle_stale_days": 365,
    "gdrive_storage_quota_bytes": 5 * 1024 * 1024 * 1024 * 1024,
    "gdrive_warning_threshold_pct": 75,
    "gdrive_critical_threshold_pct": 85,
    "conflict_resolution_policy": "BRANCH_BOTH",
    "lan_node_doc_ip": "10.65.1.53",
    "lan_node_media_ip": "192.168.0.167",
    "lan_node_movie_ip": "192.168.0.69",
}


def cast_value(raw: str, value_type: str) -> Any:
    """Safely cast raw string from database into specified Python type."""
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "bool":
        return raw.strip().lower() in ("true", "1", "yes")
    if value_type == "json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw
