"""Unit tests for deduplication engine and canonical instance resolution."""

import tempfile
import unittest
from pathlib import Path

from hub.core.database import Database
from hub.dedup.engine import DedupEngine


class TestDedup(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "dedup.db")
        self.engine = DedupEngine(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_duplicate_detection_and_resolution(self):
        # Register a file that exists on both Synology and TrueNAS .101
        file_id = self.db.register_file(
            sha256="hash_identical_123",
            file_name="MacOSMonterey.iso",
            canonical_gdrive_path="05_SOFTWARE_TOOLS/Curated_OS_Images/MacOSMonterey.iso",
            size_bytes=14 * 1024**3,  # 14 GB
            category="software",
            domain="software",
        )

        # Instance 1 on TrueNAS (lower priority)
        self.db.add_source_instance(
            file_id=file_id,
            source_origin="LAN_TRUENAS_101",
            source_path="/mnt/Tank/tools/tools/WinInstall/MacOSMonterey.iso",
            is_canonical_source=False,
        )

        # Instance 2 on Synology (higher priority)
        self.db.add_source_instance(
            file_id=file_id,
            source_origin="LAN_SYNOLOGY",
            source_path="/volume1/NetBackup/tools/WinInstall/MacOSMonterey.iso",
            is_canonical_source=False,
        )

        # Run analysis
        analysis = self.engine.analyze_duplicates()
        self.assertEqual(analysis["duplicate_groups_count"], 1)
        self.assertEqual(analysis["total_reclaimable_bytes"], 14 * 1024**3)

        # Run resolution
        resolved = self.engine.resolve_canonical_sources()
        self.assertEqual(resolved, 1)

        # Verify Synology won as canonical
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT source_origin FROM source_instances WHERE file_id = ? AND is_canonical_source = 1",
                (file_id,),
            ).fetchone()
            self.assertEqual(row["source_origin"], "LAN_SYNOLOGY")


if __name__ == "__main__":
    unittest.main()
