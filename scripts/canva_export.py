#!/usr/bin/env python3
"""Export Canva designs as MP4 through the Canva Connect API (no chat connector needed).

Used by the Build video workflow when quizzes/<quiz>/build.json has a "canva_export" block:
  {"quality": "horizontal_4k", "chunk": 10,
   "slides": {"design": "DAHZXGh4_Gw", "pages": 100},
   "intro": {"design": "DAHZcxkxydk", "page": 1}, "rules": {...page 2}, "outro": {...page 3}}

Writes <out>/slides.mp4 (chunks joined in order), intro.mp4, rules.mp4, outro.mp4.

Canva issues a new refresh token every time one is used, so the new token is saved straight back to the
CANVA_REFRESH_TOKEN repository secret (needs GH_SECRETS_TOKEN). Run one Canva job at a time.

Env: CANVA_CLIENT_ID, CANVA_CLIENT_SECRET, CANVA_REFRESH_TOKEN, GH_SECRETS_TOKEN, GITHUB_REPOSITORY.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.canva.com/rest/v1"


def access_token():
    cid = os.environ["CANVA_CLIENT_ID"].strip()
    secret = os.environ["CANVA_CLIENT_SECRET"].strip()
    refresh = os.environ["CANVA_REFRESH_TOKEN"].strip()
    req = urllib.request.Request(
        f"{API}/oauth/token",
        data=urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": refresh}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Authorization": "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Canva token refresh failed ({e.code}): {e.read().decode()[:300]}. "
                 "Run the Sign in workflow for canva again (docs/sign-in.md).")
    new = tok.get("refresh_token")
    if new:
        print(f"::add-mask::{new}")
        env = {**os.environ, "GH_TOKEN": os.environ["GH_SECRETS_TOKEN"].strip()}
        subprocess.run(["gh", "secret", "set", "CANVA_REFRESH_TOKEN", "-R", os.environ["GITHUB_REPOSITORY"]],
                       input=new.encode(), env=env, check=True)
    print(f"::add-mask::{tok['access_token']}")
    return tok["access_token"]


def call(method, path, token, body=None):
    req = urllib.request.Request(f"{API}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(15 * (attempt + 1))
                continue
            sys.exit(f"Canva {method} {path} failed ({e.code}): {e.read().decode()[:300]}")
    sys.exit(f"Canva {method} {path} kept failing")


def export(token, design, pages, quality, dest, timeout=1800):
    fmt = {"type": "mp4", "quality": quality, "pages": pages}
    job = call("POST", "/exports", token, {"design_id": design, "format": fmt})["job"]
    t0 = time.time()
    while job["status"] == "in_progress":
        if time.time() - t0 > timeout:
            sys.exit(f"Canva export of {design} pages {pages[0]}-{pages[-1]} timed out")
        time.sleep(10)
        job = call("GET", f"/exports/{job['id']}", token)["job"]
    if job["status"] != "success":
        sys.exit(f"Canva export of {design} pages {pages[0]}-{pages[-1]} failed: {job.get('error')}")
    parts = []
    for i, url in enumerate(job["urls"]):
        p = dest.with_name(f"{dest.stem}.{i}.mp4")
        urllib.request.urlretrieve(url, p)
        parts.append(p)
    print(f"Exported {design} pages {pages[0]}-{pages[-1]} ({quality}) in {time.time() - t0:.0f}s")
    return parts


def join(parts, out):
    if len(parts) == 1:
        parts[0].rename(out)
        return
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True, help="quizzes/<quiz>/build.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.loads(Path(args.build).read_text())["canva_export"]
    out = Path(args.out)
    (out / "parts").mkdir(parents=True, exist_ok=True)
    quality, chunk = spec.get("quality", "horizontal_1080p"), int(spec.get("chunk", 10))
    token = access_token()

    s = spec["slides"]
    parts = []
    for i, first in enumerate(range(1, s["pages"] + 1, chunk)):
        pages = list(range(first, min(first + chunk, s["pages"] + 1)))
        parts += export(token, s["design"], pages, quality, out / "parts" / f"{i:03d}.mp4")
    join(parts, out / "slides.mp4")
    for k in ("intro", "rules", "outro"):
        if k in spec:
            p = spec[k]
            join(export(token, p["design"], [p["page"]], quality, out / "parts" / f"{k}.mp4"), out / f"{k}.mp4")


if __name__ == "__main__":
    main()
