"""Document and media classification rules engine."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from hub.classifier.taxonomy import TAXONOMY_DOMAINS, get_category_from_extension


def classify_domain(path_str: str, file_name: str) -> str:
    """Classify the target domain based on source path and file name heuristics."""
    normalized = f"{path_str}/{file_name}".lower().replace("\\", "/")

    # 1. Business / Corporate
    if any(k in normalized for k in ("account", "finance", "invoice", "payroll", "hr", "odoo", "tax", "erp", "sales-ops", "purchasing", "contracts")):
        return "business"

    # 2. LifeOS / Personal Family
    if any(k in normalized for k in ("lifeos", "kelly", "family", "evidence", "medical", "passport", "household", "insurance")):
        return "lifeos"

    # 3. Projects / Source Code
    if any(k in normalized for k in ("git", "repository", "repo", "architecture", "adr", "workspace", "src", "code", "dev")):
        return "projects"

    # 4. Knowledge Base / Training
    if any(k in normalized for k in ("training", "jda", "sbd", "ebook", "manual", "guide", "documentation", "whitepaper", "research")):
        return "knowledge"

    # 5. Software Tools / Installers
    if any(k in normalized for k in ("wininstall", "oracle", "client", "service update", "tools/win", "tools/vm", "driver")):
        return "software"

    # 6. Media (Photo, Music, Movies)
    if any(k in normalized for k in ("photo", "picture", "music", "audio", "movie", "cinema", "video", "downloadqb")):
        return "media"

    # 7. Archives / Legacy Backups
    if any(k in normalized for k in ("netbackup", "backupdata", "vmback", "archive", "quarantine", "old")):
        return "archive"

    return "business"  # Safe default


def build_canonical_gdrive_path(source_path: str, file_name: str, domain: str, category: str) -> str:
    """Construct the standardized Google Drive destination path."""
    root_folder = TAXONOMY_DOMAINS.get(domain, "07_ARCHIVE")

    # Format clean subfolder
    subfolder = "General"
    lowered = source_path.lower().replace("\\", "/")

    if domain == "business":
        if "account" in lowered or "finance" in lowered or "invoice" in lowered:
            subfolder = "Accounting_Finance"
        elif "hr" in lowered or "contract" in lowered or "legal" in lowered:
            subfolder = "HR_Legal"
        elif "odoo" in lowered:
            subfolder = "Odoo_ERP"
        else:
            subfolder = "Operations_General"

    elif domain == "lifeos":
        if "evidence" in lowered or "medical" in lowered:
            subfolder = "Evidence"
        elif "kelly" in lowered or "family" in lowered:
            subfolder = "Family_Archives"
        else:
            subfolder = "Household_Ops"

    elif domain == "media":
        if category == "photo":
            subfolder = "Photos"
        elif category == "music":
            subfolder = "Music"
        elif "personal" in lowered or "family" in lowered:
            subfolder = "Personal_Video"
        else:
            subfolder = "Curated_Cinema"

    elif domain == "software":
        if "oracle" in lowered or "patch" in lowered or "update" in lowered:
            subfolder = "Enterprise_Patches"
        elif "win" in lowered or "iso" in lowered:
            subfolder = "Curated_OS_Images"
        else:
            subfolder = "Dev_Tools_Utilities"

    return f"{root_folder}/{subfolder}/{file_name}"


def classify_lifecycle(
    modified_time: Optional[datetime],
    domain: str,
    file_name: str,
    fresh_days: int = 180,
    stale_days: int = 365,
) -> Tuple[str, str]:
    """
    Classify lifecycle state: ('fresh', 'stable', 'lack_of_update', 'obsolete') with rationale.
    """
    lowered_name = file_name.lower()

    # Obsolete checks
    if any(k in lowered_name for k in (".tmp", "temp", "scratch", "corrupt", "old_v", "superseded", ".~tmp~")):
        return "obsolete", "Temporary or explicitly superseded file"

    if modified_time is None:
        return "lack_of_update", "No modification date recorded"

    now = datetime.now(timezone.utc)
    if modified_time.tzinfo is None:
        modified_time = modified_time.replace(tzinfo=timezone.utc)

    age_days = (now - modified_time).days

    # Stable Golden Records
    if any(k in lowered_name for k in ("contract", "agreement", "certificate", "adr-", "constitution", "final_signed", "tax_return")):
        return "stable", "Permanent legal/contractual/architectural golden record"

    # Fresh
    if age_days <= fresh_days:
        return "fresh", f"Active record modified within {age_days} days (< {fresh_days}d threshold)"

    # Lack of update
    if age_days > stale_days:
        if domain in ("business", "lifeos", "projects"):
            return "lack_of_update", f"Active domain document with no updates in {age_days} days (> {stale_days}d threshold)"
        return "stable", f"Unchanged reference content ({age_days} days old)"

    return "stable", f"Standard operational document ({age_days} days old)"
