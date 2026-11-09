#!/usr/bin/env python3
"""Build a quiz's question slides in Canva through the Connect API, then export them as 4K MP4.

For each question in quizzes/<quiz>/quiz.json:
  1. upload the question and answer GIFs (or still images) from gifs_selected.json as Canva assets
  2. autofill the "OMQ Quiz Pair" brand template (fields: question, question_gif, question_repeat,
     answer, answer_gif) into a new 2-page design
  3. export that design as MP4
Then joins the pairs in order into <out>/slides.mp4, and fills the intro template ("<series> Quiz", "Quiz # <n>")
for intro.mp4 / rules.mp4 / outro.mp4. The Build video workflow uses these instead of a hand-made export.

Three versions of the template differ only in question font size, so long questions never run off the card
(Giulia, 9 Nov); each question uses the largest size its length allows. The green "Answer:" label is fixed in
the template and the answer field is black, so answers must stay short (MAX_ANSWER characters).

quizzes/<quiz>/build.json:
  {"canva_build": {"quality": "horizontal_4k", "parallel": 4}, "canva_export": {...intro/rules/outro...}}
  (optional "templates": [[max_question_chars, brand_template_id], ...] overrides TEMPLATES)

Progress (asset IDs, design IDs) is kept in <out>/canva_state.json so a re-run resumes rather than redoing work.
Env: as scripts/canva_export.py (CANVA_CLIENT_ID, CANVA_CLIENT_SECRET, CANVA_REFRESH_TOKEN, GH_SECRETS_TOKEN, GITHUB_REPOSITORY).
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canva_export import access_token, call, export, join  # noqa: E402


# (longest question that fits, brand template): large 116px, medium 88px, small 68px text
TEMPLATES = [(60, "EAHaZJo0d7w"), (95, "EAHaZMCHgTI"), (170, "EAHaZCRO1wg")]
# intro (page 1: "<series> Quiz" / "Quiz # <n>"), rules (page 2) and outro (page 3)
INTRO_TEMPLATE = "EAHaZFWuBik"
MAX_ANSWER = 30


def pick_template(question, templates=TEMPLATES):
    for limit, tid in templates:
        if len(question) <= limit:
            return tid
    return None


def check_text(questions, templates=TEMPLATES):
    """Questions/answers that won't fit any template (so the build stops before using Canva)."""
    bad = []
    for q in questions:
        if not pick_template(q["question"], templates):
            bad.append(f"Q{q['n']} question is {len(q['question'])} characters (max {templates[-1][0]})")
        if len(q["answer"]) > MAX_ANSWER:
            bad.append(f"Q{q['n']} answer is {len(q['answer'])} characters (max {MAX_ANSWER})")
    return bad


def wait(token, path, job, what, timeout=600):
    t0 = time.time()
    while job["status"] == "in_progress":
        if time.time() - t0 > timeout:
            sys.exit(f"{what} timed out")
        time.sleep(3)
        job = call("GET", f"{path}/{job['id']}", token)["job"]
    if job["status"] != "success":
        sys.exit(f"{what} failed: {job.get('error')}")
    return job


class UploadFailed(Exception):
    pass


def upload(token, name, url, timeout=300):
    """Returns (asset_id, "image" | "video")."""
    job = call("POST", "/url-asset-uploads", token, {"name": name[:50], "url": url})["job"]
    t0 = time.time()
    while job["status"] == "in_progress" and time.time() - t0 < timeout:
        time.sleep(3)
        job = call("GET", f"/url-asset-uploads/{job['id']}", token)["job"]
    if job["status"] != "success":
        raise UploadFailed(f"upload of {url} failed: {job.get('error') or job['status']}")
    asset = job["asset"]
    return asset["id"], asset.get("type", "image")


# (name, max question characters, max answer characters) — measured on the template's text boxes:
# large 116px question / 60px answer, medium 92 / 48, small 74 / 40.
SIZES = [("large", 58, 26), ("medium", 80, 34), ("small", 140, 44)]


def size_for(q):
    for name, qmax, amax in SIZES:
        if len(q["question"]) <= qmax and len(q["answer"]) <= amax:
            return name
    sys.exit(f"Q{q['n']} is too long for the smallest template (question {len(q['question'])} chars, "
             f"answer {len(q['answer'])} chars). Shorten it in quiz.json.")


def media_url(m):
    return m.get("clean_mp4") or m.get("mp4") if m.get("type", "gif") == "gif" else m["url"]


