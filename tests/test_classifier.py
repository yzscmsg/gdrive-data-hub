"""Unit tests for classification rules and taxonomy mapper."""

import unittest
from datetime import datetime, timedelta, timezone

from hub.classifier.rules import classify_domain, build_canonical_gdrive_path, classify_lifecycle


class TestClassifier(unittest.TestCase):
    def test_classify_domain(self):
        self.assertEqual(classify_domain("Account/2026", "invoice_102.pdf"), "business")
        self.assertEqual(classify_domain("Kelly Zeng/Doc", "passport.pdf"), "lifeos")
        self.assertEqual(classify_domain("Projects/nas-arch", "architecture.md"), "projects")
        self.assertEqual(classify_domain("Training/2020-JDA", "jda_manual.pdf"), "knowledge")
        self.assertEqual(classify_domain("WinInstall", "Win11_Pro.iso"), "software")
        self.assertEqual(classify_domain("Media/Movie", "Top Gun Maverick.mkv"), "media")

    def test_build_canonical_path(self):
        path = build_canonical_gdrive_path("Account/Invoices", "invoice_001.pdf", "business", "doc")
        self.assertEqual(path, "01_BUSINESS/Accounting_Finance/invoice_001.pdf")

        photo_path = build_canonical_gdrive_path("Photos/2026/Summer", "IMG_001.HEIC", "media", "photo")
        self.assertEqual(photo_path, "06_MEDIA/Photos/IMG_001.HEIC")

    def test_classify_lifecycle(self):
        now = datetime.now(timezone.utc)

        # Fresh (<180 days)
        fresh_time = now - timedelta(days=30)
        status, reason = classify_lifecycle(fresh_time, "business", "q2_report.xlsx")
        self.assertEqual(status, "fresh")

        # Stable golden record
        status, reason = classify_lifecycle(now - timedelta(days=500), "business", "Signed_Partnership_Contract.pdf")
        self.assertEqual(status, "stable")

        # Lack of update (>365 days in active business domain)
        stale_time = now - timedelta(days=400)
        status, reason = classify_lifecycle(stale_time, "business", "unreviewed_notes.docx")
        self.assertEqual(status, "lack_of_update")

        # Obsolete
        status, reason = classify_lifecycle(fresh_time, "business", "draft_temp.tmp")
        self.assertEqual(status, "obsolete")


if __name__ == "__main__":
    unittest.main()
