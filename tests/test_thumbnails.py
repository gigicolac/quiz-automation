import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_thumbnails as mt  # noqa: E402

FONTS = os.path.exists(mt.SANS) and os.path.exists(mt.SERIF_I)


@unittest.skipUnless(FONTS, "thumbnail fonts not installed")
class Thumbnails(unittest.TestCase):
    def tiles(self):
        return [Image.new("RGB", (480, 270), (i * 20, 100, 200 - i * 10)) for i in range(12)]

    def test_heading_fills_the_width_for_short_and_long_series(self):
        for series in ("TV", "Disney", "General Knowledge"):
            parts, w, h = mt.fit_heading(series, 12, mt.W - 2 * mt.MARGIN, mt.TOP * 0.86)
            self.assertLessEqual(w, mt.W - 2 * mt.MARGIN)
            self.assertLessEqual(h, mt.TOP * 0.86)
            # either the width or the height is the limit, so the text is as big as it can be
            self.assertTrue(w > (mt.W - 2 * mt.MARGIN) * 0.93 or h > mt.TOP * 0.86 * 0.93, series)

    def test_output_is_2560x1440_and_under_2mb(self):
        img = mt.render({"series": "Disney", "number": 10}, self.tiles(), "red", "Only REAL fans know")
        self.assertEqual(img.size, (2560, 1440))
        with tempfile.TemporaryDirectory() as d:
            q, n = mt.save(img, Path(d) / "a.jpg")
            self.assertLessEqual(n, mt.MAX_BYTES)


if __name__ == "__main__":
    unittest.main()
