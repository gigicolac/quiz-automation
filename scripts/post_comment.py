#!/usr/bin/env python3
"""Post the score comment on quiz videos that have gone public (rain-sounds pattern).

For each quizzes/*/upload.json that is scheduled, past its release time and has no comment yet:
check YouTube says the video is public, reuse a matching comment the channel already posted (so a
video is never commented on twice), otherwise post one, and record comment_id. The YouTube API
cannot pin comments: the run summary lists an "Open and pin" link for each.

Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import upload_youtube as up  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def comment_text(quiz_dir, cfg):
    quiz = json.loads((quiz_dir / "quiz.json").read_text())
    count = len(quiz["questions"]) if isinstance(quiz["questions"], list) else quiz["questions"]
    return cfg["comment"].format(count=count)


def existing_comment(token, vid, channel_id, text):
    page = ""
    while True:
        q = urllib.parse.urlencode({"part": "snippet", "videoId": vid, "maxResults": 100})
        _, _, resp = up.http("GET", f"{up.API}/commentThreads?{q}{page}", token, expect=(200, 403))
        for item in resp.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            if top.get("authorChannelId", {}).get("value") == channel_id and top.get("textOriginal") == text:
                return item["id"]
        if not resp.get("nextPageToken"):
            return None
        page = f"&pageToken={resp['nextPageToken']}"


def main():
    cfg = json.loads((ROOT / "config" / "youtube.json").read_text())
    now = dt.datetime.now(dt.timezone.utc)
    due = []
    for f in sorted((ROOT / "quizzes").glob("*/upload.json")):
        rec = json.loads(f.read_text())
        if rec.get("status") != "scheduled" or rec.get("comment_id") or not rec.get("publish_at"):
            continue
        if dt.datetime.fromisoformat(rec["publish_at"].replace("Z", "+00:00")) > now + dt.timedelta(minutes=5):
            continue
        due.append((f, rec))
    summary = ["## Score comments", ""]
    if not due:
        summary.append("Nothing due.")
    else:
        token = up.access_token()
        channel = up.check_channel(token, cfg)
        for f, rec in due:
            vid = rec["video_id"]
            _, _, info = up.http("GET", f"{up.API}/videos?part=status&id={vid}", token)
            privacy = (info.get("items") or [{}])[0].get("status", {}).get("privacyStatus")
            if privacy != "public":
                summary.append(f"- {rec['quiz']}: video is {privacy}, not public yet; will retry.")
                continue
            text = comment_text(f.parent, cfg)
            cid = existing_comment(token, vid, channel["id"], text)
            if not cid:
                body = {"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": text}}}}
                _, _, resp = up.http("POST", f"{up.API}/commentThreads?part=snippet", token,
                                     json.dumps(body).encode(), {"Content-Type": "application/json"})
                cid = resp["id"]
            rec.update(comment_id=cid, comment_posted_at=up.iso(now),
                       pin_link=f"https://www.youtube.com/watch?v={vid}&lc={cid}")
            f.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
            summary.append(f"- {rec['quiz']}: comment posted. [Open and pin]({rec['pin_link']}) "
                           "(comment's ⋮ menu → Pin).")
    out = "\n".join(summary)
    print(out)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write(out + "\n")


if __name__ == "__main__":
    main()
