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
        self.assertEqual([l["id"] for l in lines], ["intro", "rules", "q01", "a01", "outro1", "outro2", "outro3", "outro4"])
        self.assertEqual(lines[3]["text"], "The answer is Canberra. Not Sydney.")
        self.assertEqual(bv.clean("1,440! ⏰"), "1,440!")
        self.assertEqual(bv.clean("Two! 2️⃣"), "Two!")
        self.assertIn("Quiz number nine", lines[0]["text"])
        self.assertIn("Quiz number 9", lines[0]["caption"])


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "config" / "video.json").read_text())
        self.quiz = {"number": 16, "series": "General Knowledge", "questions": [
            {"n": i, "question": f"Q{i}?", "answer": "Yes", "reveal": ""} for i in range(1, 51)]}

    def test_score_checks_after_every_tenth_answer_but_not_the_last(self):
        lines = bv.build_script(self.quiz, self.cfg)
        ids = [l["id"] for l in lines]
        self.assertEqual([i for i in ids if i.startswith("cp")], ["cp10", "cp20", "cp30", "cp40"])
        self.assertEqual(ids[ids.index("a10") + 1], "cp10")
        self.assertEqual(ids[ids.index("cp10") + 1], "q11")
        cp = lines[ids.index("cp10")]
        self.assertEqual(cp["good"], 8)
        self.assertIn("8 or more", cp["caption"])
        self.assertIn("eight or more", cp["text"])

    def test_no_checkpoints_when_disabled_or_short(self):
        cfg = dict(self.cfg, checkpoint={"every": 0})
        self.assertFalse([l for l in bv.build_script(self.quiz, cfg) if l["kind"] == "checkpoint"])
        short = dict(self.quiz, questions=self.quiz["questions"][:10])
        self.assertFalse([l for l in bv.build_script(short, self.cfg) if l["kind"] == "checkpoint"])

    def test_card_renders(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            frame, out = Path(tmp) / "f.png", Path(tmp) / "c.png"
            Image.new("RGB", (640, 360), (200, 80, 40)).save(frame)
            bv.checkpoint_card(frame, out, "SCORE CHECK", 10, 8, (640, 360))
            self.assertEqual(Image.open(out).size, (640, 360))


class NumberTests(unittest.TestCase):
    def test_numbers_become_words(self):
        self.assertEqual(bv.say_numbers("around 130 seeds"), "around one hundred and thirty seeds")
        self.assertEqual(bv.say_numbers("The answer is 1,440."), "The answer is one thousand four hundred and forty.")
        self.assertEqual(bv.say_numbers("in 1945."), "in nineteen forty-five.")
        self.assertEqual(bv.say_numbers("top 300 km/h"), "top three hundred kilometres per hour")
        self.assertEqual(bv.say_numbers("the 21st century"), "the twenty-first century")


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


class BuzzerTests(unittest.TestCase):
    CFG = {"search_from": 9.0, "search_to": 12.5, "onset_db": -20.0, "length": 0.8, "rms_db": -19.0}

    def test_missing_buzzers_reuse_the_nearest_earlier_one(self):
        import numpy as np
        sr = 1000
        canva = np.zeros(60 * sr, np.float32)
        canva[10 * sr:int(10.8 * sr)] = 0.5      # q01 buzzer at 10 s; q02 (page at 20 s) and q03 (40 s) quiet
        pages = [("q01", 0.0), ("q02", 20.0), ("q03", 55.0)]  # q03's window runs past the end of the audio
        out = list(bv.find_buzzers(canva, pages, self.CFG, sr))
        self.assertEqual([o[0] for o in out], ["q01", "q02", "q03"])
        self.assertIsNone(out[0][2])
        self.assertEqual(out[1][2], "no buzzer in the Canva audio; reused q01's")
        self.assertEqual(out[2][2], "no buzzer in the Canva audio; reused q01's")
        self.assertTrue(all(o[1] is not None and len(o[1]) == int(0.8 * sr) for o in out))

    def test_leading_gap_uses_first_found_and_none_found_warns(self):
        import numpy as np
        sr = 1000
        canva = np.zeros(40 * sr, np.float32)
        canva[30 * sr:int(30.8 * sr)] = 0.5
        out = list(bv.find_buzzers(canva, [("q01", 0.0), ("q02", 20.0)], self.CFG, sr))
        self.assertEqual(out[0][2], "no buzzer in the Canva audio; reused q02's")
        self.assertIsNone(out[1][2])
        none = list(bv.find_buzzers(np.zeros(40 * sr, np.float32), [("q01", 0.0)], self.CFG, sr))
        self.assertEqual(none, [("q01", None, "no buzzer found in the Canva audio")])