def fill(token, template, title, q, qa, aa):
    """qa/aa: (asset_id, type). The green "Answer:" label is part of the template."""
    data = {"question": {"type": "text", "text": q["question"]},
            "question_repeat": {"type": "text", "text": q["question"]},
            "answer": {"type": "text", "text": q["answer"]},
            "question_gif": {"type": qa[1], "asset_id": qa[0]},
            "answer_gif": {"type": aa[1], "asset_id": aa[0]}}
    job = call("POST", "/autofills", token, {"brand_template_id": template, "title": title, "data": data})["job"]
    return wait(token, "/autofills", job, f"Autofill of {title}")["result"]["design"]["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, help="quizzes/<quiz>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", type=int, nargs="*", help="question numbers (for a quick test)")
    args = ap.parse_args()
    qdir, out = Path(args.quiz), Path(args.out)
    (out / "pairs").mkdir(parents=True, exist_ok=True)
    spec = json.loads((qdir / "build.json").read_text())["canva_build"]
    quiz = json.loads((qdir / "quiz.json").read_text())
    gifs = {g["n"]: g for g in json.loads((qdir / "gifs_selected.json").read_text())}
    questions = [q for q in quiz["questions"] if not args.only or q["n"] in args.only]
    missing = [q["n"] for q in questions if not ({"question_gif", "answer_gif"} <= gifs.get(q["n"], {}).keys())]
    if missing:
        sys.exit(f"No GIF or image chosen for questions {missing} (gifs_selected.json)")
    templates = [tuple(t) for t in spec.get("templates", TEMPLATES)]
    bad = check_text(questions, templates)
    if bad:
        sys.exit("Text too long for the slide templates (shorten in quiz.json):\n" + "\n".join(bad))

    state_path = out / "canva_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    token = access_token()
    if os.environ.get("GITHUB_ENV"):  # later Canva steps in this job reuse it (the refresh token has rotated)
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write(f"CANVA_ACCESS_TOKEN={token}\n")
    label = quiz.get("series", "Quiz")

    def prepare(q):
        n, s = q["n"], state.setdefault(str(q["n"]), {})
        g = gifs[n]
        for slot in ("question_gif", "answer_gif"):
            if slot not in s:
                urls = [media_url(g[slot])] + ([g[slot]["still"]] if g[slot].get("still") else [])
                for i, url in enumerate(urls):  # a GIF Canva can't fetch falls back to its still frame
                    try:
                        s[slot] = upload(token, f"{quiz['id']} Q{n} {slot}", url)
                        break
                    except UploadFailed as e:
                        if i == len(urls) - 1:
                            sys.exit(f"Q{n} {slot}: {e}. Pick another GIF or image in gifs_selected.json.")
        if "design" not in s:
            s["template"] = pick_template(q["question"], templates)
            s["design"] = fill(token, s["template"], f"{label} Quiz #{quiz['number']} Q{n:02d}", q,
                               s["question_gif"], s["answer_gif"])
        print(f"Q{n}: design {s['design']}", flush=True)
        return n

    with ThreadPoolExecutor(int(spec.get("parallel", 4))) as pool:
        for _ in pool.map(prepare, questions):
            state_path.write_text(json.dumps(state, indent=1))

    quality = spec.get("quality", "horizontal_4k")

    def render(q):
        n = q["n"]
        dest = out / "pairs" / f"{n:03d}.mp4"
        if not dest.exists():
            join(export(token, state[str(n)]["design"], [1, 2], quality, out / "pairs" / f"{n:03d}.part.mp4"), dest)
        return dest

    with ThreadPoolExecutor(int(spec.get("parallel", 4))) as pool:
        parts = list(pool.map(render, questions))
    join(parts, out / "slides.mp4")
    print(f"slides.mp4 from {len(parts)} pairs")

    if args.only:  # quick test: question slides only
        return
    # intro / rules / outro from the intro template, with this quiz's series and number
    if "intro_design" not in state:
        data = {"series_title": {"type": "text", "text": f"{label} Quiz"},
                "quiz_number": {"type": "text", "text": f"Quiz # {quiz['number']}"}}
        job = call("POST", "/autofills", token, {"brand_template_id": spec.get("intro_template", INTRO_TEMPLATE),
                                                  "title": f"{label} Quiz #{quiz['number']} (intro and outro)",
                                                  "data": data})["job"]
        state["intro_design"] = wait(token, "/autofills", job, "Autofill of the intro")["result"]["design"]["id"]
        state_path.write_text(json.dumps(state, indent=1))
    for page, name in ((1, "intro"), (2, "rules"), (3, "outro")):
        join(export(token, state["intro_design"], [page], quality, out / "pairs" / f"{name}.part.mp4"),
             out / f"{name}.mp4")
    print(f"intro/rules/outro from {state['intro_design']}")


if __name__ == "__main__":
    main()
