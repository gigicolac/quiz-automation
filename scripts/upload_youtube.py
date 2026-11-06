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
    """First publishing slot (config slots) at least lead_days after now that isn't already used."""
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
    titles = title_variants(quiz, cfg)
    return [
        f"End screen: {es.get('note', '')} Left = {es.get('left', '')}; right = {es.get('right', '').format(playlist=playlist)}.",
        "Test & Compare (A/B), Title and thumbnail: " + " | ".join(
            f"{t} + thumbnail {chr(65 + i)}" for i, t in enumerate(titles)) + ".",
        "Category Education: Type = Activity; Problems = the 'problems' list in upload.json.",
        "Caption certification: This content has never aired on television in the U.S.",
        "Shorts remixing: allowed.",
        "Pin the score comment once it is posted (every release).",
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


def tag_length(tags):
    # YouTube counts quotes around tags that contain spaces, plus the separating commas
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)


def build_tags(quiz, cfg, limit=500):
    tags = []
    for t in quiz.get("tags", []) + cfg.get("series_tags", {}).get(quiz.get("series", ""), []) + cfg["tags"]:
        if t.lower() not in {x.lower() for x in tags} and tag_length(tags + [t]) <= limit:
            tags.append(t)
    return tags


def problems(quiz, report):
    """Studio > Category Education > Problems: one line per question, timecode then question."""
    qs = {q["n"]: q["question"] for q in quiz["questions"] if isinstance(q, dict)} \
        if isinstance(quiz["questions"], list) else {}
    out = []
    for seg in report["segments"]:
        n = seg["name"]
        if n.startswith("q") and n[1:].isdigit() and int(n[1:]) in qs:
            out.append(f"{stamp(seg['start'])} {qs[int(n[1:])]}")
    return "\n".join(out)


