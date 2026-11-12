import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_shorts as ms  # noqa: E402
import upload_shorts as us  # noqa: E402


class FiveSecondCountdown(unittest.TestCase):
    """Giulia, 13 Nov 2026: the Shorts counter shows 5 seconds, not 10."""

    def test_config_is_five_seconds(self):
        self.assertEqual(json.loads((ROOT / "config" / "shorts.json").read_text())["think_seconds"], 5)

    def test_short_reading_holds_timer_then_counts_last_five(self):
        (a0, a1, hold, mute), (b0, b1, hold2, mute2) = ms.question_spans(100.0, 110.6, 104.5, 5, 10.0)
        self.assertEqual((a0, a1, hold), (100.0, 104.5, True))
        self.assertEqual((b0, b1, hold2, mute2), (105.0, 110.6, False, 0.0))
        self.assertAlmostEqual(100.0 + 10.0 - b0, 5.0)  # the countdown shown is 00:05 -> 00:00

    def test_long_reading_mutes_the_overlap_instead_of_repeating_the_voice(self):
        (_, a1, _, _), (b0, b1, _, mute) = ms.question_spans(100.0, 110.6, 108.4, 5, 10.0)
        self.assertEqual(a1, 108.4)
        self.assertEqual(b0, 105.0)
        self.assertAlmostEqual(mute, 3.4)

    def test_reading_past_the_page_is_clamped(self):
        (_, a1, _, _), (_, _, _, mute) = ms.question_spans(100.0, 110.6, 112.0, 5, 10.0)
        self.assertEqual(a1, 110.6)
        self.assertAlmostEqual(mute, 5.6)


class ReplaceUnpostedShorts(unittest.TestCase):
    now = dt.datetime(2026, 11, 13, 0, 0, tzinfo=dt.timezone.utc)

    def rec(self, **kw):
        return {"video_id": "x", "status": "scheduled", "publish_at": "2026-11-14T13:00:00Z", **kw}

    def test_scheduled_old_countdown_is_replaced(self):
        self.assertTrue(us.needs_replacing(self.rec(), 5, self.now))

    def test_already_five_seconds_is_left(self):
        self.assertFalse(us.needs_replacing(self.rec(countdown_seconds=5.0), 5, self.now))

    def test_live_or_imminent_is_left(self):
        self.assertFalse(us.needs_replacing(self.rec(publish_at="2026-11-12T23:00:00Z"), 5, self.now))
        self.assertFalse(us.needs_replacing(self.rec(publish_at="2026-11-13T00:30:00Z"), 5, self.now))

    def test_uploaded_but_unscheduled_is_replaced(self):
        self.assertTrue(us.needs_replacing({"video_id": "x", "status": "uploading"}, 5, self.now))

    def test_not_uploaded_is_not_a_replacement(self):
        self.assertFalse(us.needs_replacing({"status": "uploading"}, 5, self.now))


if __name__ == "__main__":
    unittest.main()
