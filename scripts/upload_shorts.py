#!/usr/bin/env python3
"""Upload a quiz's Shorts and schedule them twice a day (rain-sounds release pattern, like the long videos).

For each Short made by make_shorts.py (shorts.json in --dir) that isn't done yet:
  upload private with no publishAt -> captions -> thumbnail (same as the full quiz) -> wait for processing
  -> schedule to the next free Shorts slot (config/shorts.json times, US Eastern) that is at least
     minimum_lead_minutes after the upload finished and not taken by any scheduled video on the channel.
Same settings as the long videos: Education, en-AU, not made for kids, altered/synthetic content No.
Records everything in quizzes/<quiz>/shorts-upload.json; a re-run resumes and never uploads a Short twice.
Studio-only steps (Related video = full quiz, pin the score comment) are listed for the Studio run.

Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import argparse
import datetime as dt
import json
import sys
import urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import upload_youtube as up  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")


def metadata(n, quiz, meta, scfg, ycfg):
    s = meta["shorts"][str(n)]
    count = len(quiz["questions"]) if isinstance(quiz["questions"], list) else quiz["questions"]
    desc = scfg["description"].format(
        opening=s.get("opening") or scfg["default_opening"], series=quiz.get("series", ""),
        number=quiz.get("number", ""), count=count,
        full_quiz_link=f"https://youtu.be/{meta['full_quiz_video_id']}", series_tag=meta.get("series_tag", "quiz"))
    if len(s["title"]) > 100 or len(desc) > 5000:
        raise SystemExit(f"Short {n}: title or description over YouTube's limit")
    tags = []
    for t in scfg.get("tags", []) + ycfg.get("series_tags", {}).get(quiz.get("series", ""), []):
        if t.lower() not in {x.lower() for x in tags} and up.tag_length(tags + [t]) <= 500:
            tags.append(t)
    return {"title": s["title"], "description": desc, "tags": tags}


def scheduled_slots(token):
    """publishAt times of every video on the channel that is scheduled (so Shorts never share a slot)."""
    _, _, ch = up.http("GET", f"{up.API}/channels?part=contentDetails&mine=true", token)
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], ""
    for _ in range(4):  # the latest 200 uploads is plenty
        q = urllib.parse.urlencode({"part": "contentDetails", "playlistId": uploads, "maxResults": 50})
        _, _, r = up.http("GET", f"{up.API}/playlistItems?{q}{page}", token)
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        if not r.get("nextPageToken"):
            break
        page = f"&pageToken={r['nextPageToken']}"
    taken = set()
    for i in range(0, len(ids), 50):
        _, _, r = up.http("GET", f"{up.API}/videos?part=status&id={','.join(ids[i:i + 50])}", token)
        for v in r.get("items", []):
            p = v["status"].get("publishAt")
            if p:
                taken.add(dt.datetime.fromisoformat(p.replace("Z", "+00:00")).replace(second=0, microsecond=0))
    return taken


def next_short_slot(after, times, taken):
    day = after.astimezone(ET).date()
    for _ in range(60):
        for t in times:
            hh, mm = map(int, t.split(":"))
            slot = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET)
            if slot >= after and slot.astimezone(dt.timezone.utc) not in taken:
                return slot
        day += dt.timedelta(days=1)
    raise SystemExit("No free Shorts slot in the next 60 days")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, help="quizzes/<quiz>")
    ap.add_argument("--dir", required=True, help="folder with make_shorts.py output")
    ap.add_argument("--thumbnail", help="thumbnail for every Short (the full quiz's thumbnail A)")
    ap.add_argument("--mode", choices=["preview", "upload"], default="preview")
    args = ap.parse_args()

    qdir, sdir = Path(args.quiz), Path(args.dir)
    quiz = json.loads((qdir / "quiz.json").read_text())
    meta = json.loads((qdir / "shorts.json").read_text())
    scfg = json.loads((ROOT / "config" / "shorts.json").read_text())
    ycfg = json.loads((ROOT / "config" / "youtube.json").read_text())
    made = json.loads((sdir / "shorts.json").read_text())
    rec_path = qdir / "shorts-upload.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {"quiz": quiz["id"], "shorts": {}}

    def save():
        rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))

    todo = [m for m in made if rec["shorts"].get(str(m["short"]), {}).get("status") != "scheduled"
            and not meta["shorts"][str(m["short"])].get("video_id")]
    plan = [{"short": m["short"], **metadata(m["short"], quiz, meta, scfg, ycfg)} for m in todo]
    if args.mode == "preview":
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    token = up.access_token()
    up.check_channel(token, ycfg)
    status_fields = {"selfDeclaredMadeForKids": ycfg["made_for_kids"], "license": "youtube", "embeddable": True,
                     "publicStatsViewable": True, "containsSyntheticMedia": ycfg["contains_synthetic_media"]}
    for m in todo:
        n = str(m["short"])
        r = rec["shorts"].setdefault(n, {"short": m["short"], "status": "uploading", "steps": {}})
        md = metadata(m["short"], quiz, meta, scfg, ycfg)
        if not r.get("video_id"):
            body = {"snippet": {"title": md["title"], "description": md["description"], "tags": md["tags"],
                                "categoryId": ycfg["category_id"], "defaultLanguage": ycfg["language"],
                                "defaultAudioLanguage": ycfg["language"]},
                    "status": {"privacyStatus": "private", **status_fields}}
            resp = up.upload_video(token, sdir / m["file"], body, ycfg.get("notify_subscribers", True))
            r.update(video_id=resp["id"], url=f"https://youtube.com/shorts/{resp['id']}", title=md["title"],
                     upload_completed_at=up.iso(dt.datetime.now(dt.timezone.utc)), questions=m["questions"])
            save()
        vid, steps = r["video_id"], r.setdefault("steps", {})
        if "captions" not in steps and (sdir / m["captions"]).exists():
            data, ctype = up.multipart({"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                                       (sdir / m["captions"]).read_bytes(), "application/octet-stream")
            up.http("POST", f"{up.UPLOAD_API}/captions?part=snippet&uploadType=multipart", token, data,
                    {"Content-Type": ctype})
            steps["captions"] = "uploaded"
            save()
        if "thumbnail" not in steps and args.thumbnail and Path(args.thumbnail).exists():
            code, _, _ = up.http("POST", f"{up.UPLOAD_API}/thumbnails/set?videoId={vid}", token,
                                 Path(args.thumbnail).read_bytes(), {"Content-Type": "image/jpeg"},
                                 expect=(200, 201, 400, 403))
            steps["thumbnail"] = Path(args.thumbnail).name if code in (200, 201) else f"not accepted ({code})"
            save()
        r["studio_tasks"] = [f"Related video: link to the full quiz https://youtu.be/{meta['full_quiz_video_id']}.",
                             "Pin the score comment once it is posted."]
        save()

    # schedule after processing, in order, each in the next free slot
    taken = scheduled_slots(token)
    for m in todo:
        r = rec["shorts"][str(m["short"])]
        if r.get("status") == "scheduled":
            continue
        item = up.wait_for_processing(token, r["video_id"], ycfg.get("processing_wait_minutes", 45))
        r["processing"] = item.get("processingDetails", {}).get("processingStatus")
        if r["processing"] != "succeeded":
            r["status"] = "processing_incomplete"
            save()
            continue
        done = dt.datetime.fromisoformat(r["upload_completed_at"].replace("Z", "+00:00"))
        after = max(done + dt.timedelta(minutes=scfg.get("minimum_lead_minutes", 1440)),
                    dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5))
        slot = next_short_slot(after, scfg["times_us_eastern"], taken)
        body = {"id": r["video_id"], "status": {"privacyStatus": "private", "publishAt": up.iso(slot), **status_fields}}
        _, _, resp = up.http("PUT", f"{up.API}/videos?part=status", token, json.dumps(body).encode(),
                             {"Content-Type": "application/json"})
        st = resp.get("status", {})
        if st.get("publishAt", "").replace(".000Z", "Z") != up.iso(slot):
            r.update(status="schedule_unconfirmed", youtube_status=st)
            save()
            continue
        taken.add(slot.astimezone(dt.timezone.utc))
        r.update(status="scheduled", publish_at=up.iso(slot), publish_at_local=up.local_times(slot))
        save()
    print(json.dumps({n: {k: v.get(k) for k in ("video_id", "title", "status", "publish_at_local", "steps")}
                      for n, v in rec["shorts"].items()}, indent=2, ensure_ascii=False))
    if any(v.get("status") != "scheduled" for v in rec["shorts"].values()):
        raise SystemExit("Some Shorts are not scheduled yet; re-run to resume.")


if __name__ == "__main__":
    main()
