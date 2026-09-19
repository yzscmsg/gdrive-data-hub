"""Unit tests for two-phase streaming hasher."""

import tempfile
import unittest
from pathlib import Path

from hub.scanner.hasher import compute_fast_hash, compute_sha256, hash_file_two_tiered


class TestHasher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "sample.bin"
        # Write 256 KB of dummy data
        self.test_file.write_bytes(b"A" * 128 * 1024 + b"B" * 128 * 1024)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fast_hash_and_sha256(self):
        size = self.test_file.stat().st_size
        self.assertEqual(size, 256 * 1024)

        fast = compute_fast_hash(self.test_file, size)
        self.assertTrue(len(fast) > 0)

        full = compute_sha256(self.test_file)
        self.assertEqual(len(full), 64)  # standard SHA-256 length

        full2, fast2, size2 = hash_file_two_tiered(self.test_file)
        self.assertEqual(full, full2)
        self.assertEqual(fast, fast2)
        self.assertEqual(size, size2)


if __name__ == "__main__":
    unittest.main()
