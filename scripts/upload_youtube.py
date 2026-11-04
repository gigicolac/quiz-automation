#!/usr/bin/env python3
"""Upload an approved quiz video to YouTube: private, scheduled with publishAt.

Modes:
  preview  builds the title, description (with chapters), tags and schedule and writes them out. No YouTube calls.
  upload   does the above, then uploads the video, captions, thumbnail (if given) and comment,
           and records the result in quizzes/<quiz>/upload.json.

Safety: refuses unless quiz.json records the final video as approved, refuses if upload.json already holds a
video ID (no duplicate uploads), and blocks if the description's schedule line is wrong (PLAN.md rule).

Env for upload mode: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
API = "https://www.googleapis.com/youtube/v3"
UPLOAD_API = "https://www.googleapis.com/upload/youtube/v3"


# ---------------------------------------------------------------- metadata

def stamp(seconds):
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def chapters(report):
    out = []
    for seg in report["segments"]:
        name = seg["name"]
        if name == "intro":
            out.append(("0:00", "Intro"))
        elif name.startswith("q") and name[1:].isdigit():
            out.append((stamp(seg["start"]), f"Question {int(name[1:])}"))
        elif name == "outro":
            out.append((stamp(seg["start"]), "Thanks for playing"))
    return "\n".join(f"{t} {label}" for t, label in out)


def taken_slots(quizzes_dir, skip):
    taken = set()
    for f in Path(quizzes_dir).glob("*/upload.json"):
        if f.parent.name == skip:
            continue
        at = json.loads(f.read_text()).get("publish_at")
        if at:
            taken.add(dt.datetime.fromisoformat(at.replace("Z", "+00:00")))
    return taken


def next_slot(now, cfg, taken=()):
    """First Thursday/Sunday slot at least lead_days after now that isn't already used."""
    tz = ZoneInfo(cfg["timezone"])
    earliest = now.astimezone(tz) + dt.timedelta(days=cfg["lead_days"])
    day = earliest.date()
    taken_utc = {t.astimezone(dt.timezone.utc) for t in taken}
    for _ in range(60):
        for slot in cfg["slots"]:
            if WEEKDAYS[day.weekday()] != slot["weekday"]:
                continue
            h, m = map(int, slot["time"].split(":"))
            when = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=tz)
            if when >= earliest and when.astimezone(dt.timezone.utc) not in taken_utc:
                return when
        day += dt.timedelta(days=1)
    raise SystemExit("No free publishing slot found in the next 60 days")


def parse_publish_at(value, now, cfg, taken):
    value = (value or "").strip()
    if not value:
        return None
    if value == "next":
        return next_slot(now, cfg, taken)
    when = dt.datetime.fromisoformat(value)
    if when.tzinfo is None:
        when = when.replace(tzinfo=ZoneInfo(cfg["timezone"]))
    if when <= now:
        raise SystemExit(f"publish_at {value} is in the past")
    return when


def playlist_title(quiz, cfg):
    series = quiz.get("series", "")
    return cfg.get("playlists", {}).get(series) or f"{series} Quizzes"


def title_variants(quiz, cfg):
    count = len(quiz["questions"]) if isinstance(quiz["questions"], list) else quiz["questions"]
    out = []
    for t in cfg.get("title_variants", ["{title}"]):
        v = t.format(title=quiz["title"], count=count, series=quiz.get("series", ""), number=quiz.get("number", ""))
        if v not in out and len(v) <= 100:
            out.append(v)
    return out


def studio_tasks(quiz, cfg, playlist):
    """Things the YouTube API can't do; done in Studio (browser task) after upload."""
    es = cfg.get("end_screen", {})
    return [
        f"End screen: {es.get('note', '')} Left = {es.get('left', '')}; right = {es.get('right', '').format(playlist=playlist)}.",
        "Test & Compare (A/B): titles " + " | ".join(title_variants(quiz, cfg)) + "; thumbnails once there are 2-3 variants.",
        "Pin the score comment.",
    ]


