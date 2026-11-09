import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import canva_build as cb  # noqa: E402


class CanvaBuildTest(unittest.TestCase):
    def test_largest_text_that_fits(self):
        self.assertEqual(cb.pick_template("x" * 60), "EAHaZJo0d7w")
        self.assertEqual(cb.pick_template("x" * 61), "EAHaZMCHgTI")
        self.assertEqual(cb.pick_template("x" * 96), "EAHaZCRO1wg")
        self.assertIsNone(cb.pick_template("x" * 171))

    def test_too_long_text_is_reported(self):
        qs = [{"n": 1, "question": "q" * 200, "answer": "a"}, {"n": 2, "question": "ok?", "answer": "a" * 31}]
        bad = cb.check_text(qs)
        self.assertEqual(len(bad), 2)
        self.assertIn("Q1 question", bad[0])
        self.assertIn("Q2 answer", bad[1])


if __name__ == "__main__":
    unittest.main()
