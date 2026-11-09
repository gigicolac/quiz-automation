#!/usr/bin/env python3
"""Build a quiz's question slides in Canva through the Connect API, then export them as 4K MP4.

For each question in quizzes/<quiz>/quiz.json:
  1. upload the question and answer GIFs (or still images) from gifs_selected.json as Canva assets
  2. autofill the "OMQ Quiz Pair" brand template (fields: question, question_gif, question_repeat,
     answer, answer_gif) into a new 2-page design
  3. export that design as MP4
Then joins the pairs in order into <out>/slides.mp4, which the Build video workflow uses instead of
downloading a hand-made export. Intro/rules/outro come from build.json "canva_export" as before.

quizzes/<quiz>/build.json:
  {"canva_build": {"template": "EAHaZJo0d7w", "quality": "horizontal_4k", "parallel": 4}, "canva_export": {...intro/rules/outro...}}

Progress (asset IDs, design IDs) is kept in <out>/canva_state.json so a re-run resumes rather than redoing work.
Env: as scripts/canva_export.py (CANVA_CLIENT_ID, CANVA_CLIENT_SECRET, CANVA_REFRESH_TOKEN, GH_SECRETS_TOKEN, GITHUB_REPOSITORY).
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canva_export import access_token, call, export, join  # noqa: E402


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


def upload(token, name, url):
    job = call("POST", "/url-asset-uploads", token, {"name": name[:50], "url": url})["job"]
    return wait(token, "/url-asset-uploads", job, f"Upload of {name}")["asset"]["id"]


def media_url(m):
    return m.get("clean_mp4") or m.get("mp4") if m.get("type", "gif") == "gif" else m["url"]


def fill(token, template, title, q, qa, aa):
    data = {"question": {"type": "text", "text": q["question"]},
            "question_repeat": {"type": "text", "text": q["question"]},
            # template keeps "Answer:" green; autofill replaces the whole text box, so the label is re-added
            "answer": {"type": "text", "text": f"Answer: {q['answer']}"},
            "question_gif": {"type": "image", "asset_id": qa},
            "answer_gif": {"type": "image", "asset_id": aa}}
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

    state_path = out / "canva_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    token = access_token()
    label = quiz.get("series", "Quiz")

    def prepare(q):
        n, s = q["n"], state.setdefault(str(q["n"]), {})
        g = gifs[n]
        for slot in ("question_gif", "answer_gif"):
            if slot not in s:
                s[slot] = upload(token, f"{quiz['id']} Q{n} {slot}", media_url(g[slot]))
        if "design" not in s:
            s["design"] = fill(token, spec["template"], f"{label} Quiz #{quiz['number']} Q{n:02d}", q,
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


if __name__ == "__main__":
    main()
