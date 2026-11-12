#!/usr/bin/env python3
"""Upload a quiz's Shorts and schedule them twice a day (rain-sounds release pattern, like the long videos).

For each Short made by make_shorts.py (shorts.json in --dir) that isn't done yet:
  upload private with no publishAt -> captions -> thumbnail (a frame of the Short's first question, like Short 1) -> wait for processing
  -> schedule to the next free Shorts slot (config/shorts.json times, US Eastern) that is at least
     minimum_lead_minutes after the upload finished and not taken by any scheduled video on the channel.
Same settings as the long videos: Education, en-AU, not made for kids, altered/synthetic content No.
Records everything in quizzes/<quiz>/shorts-upload.json; a re-run resumes and never uploads a Short twice.
Also: added to the series playlist, recording date 2-7 days before upload (varied per Short), Problems list.
Studio-only steps (Related video = full quiz, paid promotion No, location Melbourne VIC, Education type/Problems/level,
pin the score comment) are listed in studio_tasks for the Studio run.

--mode replace (Giulia, 13 Nov 2026: Shorts countdown 10 s -> 5 s, "fix all current shorts that are scheduled but
haven't yet posted and re-upload them"): every Short in the record that hasn't gone live and wasn't made with the
current countdown (config/shorts.json think_seconds) is uploaded again from the new files. The new upload takes the
old one's publish slot; the old video is kept private with its schedule removed (never deleted; deleting needs
Giulia's OK) and its record moves to "replaced". Shorts due within REPLACE_MARGIN_MINUTES are left alone.

Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import upload_youtube as up  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")
REPLACE_MARGIN_MINUTES = 90  # a Short due sooner than this is left as it is (it may already be going live)


def upload_captions(token, vid, srt_bytes, tries=6, wait=20):
    """Captions right after an upload can get 404 videoNotFound (quiz-12 Short 2, 12 Nov 2026): retry."""
    data, ctype = up.multipart({"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                               srt_bytes, "application/octet-stream")
    for i in range(tries):
        code, _, _ = up.http("POST", f"{up.UPLOAD_API}/captions?part=snippet&uploadType=multipart", token, data,
                             {"Content-Type": ctype}, expect=(200, 201, 404))
        if code in (200, 201):
            return "uploaded"
        time.sleep(wait)
    return "not uploaded (video not found yet); add in Studio"


def needs_replacing(r, think, now):
    """A Short record that hasn't gone live and wasn't made with the current countdown."""
    if not r.get("video_id") or r.get("countdown_seconds") == think:
        return False
    if r.get("status") == "scheduled":
        p = r.get("publish_at")
        if not p:
            return False
        return dt.datetime.fromisoformat(p.replace("Z", "+00:00")) > now + dt.timedelta(minutes=REPLACE_MARGIN_MINUTES)
    return True  # uploaded but never scheduled (e.g. a failed run): replace it too


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
    # Giulia, 11 Nov 2026: every Short carries the quiz's researched tags (vidIQ/Apify, quiz.json "tags")
    for t in scfg.get("tags", [])[:1] + quiz.get("tags", []) + scfg.get("tags", [])[1:] \
            + ycfg.get("series_tags", {}).get(quiz.get("series", ""), []):
        if t.lower() not in {x.lower() for x in tags} and up.tag_length(tags + [t]) <= 500:
            tags.append(t)
    return {"title": s["title"], "description": desc, "tags": tags}


def default_meta(quiz, qdir, scfg, made):
    """Titles/openings for a quiz with no hand-written shorts.json: rotate the config hooks, then name the quiz."""
    rec = json.loads((qdir / "upload.json").read_text()) if (qdir / "upload.json").exists() else {}
    if not rec.get("video_id"):
        raise SystemExit("The full quiz isn't uploaded yet (no video_id in upload.json), so the Shorts can't link to it.")
    series, number = quiz.get("series", "Quiz"), quiz.get("number", "")
    titles, openings = scfg["title_hooks"], scfg["opening_hooks"]
    start = int(number or 0) % len(titles)  # a different first hook each quiz
    shorts = {}
    for i, m in enumerate(made):
        n = len(m["questions"])
        k = (start + i) % len(titles)
        shorts[str(m["short"])] = {"title": f"{titles[k].format(n=n)} {series} Quiz #{number}",
                                   "opening": openings[k % len(openings)].format(n=n), "pattern": "config default"}
    return {"_comment": "Made from config/shorts.json title_hooks/opening_hooks (no hand-written titles for this quiz).",
            "full_quiz_video_id": rec["video_id"],
            "series_tag": "".join(ch for ch in series.lower() if ch.isalnum()) or "quiz", "shorts": shorts}


def recording_date(upload_day, video_key, lo=2, hi=7):
    """Recording date a few days before upload (Giulia: 'one week prior or a couple of days prior; vary these').
    Varies per Short but is stable for the same Short, so a re-run records the same date."""
    import hashlib
    back = lo + int(hashlib.sha256(video_key.encode()).hexdigest(), 16) % (hi - lo + 1)
    return (upload_day - dt.timedelta(days=back)).strftime("%Y-%m-%dT00:00:00Z")


def short_problems(quiz, made_entry):
    """Studio > Education > Problems for a Short: timecode in the Short, then the question."""
    qs = {q["n"]: q["question"] for q in quiz["questions"] if isinstance(q, dict)}
    starts = made_entry.get("question_starts") or [None] * len(made_entry["questions"])
    return "\n".join((f"{up.stamp(t)} " if t is not None else "") + qs[n]
                     for n, t in zip(made_entry["questions"], starts) if n in qs)


def set_paid_promotion_no(token, vid):
    """Paid promotion = No (Giulia, 11 Nov 2026). A separate call so an API refusal never stops an upload."""
    body = {"id": vid, "paidProductPlacementDetails": {"hasPaidProductPlacement": False}}
    code, _, _ = up.http("PUT", f"{up.API}/videos?part=paidProductPlacementDetails", token,
                         json.dumps(body).encode(), {"Content-Type": "application/json"}, expect=(200, 400, 403))
    return "no" if code == 200 else f"not set by API ({code}); set it in Studio"


def short_level(quiz, scfg):
    """Studio Level for a Short: config "level" if set, else from the quiz difficulty (hard = Advanced)."""
    st = scfg.get("studio", {})
    return st.get("level") or st.get("level_by_difficulty", {}).get((quiz.get("difficulty") or "medium").lower(), "")


def short_studio_tasks(meta, scfg, problems, playlist, level=""):
    st = scfg.get("studio", {})
    return [f"Related video: link to the full quiz https://youtu.be/{meta['full_quiz_video_id']}.",
            f"Playlist: check it is in '{playlist}'.",
            "Paid promotion: 'No, my video doesn't include paid promotion'.",
            f"Video location: {st.get('location', 'Melbourne, VIC')}.",
            "Recording date: check it is set (see recording_date in this record).",
            f"Category Education: Type = {st.get('education_type', 'Activity')}; Problems = the 'problems' in this record"
            f"{'; Level = ' + level if level else ''}.",
            "Altered or synthetic content: No (it's Giulia's own voice).",
            "Pin the score comment once it is posted."]


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


def unschedule(token, vid, status_fields):
    """Keep a replaced Short private and remove its publish time (never deletes it)."""
    body = {"id": vid, "status": {"privacyStatus": "private", **status_fields}}
    up.http("PUT", f"{up.API}/videos?part=status", token, json.dumps(body).encode(),
            {"Content-Type": "application/json"})
    st = {}
    for i in range(7):  # YouTube can report the old publishAt for a while after the change (quiz-10, 13 Nov)
        if i:
            time.sleep(10)
        _, _, r = up.http("GET", f"{up.API}/videos?part=status&id={vid}", token)
        items = r.get("items", [])
        if not items:
            return "not found"
        st = items[0]["status"]
        if st.get("privacyStatus") == "private" and not st.get("publishAt"):
            return "yes"
    return f"no ({st})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, help="quizzes/<quiz>")
    ap.add_argument("--dir", required=True, help="folder with make_shorts.py output")
    ap.add_argument("--thumbnail", help="fallback thumbnail if a Short has none of its own")
    ap.add_argument("--mode", choices=["preview", "upload", "retitle", "defaults", "replace"], default="preview",
                    help="retitle = update the title/description of Shorts already uploaded to match shorts.json; "
                         "defaults = re-apply tags and paid promotion No to every Short already uploaded")
    args = ap.parse_args()

    qdir, sdir = Path(args.quiz), Path(args.dir)
    quiz = json.loads((qdir / "quiz.json").read_text())
    scfg_ = json.loads((ROOT / "config" / "shorts.json").read_text())
    if (qdir / "shorts.json").exists():
        meta = json.loads((qdir / "shorts.json").read_text())
    else:
        meta = default_meta(quiz, qdir, scfg_, json.loads((sdir / "shorts.json").read_text()))
        if args.mode != "preview":
            (qdir / "shorts.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    scfg = json.loads((ROOT / "config" / "shorts.json").read_text())
    ycfg = json.loads((ROOT / "config" / "youtube.json").read_text())
    rec_path = qdir / "shorts-upload.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {"quiz": quiz["id"], "shorts": {}}

    def save():
        rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))

    if args.mode == "defaults":
        # Giulia, 11 Nov 2026: bring every uploaded Short up to the standard settings the API can set
        # (title/description/tags as metadata() builds them, paid promotion No). Studio-only settings
        # (location, type, Problems, Level, related video) are done by the Mac task (docs/mac-studio-task.md).
        token = up.access_token()
        up.check_channel(token, ycfg)
        done = {}
        for n, r in rec["shorts"].items():
            if not r.get("video_id"):
                continue
            md = metadata(int(n), quiz, meta, scfg, ycfg)
            body = {"id": r["video_id"], "snippet": {"title": md["title"], "description": md["description"],
                                                     "tags": md["tags"], "categoryId": ycfg["category_id"],
                                                     "defaultLanguage": ycfg["language"],
                                                     "defaultAudioLanguage": ycfg["language"]}}
            _, _, resp = up.http("PUT", f"{up.API}/videos?part=snippet", token, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
            if resp.get("snippet", {}).get("title") != md["title"]:
                raise SystemExit(f"Short {n}: YouTube didn't confirm the update")
            back = resp.get("snippet", {}).get("tags")  # YouTube may not echo tags exactly; record what it says
            r["tags_confirmed"] = len(back) if back is not None else "not echoed"
            r.update(title=md["title"], description=md["description"], tags=md["tags"],
                     paid_promotion=set_paid_promotion_no(token, r["video_id"]))
            r["problems"] = r.get("problems") or short_problems(quiz, {"questions": r.get("questions", [])})
            r["studio_tasks"] = short_studio_tasks(meta, scfg, r["problems"], up.playlist_title(quiz, ycfg),
                                                   short_level(quiz, scfg))
            done[n] = {"video_id": r["video_id"], "tags_sent": len(md["tags"]), "tags_confirmed": r["tags_confirmed"],
                       "paid_promotion": r["paid_promotion"]}
            save()
        print(json.dumps({"defaults": done}, indent=2, ensure_ascii=False))
        return

    if args.mode == "retitle":
        token = up.access_token()
        up.check_channel(token, ycfg)
        changed = {}
        for n, r in rec["shorts"].items():
            md = metadata(int(n), quiz, meta, scfg, ycfg)
            if not r.get("video_id") or (r.get("title") == md["title"] and r.get("description") == md["description"]):
                continue
            body = {"id": r["video_id"], "snippet": {"title": md["title"], "description": md["description"],
                                                     "tags": md["tags"], "categoryId": ycfg["category_id"],
                                                     "defaultLanguage": ycfg["language"],
                                                     "defaultAudioLanguage": ycfg["language"]}}
            _, _, resp = up.http("PUT", f"{up.API}/videos?part=snippet", token, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
            if resp.get("snippet", {}).get("title") != md["title"]:
                raise SystemExit(f"Short {n}: YouTube didn't confirm the new title")
            r.update(title=md["title"], description=md["description"])
            changed[n] = md["title"]
            save()
        print(json.dumps({"retitled": changed}, indent=2, ensure_ascii=False))
        return

    made = json.loads((sdir / "shorts.json").read_text())
    now = dt.datetime.now(dt.timezone.utc)
    think = scfg.get("think_seconds", 5)
    targets = {}  # Short number -> the publish slot it keeps when replaced
    if args.mode == "replace":
        for m in made:
            n = str(m["short"])
            old = rec["shorts"].get(n)
            if old and needs_replacing(old, think, now):
                if old.get("status") == "scheduled":
                    targets[n] = old["publish_at"]
                old = {**old, "replaced_reason": f"countdown changed to {think} s (Giulia, 13 Nov 2026)",
                       "keep_slot": targets.get(n)}
                rec.setdefault("replaced", []).append(old)
                rec["shorts"][n] = {"short": m["short"], "status": "uploading", "steps": {},
                                    "countdown_seconds": m.get("countdown_seconds"), "replaces": old["video_id"],
                                    "recording_date": old.get("recording_date")}
                if targets.get(n):
                    rec["shorts"][n]["keep_slot"] = targets[n]
        save()
        args.mode = "upload"
    for n, r in rec["shorts"].items():  # a resumed run keeps the slots it was given
        if r.get("keep_slot") and r.get("status") != "scheduled":
            targets[n] = r["keep_slot"]

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
    playlist = up.playlist_title(quiz, ycfg)
    today = dt.datetime.now(dt.timezone.utc)
    for m in todo:
        n = str(m["short"])
        r = rec["shorts"].setdefault(n, {"short": m["short"], "status": "uploading", "steps": {}})
        md = metadata(m["short"], quiz, meta, scfg, ycfg)
        r.setdefault("recording_date", recording_date(today, f"{quiz['id']}-short-{n}",
                                                      *scfg.get("studio", {}).get("recording_days_before", [2, 7])))
        r["problems"] = short_problems(quiz, m)
        if not r.get("video_id"):
            body = {"snippet": {"title": md["title"], "description": md["description"], "tags": md["tags"],
                                "categoryId": ycfg["category_id"], "defaultLanguage": ycfg["language"],
                                "defaultAudioLanguage": ycfg["language"]},
                    "status": {"privacyStatus": "private", **status_fields},
                    "recordingDetails": {"recordingDate": r["recording_date"]}}
            resp = up.upload_video(token, sdir / m["file"], body, ycfg.get("notify_subscribers", True))
            r.update(video_id=resp["id"], url=f"https://youtube.com/shorts/{resp['id']}", title=md["title"],
                     description=md["description"],
                     upload_completed_at=up.iso(dt.datetime.now(dt.timezone.utc)), questions=m["questions"],
                     countdown_seconds=m.get("countdown_seconds"))
            save()
        vid, steps = r["video_id"], r.setdefault("steps", {})
        if "paid_promotion" not in steps:
            steps["paid_promotion"] = set_paid_promotion_no(token, vid)
            save()
        if "captions" not in steps and (sdir / m["captions"]).exists():
            steps["captions"] = upload_captions(token, vid, (sdir / m["captions"]).read_bytes())
            save()
        thumb = sdir / m["thumbnail"] if m.get("thumbnail") else (Path(args.thumbnail) if args.thumbnail else None)
        if "thumbnail" not in steps and thumb and thumb.exists():
            code, _, _ = up.http("POST", f"{up.UPLOAD_API}/thumbnails/set?videoId={vid}", token,
                                 thumb.read_bytes(), {"Content-Type": "image/jpeg"},
                                 expect=(200, 201, 400, 403))
            steps["thumbnail"] = thumb.name if code in (200, 201) else f"not accepted ({code})"
            save()
        if "playlist" not in steps:  # same series playlist as the full quiz (Giulia, 9 Nov)
            pid, ptitle, created = up.find_or_create_playlist(token, playlist, quiz.get("series", ""))
            pl = {"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}
            up.http("POST", f"{up.API}/playlistItems?part=snippet", token, json.dumps(pl).encode(),
                    {"Content-Type": "application/json"})
            steps["playlist"] = {"id": pid, "title": ptitle, "created": created}
            save()
        r["studio_tasks"] = short_studio_tasks(meta, scfg, r["problems"], playlist, short_level(quiz, scfg))
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
        if r.get("replaces") and r.get("old_unscheduled") != "yes":
            # take the old upload out of the schedule first, so the two never both go live
            r["old_unscheduled"] = unschedule(token, r["replaces"], status_fields)
            save()
            if r["old_unscheduled"] != "yes":
                r["status"] = "old_still_scheduled"
                save()
                continue
        keep = targets.get(str(m["short"]))
        keep = dt.datetime.fromisoformat(keep.replace("Z", "+00:00")) if keep else None
        if keep and keep > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10):
            slot = keep.astimezone(ET)  # the replaced Short's own slot (its old upload no longer holds it)
        else:
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
