"""Unit tests for Database manager and catalog schema operations."""

import tempfile
import unittest
from pathlib import Path

from hub.core.database import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_catalog.db"
        self.db = Database(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_and_config(self):
        # Verify default seed config exists
        threshold = self.db.get_config("imdb_rating_threshold")
        self.assertEqual(threshold, 7.8)

        # Update config
        self.db.set_config("imdb_rating_threshold", 8.2)
        self.assertEqual(self.db.get_config("imdb_rating_threshold"), 8.2)

    def test_register_file_and_instance(self):
        file_id = self.db.register_file(
            sha256="abc123sha256",
            file_name="test_doc.pdf",
            canonical_gdrive_path="01_BUSINESS/Accounting_Finance/test_doc.pdf",
            size_bytes=1048576,
            category="doc",
            domain="business",
        )
        self.assertIsInstance(file_id, int)

        # Add source instance
        self.db.add_source_instance(
            file_id=file_id,
            source_origin="LAN_SYNOLOGY",
            source_path="/volume1/Account/test_doc.pdf",
            is_canonical_source=True,
        )

        # Set lifecycle
        self.db.set_lifecycle(file_id, "fresh", "Recently modified test document")

        # Query stats
        stats = self.db.get_storage_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertEqual(stats["total_bytes"], 1048576)
        self.assertIn("business", stats["by_domain"])
        self.assertIn("fresh", stats["by_status"])

    def test_job_telemetry_and_errors(self):
        run_id = self.db.start_job("INGEST_LAN")
        self.assertIsInstance(run_id, int)

        self.db.log_error(run_id, "/path/to/corrupt.bin", "CHECKSUM_ERROR", "Bit flip detected")
        self.db.finish_job(run_id, "WARNING", files_scanned=10, files_ingested=9, summary_message="1 file failed")

        recent_runs = self.db.get_recent_runs(limit=5)
        self.assertEqual(len(recent_runs), 1)
        self.assertEqual(recent_runs[0]["status"], "WARNING")

        errors = self.db.get_unresolved_errors(limit=5)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "CHECKSUM_ERROR")


if __name__ == "__main__":
    unittest.main()
