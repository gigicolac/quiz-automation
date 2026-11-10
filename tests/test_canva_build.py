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


class UploadAlreadyExists(unittest.TestCase):
    """Canva's 400 'Asset Upload for url ... already exists' is retried with a cache-busting query string."""

    def test_retries_with_new_url(self):
        from unittest import mock
        import canva_build as cb
        from canva_export import CanvaError
        seen = []

        def fake_call(method, path, token, body=None, raise_codes=()):
            seen.append(body["url"])
            if len(seen) == 1:
                raise CanvaError(400, '{"message":"Asset Upload for url x already exists"}')
            return {"job": {"status": "success", "asset": {"id": "A1", "type": "video"}}}

        with mock.patch.object(cb, "call", fake_call), mock.patch.object(cb.time, "sleep"):
            self.assertEqual(cb.upload("t", "n", "https://media.giphy.com/media/x/giphy.mp4"), ("A1", "video"))
        self.assertEqual(seen, ["https://media.giphy.com/media/x/giphy.mp4",
                                "https://media.giphy.com/media/x/giphy.mp4?omq=1"])

    def test_other_400_is_an_upload_failure(self):
        from unittest import mock
        import canva_build as cb
        from canva_export import CanvaError

        def fake_call(*a, **k):
            raise CanvaError(400, '{"message":"bad url"}')

        with mock.patch.object(cb, "call", fake_call):
            with self.assertRaises(cb.UploadFailed):
                cb.upload("t", "n", "https://example.com/a.gif")


class StaleRefreshToken(unittest.TestCase):
    """A run queued before another job renewed the Canva sign-in must not use its stale copy."""

    def check(self, created, updated):
        from datetime import datetime
        from unittest import mock
        import canva_export as ce
        times = {".created_at": datetime.fromisoformat(created), ".updated_at": datetime.fromisoformat(updated)}
        env = {"GITHUB_REPOSITORY": "o/r", "GITHUB_RUN_ID": "1", "GH_SECRETS_TOKEN": "s", "GH_TOKEN": "g"}
        with mock.patch.dict("os.environ", env), \
                mock.patch.object(ce, "_gh_json_field", lambda path, field, token: times[field]):
            return ce.refresh_token_may_be_stale()

    def test_renewed_after_run_was_created(self):
        self.assertTrue(self.check("2026-11-10T02:37:27+00:00", "2026-11-10T02:37:45+00:00"))

    def test_renewed_long_before(self):
        self.assertFalse(self.check("2026-11-10T02:37:27+00:00", "2026-11-10T01:00:00+00:00"))

    def test_outside_actions_is_never_stale(self):
        from unittest import mock
        import canva_export as ce
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(ce.refresh_token_may_be_stale())
