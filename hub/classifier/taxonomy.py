"""Taxonomy definitions and destination folder mapping for Google Drive."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

# Google Drive Target Taxonomy Roots
TAXONOMY_DOMAINS = {
    "business": "01_BUSINESS",
    "lifeos": "02_LIFEOS_FAMILY",
    "projects": "03_PROJECTS_CODE",
    "knowledge": "04_KNOWLEDGE_BASE",
    "software": "05_SOFTWARE_TOOLS",
    "media": "06_MEDIA",
    "archive": "07_ARCHIVE",
}

EXTENSION_CATEGORIES = {
    # Documents
    ".pdf": "doc", ".docx": "doc", ".doc": "doc", ".xlsx": "doc", ".xls": "doc",
    ".pptx": "doc", ".ppt": "doc", ".txt": "doc", ".md": "doc", ".csv": "doc",
    ".odt": "doc", ".ods": "doc", ".rtf": "doc",
    # Code & Configs
    ".py": "code", ".js": "code", ".ts": "code", ".html": "code", ".css": "code",
    ".json": "code", ".yaml": "code", ".yml": "code", ".sh": "code", ".ps1": "code",
    ".sql": "code", ".rs": "code", ".go": "code", ".c": "code", ".cpp": "code",
    # Media: Photos
    ".jpg": "photo", ".jpeg": "photo", ".png": "photo", ".heic": "photo",
    ".webp": "photo", ".tiff": "photo", ".raw": "photo", ".cr2": "photo",
    # Media: Audio
    ".mp3": "music", ".flac": "music", ".m4a": "music", ".wav": "music",
    ".aac": "music", ".ogg": "music", ".alac": "music",
    # Media: Video
    ".mp4": "movie", ".mkv": "movie", ".mov": "movie", ".avi": "movie",
    ".webm": "movie", ".m4v": "movie",
    # Software & Installers
    ".iso": "software", ".exe": "software", ".msi": "software", ".zip": "software",
    ".tar.gz": "software", ".tgz": "software", ".7z": "software", ".dmg": "software",
}


def get_category_from_extension(ext: str) -> str:
    """Map file extension to canonical category."""
    return EXTENSION_CATEGORIES.get(ext.lower(), "archive")