def find_or_create_playlist(token, title, series):
    """Reuse a playlist whose title mentions the series, else create a public one."""
    page = ""
    while True:
        _, _, resp = http("GET", f"{API}/playlists?part=snippet&mine=true&maxResults=50{page}", token)
        for item in resp.get("items", []):
            t = item["snippet"]["title"]
            if t.lower() == title.lower() or (series and series.lower() in t.lower()):
                return item["id"], t, False
        if not resp.get("nextPageToken"):
            break
        page = f"&pageToken={resp['nextPageToken']}"
    body = {"snippet": {"title": title, "description": f"Every {series} quiz from Just One More Quiz. "
                        "Grab a pen, keep score and see how you go!"},
            "status": {"privacyStatus": "public"}}
    _, _, resp = http("POST", f"{API}/playlists?part=snippet,status", token, json.dumps(body).encode(),
                      {"Content-Type": "application/json"})
    return resp["id"], title, True


def build_metadata(quiz, report, cfg):
    count = len(quiz["questions"]) if isinstance(quiz["questions"], list) else quiz["questions"]
    desc = cfg["description"].format(count=count, schedule_line=cfg["schedule_line"], chapters=chapters(report))
    if "Thursday 3PM & Sunday 1PM ET" not in desc or "AEST" in desc:
        raise SystemExit("Blocked: the description's schedule line must read 'Thursday 3PM & Sunday 1PM ET' "
                         "and must not mention AEST.")
    if len(desc) > 5000 or len(quiz["title"]) > 100:
        raise SystemExit("Title or description is over YouTube's limit (100 / 5000 characters).")
    return {
        "title": quiz["title"],
        "description": desc,
        "tags": cfg["tags"],
        "comment": cfg.get("comment", "").format(count=count),
    }


# ---------------------------------------------------------------- YouTube API

