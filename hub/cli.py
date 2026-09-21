"""Unified CLI interface for gdrive-data-hub operations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hub.core.database import Database
from hub.scanner.crawler import NASCrawler
from hub.dedup.engine import DedupEngine
from hub.sync.redistribute import RedistributionPlanner
from hub.indexer.generator import IndexGenerator
from hub.ai.extractor import AIExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gdrive-hub",
        description="Continuous Data Governance & Hybrid LAN NAS / Google Drive Cloud Hub CLI",
    )
    parser.add_argument("--db", default="data/catalog.db", help="Path to SQLite catalog database")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. scan
    scan_p = subparsers.add_parser("scan", help="Crawl and catalog a local directory or NAS share")
    scan_p.add_argument("--path", required=True, help="Directory path to scan")
    scan_p.add_argument("--origin", required=True, help="Source origin tag (e.g. LAN_SYNOLOGY, LAN_TRUENAS_167, DROPBOX, ICLOUD)")

    # 2. dedup
    dedup_p = subparsers.add_parser("dedup", help="Analyze and resolve cross-host duplicates")
    dedup_p.add_argument("--resolve", action="store_true", help="Automatically assign canonical source instances")

    # 3. redistribute
    redist_p = subparsers.add_parser("redistribute", help="Generate reverse redistribution plan down to LAN NAS nodes")
    redist_p.add_argument("--plan-only", action="store_true", default=True, help="Print redistribution tasks without executing")

    # 4. index
    index_p = subparsers.add_parser("index", help="Generate master INDEX.md and static HTML dashboard")
    index_p.add_argument("--out-md", default="INDEX.md", help="Output path for INDEX.md")
    index_p.add_argument("--out-html", default="dashboard.html", help="Output path for dashboard.html")

    # 5. verify
    verify_p = subparsers.add_parser("verify", help="Verify candidate document against historical baseline anchors")
    verify_p.add_argument("--input", required=True, help="Path to document to verify")

    # 6. portal
    portal_p = subparsers.add_parser("portal", help="Launch Data Hub Management Portal Web UI")
    portal_p.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    portal_p.add_argument("--port", type=int, default=8080, help="Port to listen on")

    # 7. restore (Disaster Recovery & Re-hydration)
    restore_p = subparsers.add_parser("restore", help="Re-hydrate replacement LAN NAS node from Google Drive")
    restore_p.add_argument("--role", choices=["doc_nas", "media_nas", "all"], required=True, help="Target node role to restore")
    restore_p.add_argument("--target", required=True, help="Local target directory on new NAS")
    restore_p.add_argument("--plan-only", action="store_true", default=True, help="Preview restore plan without downloading")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    db = Database(args.db)

    if args.command == "scan":
        crawler = NASCrawler(db)
        print(f"[*] Scanning {args.path} for origin '{args.origin}'...")
        res = crawler.scan_path(args.path, args.origin)
        print(f"[+] Scan complete: {res.get('files_ingested', 0)} files registered.")
        return 0

    elif args.command == "dedup":
        engine = DedupEngine(db)
        analysis = engine.analyze_duplicates()
        print(f"[+] Found {analysis['duplicate_groups_count']} duplicate groups across estate.")
        print(f"[+] Reclaimable volume: {analysis['total_reclaimable_bytes'] / (1024**3):.2f} GiB.")
        if args.resolve:
            resolved = engine.resolve_canonical_sources()
            print(f"[+] Resolved canonical instances for {resolved} files.")
        return 0

    elif args.command == "redistribute":
        planner = RedistributionPlanner(db)
        plan = planner.generate_redistribution_plan()
        print(f"[+] Total redistribution tasks computed: {plan['total_redistribution_tasks']}")
        print(f"    - Document NAS tasks (Synology): {len(plan['doc_nas_tasks'])}")
        print(f"    - Media NAS tasks (TrueNAS 167): {len(plan['media_nas_tasks'])}")
        print(f"    - Cinema Vault tasks (TrueNAS 069): {len(plan['cinema_vault_tasks'])}")
        print(f"    - TrueNAS 167 Satellite Edge Cache tasks: {len(plan.get('edge_167_cache_tasks', []))}")
        return 0

    elif args.command == "index":
        gen = IndexGenerator(db)
        gen.generate_index_markdown(args.out_md)
        gen.generate_static_html_dashboard(args.out_html)
        print(f"[+] Generated {args.out_md} and {args.out_html}")
        return 0

    elif args.command == "verify":
        extractor = AIExtractor(db)
        text = extractor.extract_text_sample(args.input)
        res = extractor.verify_against_history(text)
        print(f"[+] Verified {args.input}: {res['historical_matches_found']} historical matches found.")
        for match in res["matches"]:
            print(f"    - Matched in {match['file_name']}: {match['matched_anchors']}")
        return 0

    elif args.command == "portal":
        from portal.app import run_portal
        print(f"[*] Starting Data Hub Management Portal on http://{args.host}:{args.port}...")
        run_portal(db, host=args.host, port=args.port)
        return 0

    elif args.command == "restore":
        from hub.sync.restore import NodeRestoreEngine
        engine = NodeRestoreEngine(db)
        plan = engine.plan_restore(args.role, args.target)
        print(f"[+] Disaster Recovery Plan for role '{args.role}':")
        print(f"    - Target directory: {plan['target_directory']}")
        print(f"    - Files to restore: {plan['total_files']}")
        print(f"    - Volume to download: {plan['total_bytes'] / (1024**2):.2f} MB")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
