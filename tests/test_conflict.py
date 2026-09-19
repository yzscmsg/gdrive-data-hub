"""Unit tests for bidirectional sync conflict manager."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from hub.core.database import Database
from hub.sync.conflict import ConflictManager


class TestConflict(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "conflict.db")
        self.manager = ConflictManager(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_conflict_detection_and_branching(self):
        now = datetime.now(timezone.utc)
        file_id = self.db.register_file(
            sha256="base_sha",
            file_name="ledger_2026.xlsx",
            canonical_gdrive_path="01_BUSINESS/Accounting_Finance/ledger_2026.xlsx",
            size_bytes=50000,
            category="doc",
            domain="business",
        )

        # 1. Matching hashes -> No conflict
        is_conf, cid = self.manager.check_conflict(
            file_id=file_id,
            lan_path="/volume1/Account/ledger_2026.xlsx",
            cloud_path="01_BUSINESS/Accounting_Finance/ledger_2026.xlsx",
            lan_sha256="same_sha",
            cloud_sha256="same_sha",
            lan_mtime=now,
            cloud_mtime=now,
        )
        self.assertFalse(is_conf)
        self.assertIsNone(cid)

        # 2. Diverging hashes -> Conflict created
        is_conf2, cid2 = self.manager.check_conflict(
            file_id=file_id,
            lan_path="/volume1/Account/ledger_2026.xlsx",
            cloud_path="01_BUSINESS/Accounting_Finance/ledger_2026.xlsx",
            lan_sha256="lan_edit_sha",
            cloud_sha256="cloud_edit_sha",
            lan_mtime=now,
            cloud_mtime=now,
        )
        self.assertTrue(is_conf2)
        self.assertIsInstance(cid2, int)

        # 3. Resolve conflict with BRANCH_BOTH
        res = self.manager.resolve_conflict(cid2, "BRANCH_BOTH")
        self.assertEqual(res["resolution"], "BRANCH_BOTH")

        # 4. Generate branch filenames
        lan_branch, cloud_branch = self.manager.generate_branch_names("ledger_2026.xlsx")
        self.assertIn("ledger_2026_lan_", lan_branch)
        self.assertIn("ledger_2026_gdrive_", cloud_branch)


if __name__ == "__main__":
    unittest.main()
