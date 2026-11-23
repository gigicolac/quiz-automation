import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import channel_stats as cs  # noqa: E402


class Summarise(unittest.TestCase):
    def test_totals_and_weighted_ctr(self):
        rows = [
            {"views": 10, "estimatedMinutesWatched": 120, "subscribersGained": 3, "subscribersLost": 1,
             "videoThumbnailImpressions": 1000, "videoThumbnailImpressionsClickRate": 0.02},
            {"views": 5, "estimatedMinutesWatched": 60, "subscribersGained": 0, "subscribersLost": 0,
             "videoThumbnailImpressions": 1000, "videoThumbnailImpressionsClickRate": 0.04},
        ]
        s = cs.summarise(rows)
        self.assertEqual((s["views"], s["watch_hours"], s["subs_net"], s["impressions"]), (15, 3.0, 2, 2000))
        self.assertAlmostEqual(s["ctr"], 0.03)

    def test_no_impressions_means_no_ctr(self):
        self.assertNotIn("ctr", cs.summarise([{"views": 1, "estimatedMinutesWatched": 1}]))


if __name__ == "__main__":
    unittest.main()