def build_metadata(quiz, report, cfg):
    count = len(quiz["questions"]) if isinstance(quiz["questions"], list) else quiz["questions"]
    hooks = cfg.get("description_hooks", {})
    hook = quiz.get("description_hook") or hooks.get(quiz.get("series", ""), hooks.get("default", ""))
    desc = cfg["description"].format(hook=hook.format(count=count), count=count, schedule_line=cfg["schedule_line"],
                                     chapters=chapters(report))
    need = cfg.get("schedule_required", "every Thursday, Saturday & Sunday")
    if need not in desc or "AEST" in desc:
        raise SystemExit(f"Blocked: the description's schedule line must say '{need}' and must not mention AEST.")
    if len(desc) > 5000 or len(quiz["title"]) > 100:
        raise SystemExit("Title or description is over YouTube's limit (100 / 5000 characters).")
    return {
        "title": quiz["title"],
        "description": desc,
        "tags": build_tags(quiz, cfg),
        "comment": cfg.get("comment", "").format(count=count),
        "problems": problems(quiz, report),
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


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_times(t):
    if not t:
        return None
    return {"US Eastern": t.astimezone(ZoneInfo("America/New_York")).strftime("%a %d %b %Y %H:%M %Z"),
            "Sydney": t.astimezone(ZoneInfo("Australia/Sydney")).strftime("%a %d %b %Y %H:%M %Z")}


def check_channel(token, cfg):
    """Refuse to upload unless the signed-in channel is the quiz channel."""
    _, _, resp = http("GET", f"{API}/channels?part=snippet&mine=true", token)
    items = resp.get("items") or []
    if not items:
        raise SystemExit("The YouTube sign-in has no channel. Re-run the YouTube sign-in and pick One More Quiz.")
    ch = items[0]
    want_id, want_name = cfg.get("expected_channel_id"), cfg.get("expected_channel_title", "")
    if want_id and ch["id"] != want_id:
        raise SystemExit(f"Signed in to channel {ch['id']} ({ch['snippet']['title']}), expected {want_id}.")
    if not want_id and want_name.lower() not in ch["snippet"]["title"].lower():
        raise SystemExit(f"Signed in to '{ch['snippet']['title']}', expected a channel named like '{want_name}'.")
    return {"id": ch["id"], "title": ch["snippet"]["title"]}


def wait_for_processing(token, vid, minutes):
    import time
    deadline = time.time() + minutes * 60
    while True:
        _, _, info = http("GET", f"{API}/videos?part=status,processingDetails&id={vid}", token)
        item = (info.get("items") or [{}])[0]
        state = item.get("processingDetails", {}).get("processingStatus")
        print(f"  processing: {state}", flush=True)
        if state in ("succeeded", "failed", "terminated") or time.time() > deadline:
            return item
        time.sleep(30)


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
    ap.add_argument("--replace", action="store_true",
                    help="re-upload a quiz that is already scheduled: the old video is taken off the schedule "
                         "(left private, not deleted) and a new upload is scheduled instead")
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
    replacing = None
    if record.get("status") == "scheduled" and args.replace and args.mode == "upload":
        replacing, record = record, {}
    elif record.get("status") == "scheduled":  # done; anything else with a video_id resumes
        raise SystemExit(f"{quiz['id']} is already uploaded and scheduled as {record['video_id']}; nothing to do. "
                         "Use replace to re-upload it.")
    if record and not record.get("video_id") and set(record) != {"replaced"}:
        raise SystemExit(f"{quiz['id']}: a previous upload stopped before YouTube returned a video ID. "
                         "Check YouTube Studio for a stray private upload, then reconcile upload.json by hand.")
    resume = bool(record.get("video_id"))

    now = dt.datetime.now(dt.timezone.utc)
    when = parse_publish_at(args.publish_at, now, cfg, taken_slots(qdir.parent, qdir.name))
    if resume and record.get("intended_publish_at"):
        when = dt.datetime.fromisoformat(record["intended_publish_at"].replace("Z", "+00:00"))
    meta = build_metadata(quiz, report, cfg)
    plan = {**meta, "intended_publish_at": iso(when) if when else None,
            "publish_at_local": local_times(when),
            "release_tag": review.get("release_tag"), "playlist": playlist_title(quiz, cfg),
            "studio_tasks": studio_tasks(quiz, cfg, playlist_title(quiz, cfg))}
    Path(args.out).write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print(json.dumps({k: plan[k] for k in ("title", "intended_publish_at", "publish_at_local", "playlist",
                                           "studio_tasks")}, indent=2, ensure_ascii=False))
    if args.mode == "preview":
        print("Preview only: nothing was sent to YouTube.")
        return

    def save():
        record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))

    token = access_token()
    channel = check_channel(token, cfg)
    status_fields = {"selfDeclaredMadeForKids": cfg["made_for_kids"], "license": "youtube", "embeddable": True,
                     "publicStatsViewable": True, "containsSyntheticMedia": cfg["contains_synthetic_media"]}

    if replacing:
        # take the old upload off the schedule first, so only one copy can go live; it stays private (not deleted)
        old = replacing["video_id"]
        body = {"id": old, "status": {"privacyStatus": "private", **status_fields}}
        _, _, resp = http("PUT", f"{API}/videos?part=status", token, json.dumps(body).encode(),
                          {"Content-Type": "application/json"})
        if resp.get("status", {}).get("publishAt"):
            raise SystemExit(f"YouTube kept the schedule on the old video {old}; not uploading a second copy.")
        replacing.update(status="replaced_unscheduled", unscheduled_at=iso(dt.datetime.now(dt.timezone.utc)))
        replaced_list = replacing.pop("replaced", []) + [replacing]
        record_path.write_text(json.dumps({"replaced": replaced_list}, indent=2, ensure_ascii=False))
        record = {"replaced": replaced_list}

    if not resume:
        # 1. transfer PRIVATE with no publishAt (rain-sounds release buffer pattern)
        today = dt.date.today().isoformat()
        body = {
            "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": cfg["category_id"], "defaultLanguage": cfg["language"],
                        "defaultAudioLanguage": cfg["language"]},
            "status": {"privacyStatus": "private", **status_fields},
            "recordingDetails": {"recordingDate": f"{today}T00:00:00Z"},
            "paidProductPlacementDetails": {"hasPaidProductPlacement": cfg["paid_promotion"]},
        }
        record = {"quiz": quiz["id"], "channel": channel, "status": "uploading", "started_at": now.isoformat(),
                  **{k: plan[k] for k in ("title", "intended_publish_at", "publish_at_local", "release_tag",
                                          "playlist", "problems")}, "steps": {},
                  **({"replaced": record["replaced"]} if record.get("replaced") else {})}
        save()
        video = upload_video(token, Path(args.video), body, cfg["notify_subscribers"])
        vid = video["id"]
        record.update(video_id=vid, url=f"https://youtu.be/{vid}", status="transferred",
                      upload_completed_at=iso(dt.datetime.now(dt.timezone.utc)))
        save()
    vid = record["video_id"]
    steps = record.setdefault("steps", {})

    # 2. captions, thumbnail, playlist (each once, so a resumed run doesn't repeat them)
    if "captions" not in steps and args.captions and Path(args.captions).exists():
        data, ctype = multipart({"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                                Path(args.captions).read_bytes(), "application/octet-stream")
        http("POST", f"{UPLOAD_API}/captions?part=snippet&uploadType=multipart", token, data, {"Content-Type": ctype})
        steps["captions"] = "uploaded"
        save()
    if "thumbnail" not in steps and args.thumbnail and Path(args.thumbnail).exists():
        http("POST", f"{UPLOAD_API}/thumbnails/set?videoId={vid}", token, Path(args.thumbnail).read_bytes(),
             {"Content-Type": "image/jpeg" if args.thumbnail.lower().endswith((".jpg", ".jpeg")) else "image/png"})
        steps["thumbnail"] = Path(args.thumbnail).name
        save()
    if "playlist" not in steps:
        pid, ptitle, created = find_or_create_playlist(token, playlist_title(quiz, cfg), quiz.get("series", ""))
        pl = {"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}
        http("POST", f"{API}/playlistItems?part=snippet", token, json.dumps(pl).encode(),
             {"Content-Type": "application/json"})
        steps["playlist"] = {"id": pid, "title": ptitle, "created": created}
        record["studio_tasks"] = studio_tasks(quiz, cfg, ptitle)
        save()

    # 3. wait for YouTube to finish processing
    item = wait_for_processing(token, vid, cfg.get("processing_wait_minutes", 45))
    record["processing"] = item.get("processingDetails", {}).get("processingStatus")
    save()
    if record["processing"] != "succeeded":
        record["status"] = "processing_incomplete"
        save()
        raise SystemExit(f"Video {vid} is still private: processing status is {record['processing']}. "
                         "Re-run the upload later; it resumes this video without uploading again.")

    # 4. schedule: intended slot, but never sooner than the minimum buffer after the transfer finished
    if when:
        done = dt.datetime.fromisoformat(record["upload_completed_at"].replace("Z", "+00:00"))
        earliest = max(done + dt.timedelta(minutes=cfg.get("minimum_lead_minutes", 1440)),
                       dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1))
        publish = max(when, earliest)
        record.update(publish_at=iso(publish), publish_at_local=local_times(publish))
        save()
        body = {"id": vid, "status": {"privacyStatus": "private", "publishAt": iso(publish), **status_fields}}
        # confirm from the update response, as the rain pipeline does: a read straight
        # after the update can return the old status without publishAt
        _, _, resp = http("PUT", f"{API}/videos?part=status", token, json.dumps(body).encode(),
                          {"Content-Type": "application/json"})
        st = resp.get("status", {})
        if not st.get("publishAt"):
            import time
            for _ in range(6):
                time.sleep(10)
                _, _, info = http("GET", f"{API}/videos?part=status&id={vid}", token)
                st = (info.get("items") or [{}])[0].get("status", {})
                if st.get("publishAt"):
                    break
        record["youtube_status"] = st
        if st.get("privacyStatus") != "private" or st.get("publishAt", "").replace(".000Z", "Z") != iso(publish):
            record["status"] = "schedule_unconfirmed"
            save()
            raise SystemExit(f"YouTube did not confirm the schedule for {vid}: {st}")
        record["status"] = "scheduled"
    else:
        record["status"] = "private_unscheduled"
    record["finished_at"] = iso(dt.datetime.now(dt.timezone.utc))
    save()
    print(json.dumps({k: record.get(k) for k in ("video_id", "url", "status", "publish_at", "publish_at_local",
                                                  "steps", "processing", "studio_tasks")}, indent=2,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
