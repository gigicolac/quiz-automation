import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import upload_youtube as up  # noqa: E402

CFG = json.loads((ROOT / "config" / "youtube.json").read_text())
NY = ZoneInfo("America/New_York")


class ScheduleTests(unittest.TestCase):
    def test_next_slot_is_three_days_ahead(self):
        now = dt.datetime(2026, 11, 4, 4, 0, tzinfo=dt.timezone.utc)  # Tue 3 Nov 11pm New York
        self.assertEqual(up.next_slot(now, CFG), dt.datetime(2026, 11, 8, 13, 0, tzinfo=NY))  # Sunday 1pm

    def test_taken_slot_is_skipped(self):
        now = dt.datetime(2026, 11, 4, 4, 0, tzinfo=dt.timezone.utc)
        taken = {dt.datetime(2026, 11, 8, 13, 0, tzinfo=NY)}
        self.assertEqual(up.next_slot(now, CFG, taken), dt.datetime(2026, 11, 12, 15, 0, tzinfo=NY))  # Thursday 3pm

    def test_explicit_time_is_new_york(self):
        now = dt.datetime(2026, 11, 4, tzinfo=dt.timezone.utc)
        when = up.parse_publish_at("2026-11-12T15:00", now, CFG, set())
        self.assertEqual(when.astimezone(dt.timezone.utc).hour, 20)


class MetadataTests(unittest.TestCase):
    report = {"segments": [{"name": "intro", "start": 0}, {"name": "rules", "start": 10.9},
                           {"name": "q01", "start": 19.0}, {"name": "a01", "start": 29.6},
                           {"name": "q02", "start": 35.2}, {"name": "outro", "start": 889.0}]}
    quiz = {"title": "General Knowledge Quiz #9 | 50 Questions Everyone Should Know", "questions": [1] * 50}

    def test_description_has_chapters_and_schedule(self):
        meta = up.build_metadata(self.quiz, self.report, CFG)
        self.assertIn("0:00 Intro\n0:19 Question 1\n0:35 Question 2\n14:49 Thanks for playing", meta["description"])
        self.assertIn("Thursday 3PM & Sunday 1PM ET", meta["description"])

    def test_wrong_schedule_line_blocks(self):
        bad = {**CFG, "schedule_line": "New quizzes every Friday 7AM AEST."}
        with self.assertRaises(SystemExit):
            up.build_metadata(self.quiz, self.report, bad)


if __name__ == "__main__":
    unittest.main()
