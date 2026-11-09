#!/usr/bin/env python3
"""Make a quiz's two YouTube thumbnails (A and B, for Studio's Test & Compare) from the Canva brand template.

Template "OMQ Thumbnail A-B" (EAHaZaB3wtY), the Quiz #9 thumbnail design with fields:
  page 1 (A, red top bar):  series, number, tagline, img1..img12
  page 2 (B, blue top bar): b_series, b_number, b_tagline, b_img1..b_img12
The 12 picture tiles are stills from the quiz's answer GIFs (spread across the quiz), so every thumbnail shows
pictures from the quiz itself. Tagline: quiz.json "thumbnail_tagline", else config/youtube.json
thumbnail_taglines[series], else "Everyone should know".

Writes <out>/thumbnail-a.jpg and <out>/thumbnail-b.jpg (1280x720). The upload step uses thumbnail-a.jpg; the
Studio task uses thumbnail-b.jpg for the A/B test.
Env: as scripts/canva_export.py (CANVA_TOKEN_CACHE shares the access token within a job).
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from canva_build import UploadFailed, upload, wait  # noqa: E402
from canva_export import access_token, call  # noqa: E402

TEMPLATE = "EAHaZaB3wtY"
ROOT = Path(__file__).resolve().parent.parent


def still(m):
    """A still image for a tile: the GIF's first frame, or the chosen image itself."""
    return m.get("still") if m.get("type", "gif") == "gif" else m.get("url")


def tiles(gifs, count=12):
    """Up to `count` stills spread evenly across the quiz, answer GIFs first, then question GIFs."""
    pool = [still(g[s]) for s in ("answer_gif", "question_gif") for g in gifs if g.get(s) and still(g[s])]
    seen, out = set(), []
    step = max(1, len(gifs) // count)
    order = list(range(0, len(pool), step)) + list(range(len(pool)))
    for i in order:
        if pool[i] not in seen:
            seen.add(pool[i])
            out.append(pool[i])
        if len(out) == count:
            break
    return out


def tagline(quiz):
    if quiz.get("thumbnail_tagline"):
        return quiz["thumbnail_tagline"]
    cfg = json.loads((ROOT / "config/youtube.json").read_text())
    return cfg.get("thumbnail_taglines", {}).get(quiz.get("series", ""), "Everyone should know")


def export_jpg(token, design, page, dest):
    job = call("POST", "/exports", token, {"design_id": design, "format": {"type": "jpg", "quality": 92, "pages": [page]}})["job"]
    job = wait(token, "/exports", job, f"Thumbnail export page {page}")
    urllib.request.urlretrieve(job["urls"][0], dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True, help="quizzes/<quiz>")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    qdir, out = Path(args.quiz), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    quiz = json.loads((qdir / "quiz.json").read_text())
    gifs = json.loads((qdir / "gifs_selected.json").read_text())
    token = access_token()

    assets = []
    for i, url in enumerate(tiles(gifs * 2 if len(gifs) < 6 else gifs)):
        try:
            assets.append(upload(token, f"{quiz['id']} thumb tile {i + 1}", url)[0])
        except UploadFailed as e:
            print(f"::warning::{e}")
    if len(assets) < 12:
        assets += assets[:12 - len(assets)] if assets else []
    if len(assets) < 12:
        sys.exit("Not enough pictures for the thumbnail tiles")

    series, number, line = quiz.get("series", "Quiz"), f"Quiz #{quiz['number']}", tagline(quiz)
    data = {}
    for prefix in ("", "b_"):
        data[f"{prefix}series"] = {"type": "text", "text": f" {series} "}
        data[f"{prefix}number"] = {"type": "text", "text": number}
        data[f"{prefix}tagline"] = {"type": "text", "text": line}
        for i, a in enumerate(assets[:12], 1):
            data[f"{prefix}img{i}"] = {"type": "image", "asset_id": a}
    job = call("POST", "/autofills", token, {"brand_template_id": TEMPLATE, "data": data,
                                              "title": f"{series} Quiz #{quiz['number']} (thumbnails A-B)"})["job"]
    design = wait(token, "/autofills", job, "Thumbnail autofill")["result"]["design"]["id"]
    export_jpg(token, design, 1, out / "thumbnail-a.jpg")
    export_jpg(token, design, 2, out / "thumbnail-b.jpg")
    print(f"Thumbnails A and B from design {design} (tagline: {line})")


if __name__ == "__main__":
    main()
