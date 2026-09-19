"""Unit tests for IMDb movie parser and placement evaluator."""

import unittest
from hub.media.imdb import parse_movie_title_and_year, evaluate_cloud_placement, fetch_movie_rating


class TestIMDb(unittest.TestCase):
    def test_parse_movie_title_and_year(self):
        title, year = parse_movie_title_and_year(
            "Blade.Runner.2049.2017.PROPER.2160p.US.BluRay.REMUX.HEVC.DTS-HD.MA.TrueHD.7.1.Atmos-FGT.mkv"
        )
        self.assertEqual(title, "Blade Runner 2049")
        self.assertEqual(year, 2017)

        title2, year2 = parse_movie_title_and_year(
            "Top Gun Maverick (2022) [IMAX] [2160p] [4K] [WEB] [5.1] [YTS.MX].mkv"
        )
        self.assertEqual(title2, "Top Gun Maverick")
        self.assertEqual(year2, 2022)

    def test_evaluate_cloud_placement(self):
        # 8.2 rating with 700k votes -> Cloud and Local
        tier, reason = evaluate_cloud_placement(8.2, 700000, rating_threshold=7.8)
        self.assertEqual(tier, "CLOUD_AND_LOCAL")

        # 6.5 rating -> Local Vault Only
        tier2, reason2 = evaluate_cloud_placement(6.5, 30000, rating_threshold=7.8)
        self.assertEqual(tier2, "LOCAL_VAULT_ONLY")

        # Force Cloud override
        tier3, reason3 = evaluate_cloud_placement(5.0, 100, manual_override="FORCE_CLOUD")
        self.assertEqual(tier3, "CLOUD_AND_LOCAL")


if __name__ == "__main__":
    unittest.main()