def http(method, url, token=None, data=None, headers=None, expect=(200, 201)):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            body = r.read()
            return r.status, dict(r.headers), (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        if e.code in expect:
            return e.code, dict(e.headers), {}
        raise SystemExit(f"{method} {url.split('?')[0]} failed ({e.code}): {e.read().decode()[:500]}")


def access_token():
    form = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    _, _, tok = http("POST", "https://oauth2.googleapis.com/token", data=form,
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    print(f"::add-mask::{tok['access_token']}")
    return tok["access_token"]


def upload_video(token, video, body, notify):
    size = video.stat().st_size
    q = urllib.parse.urlencode({"uploadType": "resumable", "notifySubscribers": str(notify).lower(),
                                "part": ",".join(body)})
    _, hdr, _ = http("POST", f"{UPLOAD_API}/videos?{q}", token, json.dumps(body).encode(),
                     {"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Length": str(size),
                      "X-Upload-Content-Type": "video/mp4"})
    location = hdr.get("Location") or hdr.get("location")
    chunk, sent = 32 * 1024 * 1024, 0
    with open(video, "rb") as f:
        while sent < size:
            part = f.read(chunk)
            end = sent + len(part) - 1
            status, hdr, resp = http("PUT", location, token, part,
                                     {"Content-Range": f"bytes {sent}-{end}/{size}"}, expect=(200, 201, 308))
            sent = end + 1
            print(f"  uploaded {sent / size:.0%}", flush=True)
    if not resp.get("id"):
        raise SystemExit("Upload finished without a video ID")
    return resp


def multipart(meta, payload, payload_type):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
            f"--{boundary}\r\nContent-Type: {payload_type}\r\n\r\n").encode() + payload + f"\r\n--{boundary}--".encode()
    return body, f"multipart/related; boundary={boundary}"


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True)
    ap.add_argument("--report", required=True, help="build_report.json from the approved build")
    ap.add_argument("--video")
    ap.add_argument("--captions")
    ap.add_argument("--thumbnail")
    ap.add_argument("--publish-at", default="next", help="'next', blank (private, unscheduled) or a New York time")
    ap.add_argument("--mode", choices=["preview", "upload"], default="preview")
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=str(ROOT / "config" / "youtube.json"))
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    qdir = Path(args.quiz)
    quiz = json.loads((qdir / "quiz.json").read_text())
    report = json.loads(Path(args.report).read_text())
    review = quiz.get("review", {}).get("video", {})
    if review.get("decision") != "approved":
        raise SystemExit(f"{quiz['id']}: final video is not approved in quiz.json; not uploading.")
    record_path = qdir / "upload.json"
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    if record.get("video_id"):
        raise SystemExit(f"{quiz['id']} already uploaded as {record['video_id']}; not uploading again.")

    now = dt.datetime.now(dt.timezone.utc)
    when = parse_publish_at(args.publish_at, now, cfg, taken_slots(qdir.parent, qdir.name))
    meta = build_metadata(quiz, report, cfg)
    plan = {**meta, "publish_at": when.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z") if when else None,
            "publish_at_local": {"US Eastern": when.strftime("%a %d %b %Y %H:%M %Z") if when else None,
                                 "Melbourne": when.astimezone(ZoneInfo("Australia/Melbourne")).strftime(
                                     "%a %d %b %Y %H:%M %Z") if when else None},
            "release_tag": review.get("release_tag"), "playlist": playlist_title(quiz, cfg),
            "studio_tasks": studio_tasks(quiz, cfg, playlist_title(quiz, cfg))}
    Path(args.out).write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print(json.dumps({k: plan[k] for k in ("title", "publish_at", "publish_at_local", "playlist", "studio_tasks")},
                     indent=2, ensure_ascii=False))
    if args.mode == "preview":
        print("Preview only: nothing was sent to YouTube.")
        return

    token = access_token()
    today = dt.date.today().isoformat()
    body = {
        "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                    "categoryId": cfg["category_id"], "defaultLanguage": cfg["language"],
                    "defaultAudioLanguage": cfg["language"]},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": cfg["made_for_kids"],
                   "containsSyntheticMedia": cfg["contains_synthetic_media"], "license": "youtube",
                   "embeddable": True, **({"publishAt": plan["publish_at"]} if when else {})},
        "recordingDetails": {"recordingDate": f"{today}T00:00:00Z"},
        "paidProductPlacementDetails": {"hasPaidProductPlacement": cfg["paid_promotion"]},
    }
    # record the attempt first, so an interrupted upload is reconciled against YouTube before retrying
    record = {"quiz": quiz["id"], "status": "uploading", "started_at": now.isoformat(), **plan}
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    video = upload_video(token, Path(args.video), body, cfg["notify_subscribers"])
    vid = video["id"]
    record.update(video_id=vid, url=f"https://youtu.be/{vid}", status="uploaded", transfer="complete")
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))

    steps = {}
    if args.captions and Path(args.captions).exists():
        data, ctype = multipart({"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                                Path(args.captions).read_bytes(), "application/octet-stream")
        http("POST", f"{UPLOAD_API}/captions?part=snippet&uploadType=multipart", token, data, {"Content-Type": ctype})
        steps["captions"] = "uploaded"
    if args.thumbnail and Path(args.thumbnail).exists():
        http("POST", f"{UPLOAD_API}/thumbnails/set?videoId={vid}", token, Path(args.thumbnail).read_bytes(),
             {"Content-Type": "image/png"})
        steps["thumbnail"] = "set"
    else:
        steps["thumbnail"] = "none (add in Studio or build the thumbnail step)"
    pid, ptitle, created = find_or_create_playlist(token, playlist_title(quiz, cfg), quiz.get("series", ""))
    pl = {"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}
    http("POST", f"{API}/playlistItems?part=snippet", token, json.dumps(pl).encode(),
         {"Content-Type": "application/json"})
    steps["playlist"] = f"{ptitle} ({pid}){' - created' if created else ''}"
    plan["studio_tasks"] = studio_tasks(quiz, cfg, ptitle)
    record["studio_tasks"] = plan["studio_tasks"]
    if meta["comment"]:
        c = {"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": meta["comment"]}}}}
        _, _, resp = http("POST", f"{API}/commentThreads?part=snippet", token, json.dumps(c).encode(),
                          {"Content-Type": "application/json"}, expect=(200, 201, 403))
        steps["comment"] = "posted (pin it in Studio)" if resp.get("id") else "not posted (comments may be off until processing finishes)"

    # what YouTube reports back, kept separate from the transfer itself
    _, _, info = http("GET", f"{API}/videos?part=status,processingDetails&id={vid}", token)
    item = (info.get("items") or [{}])[0]
    record.update(steps=steps, youtube_status=item.get("status"),
                  processing=item.get("processingDetails", {}).get("processingStatus"), status="uploaded",
                  finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(json.dumps({k: record.get(k) for k in ("video_id", "url", "publish_at", "steps", "youtube_status",
                                                  "processing", "studio_tasks")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
