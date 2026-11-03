import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_video as bv  # noqa: E402


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "config" / "video.json").read_text())
        self.quiz = {"number": 9, "series": "General Knowledge", "questions": [
            {"n": 1, "question": "Capital of Australia?", "answer": "Canberra! 🏛️", "reveal": "Not Sydney."}]}

    def test_script_lines_and_emoji_removed(self):
        lines = bv.build_script(self.quiz, self.cfg)
        self.assertEqual([l["id"] for l in lines], ["intro", "rules", "q01", "a01", "outro"])
        self.assertEqual(lines[3]["text"], "The answer is Canberra. Not Sydney.")
        self.assertIn("Quiz number 9", lines[0]["text"])


class PageDetectionTests(unittest.TestCase):
    def test_alternating_pages_with_flicker(self):
        fps = 10
        labels = ["Q"] * 100 + ["A"] * 2 + ["Q"] * 1 + ["A"] * 22 + ["Q"] * 100 + ["A"] * 25
        pages = bv.find_pages(labels, fps, 4)
        self.assertEqual([p[0] for p in pages], ["Q", "A", "Q", "A"])
        self.assertAlmostEqual(pages[1][1], 10.0, delta=0.15)
        self.assertAlmostEqual(pages[2][1], 12.5, delta=0.15)

    def test_wrong_count_stops(self):
        with self.assertRaises(SystemExit):
            bv.find_pages(["Q"] * 50 + ["A"] * 20, 10, 4)


class CaptionTests(unittest.TestCase):
    def test_chunks_fit_two_lines(self):
        text = "The answer is Canberra. Not Sydney, not Melbourne. Canberra was built as the ultimate compromise!"
        for chunk in bv.caption_chunks(text):
            self.assertLessEqual(len(chunk), 84)
            for line in bv.wrap2(chunk).split("\n"):
                self.assertLessEqual(len(line), 46)

    def test_srt_time(self):
        self.assertEqual(bv.srt_time(3723.456), "01:02:03,456")


class AudioTests(unittest.TestCase):
    def test_loop_to_length(self):
        import numpy as np
        x = np.ones(bv.SR * 3, np.float32)
        self.assertEqual(len(bv.loop_to(x, bv.SR * 10, 1.0)), bv.SR * 10)


if __name__ == "__main__":
    unittest.main()
