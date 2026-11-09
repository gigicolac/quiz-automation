import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import upload_shorts as us  # noqa: E402


class DefaultShortsMeta(unittest.TestCase):
    def setUp(self):
        self.scfg = json.loads((ROOT / "config" / "shorts.json").read_text())
        self.quiz = {"series": "Science", "number": 11, "questions": []}
        self.made = [{"short": i, "questions": list(range(7 * i - 6, 7 * i + 1))} for i in range(1, 6)]

    def test_titles_name_the_quiz_and_link_the_full_video(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "upload.json").write_text(json.dumps({"video_id": "abc123"}))
            meta = us.default_meta(self.quiz, Path(d), self.scfg, self.made)
        self.assertEqual(meta["full_quiz_video_id"], "abc123")
        self.assertEqual(meta["series_tag"], "science")
        titles = [s["title"] for s in meta["shorts"].values()]
        self.assertEqual(len(set(titles)), 5)
        for t in titles:
            self.assertTrue(t.endswith("Science Quiz #11"))
            self.assertLessEqual(len(t), 100)
            self.assertNotIn("{n}", t)

    def test_needs_the_full_quiz_uploaded_first(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                us.default_meta(self.quiz, Path(d), self.scfg, self.made)

    def test_cap_is_five_per_quiz(self):
        self.assertEqual(self.scfg["max_shorts_per_quiz"], 5)


if __name__ == "__main__":
    unittest.main()
