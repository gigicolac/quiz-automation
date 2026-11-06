#!/usr/bin/env python3
"""Cut vertical YouTube Shorts (1080x1920) from a finished quiz video.

Each Short: a hook header, then N questions. Per question: the question read out, about 5 seconds of
countdown (the middle of the 10-second countdown is skipped when the reading is short), the buzzer,
then the answer reveal. It ends on a card pointing to the full quiz.

Layout from the 16:9 slide: question card on top, countdown/answer strip under it, picture card below,
over a blurred copy of the slide.

Usage:
  make_shorts.py --video quiz-09.mp4 --report build_report.json --captions quiz-09.srt
                 --quiz quizzes/quiz-09/quiz.json --out shorts/ [--per 7] [--hooks config/shorts.json]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
# regions of the 1920x1080 slide (x, y, w, h)
QCARD, STRIP, PCARD = (978, 193, 832, 624), (500, 840, 920, 180), (88, 196, 830, 624)
CARD_W = 900


def run(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def srt_cues(path):
    def secs(t):
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    cues = []
    for block in Path(path).read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) >= 2 and "-->" in lines[1]:
            a, b = (secs(x.strip()) for x in lines[1].split("-->"))
            cues.append((a, b))
    return cues


def is_emoji(ch):
    return ord(ch) >= 0x2190 and not ch.isalnum()


def text_image(lines, width):
    """Render centred lines (text, size) with colour emoji; returns an RGBA image."""
    rendered = []
    for text, size in lines:
        font = ImageFont.truetype(FONT, size)
        efont = ImageFont.truetype(EMOJI, 109)
        runs, cur = [], ""
        for ch in text:
            if is_emoji(ch) or ch in "️‍":
                if cur:
                    runs.append(("t", cur))
                    cur = ""
                if ch not in "️‍":
                    runs.append(("e", ch))
            else:
                cur += ch
        if cur:
            runs.append(("t", cur))
        parts = []
        for kind, s in runs:
            if kind == "t":
                box = font.getbbox(s)
                im = Image.new("RGBA", (box[2] + 4, int(size * 1.35)), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.text((2, int(size * 0.05)), s, font=font, fill="white", stroke_width=max(2, size // 18),
                       stroke_fill=(20, 10, 40))
            else:
                im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((0, 0), s, font=efont, embedded_color=True)
                im = im.resize((int(size * 1.1), int(size * 1.05)), Image.LANCZOS)
            parts.append(im)
        if not parts:  # blank spacer line
            parts = [Image.new("RGBA", (1, size), (0, 0, 0, 0))]
        lw = sum(p.width for p in parts)
        lh = max(p.height for p in parts)
        line = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        x = 0
        for p in parts:
            line.alpha_composite(p, (x, (lh - p.height) // 2))
            x += p.width
        if line.width > width:
            line = line.resize((width, int(line.height * width / line.width)), Image.LANCZOS)
        rendered.append(line)
    h = sum(r.height for r in rendered) + 10 * (len(rendered) - 1)
    out = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    y = 0
    for r in rendered:
        out.alpha_composite(r, ((width - r.width) // 2, y))
        y += r.height + 10
    return out


def header_png(path, hook, sub):
    img = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
    t = text_image([(sub, 40), (hook, 78)], W - 80)
    img.alpha_composite(t, ((W - t.width) // 2, (300 - t.height) // 2 + 10))
    img.save(path)


def end_png(path, lines):
    img = Image.new("RGBA", (W, H), (10, 5, 30, 150))
    t = text_image(lines, W - 100)
    img.alpha_composite(t, ((W - t.width) // 2, (H - t.height) // 2))
    img.save(path)


def layout_filter(header):
    def crop(r, name):
        x, y, w, h = r
        nh = round(h * CARD_W / w / 2) * 2
        return f"[0:v]crop={w}:{h}:{x}:{y},scale={CARD_W}:{nh}[{name}]", nh
    fq, hq = crop(QCARD, "q")
    fs, hs = crop(STRIP, "s")
    fp, hp = crop(PCARD, "p")
    x = (W - CARD_W) // 2
    y1, y2, y3 = 300, 300 + hq + 18, 300 + hq + 18 + hs + 18
    return ";".join([
        f"[0:v]scale=-2:{H},crop={W}:{H},gblur=sigma=28,eq=brightness=-0.12[bg]", fq, fs, fp,
        f"[bg][q]overlay={x}:{y1}[b1]", f"[b1][s]overlay={x}:{y2}[b2]", f"[b2][p]overlay={x}:{y3}[b3]",
        f"[b3][1:v]overlay=0:0,fps=30,format=yuv420p[v]"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--captions", required=True)
    ap.add_argument("--quiz", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per", type=int, default=7)
    ap.add_argument("--think", type=float, default=5.0, help="seconds of countdown kept after the question is read")
    ap.add_argument("--hooks", default=str(Path(__file__).resolve().parent.parent / "config" / "shorts.json"))
    args = ap.parse_args()

    quiz = json.loads(Path(args.quiz).read_text())
    report = json.loads(Path(args.report).read_text())
    hooks = json.loads(Path(args.hooks).read_text())["hooks"]
    segs = {s["name"]: s for s in report["segments"]}
    cues = srt_cues(args.captions)
    out = Path(args.out)
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    nq = len([n for n in segs if re.fullmatch(r"q\d+", n)])
    groups = [list(range(i, min(i + args.per, nq + 1))) for i in range(1, nq + 1, args.per)]
    groups = [g for g in groups if len(g) == args.per]  # leftovers stay in the long video
    made = []
    for gi, qs in enumerate(groups, 1):
        hook = hooks[(gi - 1) % len(hooks)].format(n=len(qs))
        sub = f"{quiz.get('series', '')} Quiz #{quiz.get('number', '')} · Part {gi}"
        hdr = work / f"h{gi}.png"
        header_png(hdr, hook, sub)
        pieces = []
        for n in qs:
            q, a = segs[f"q{n:02d}"], segs[f"a{n:02d}"]
            t0, t_end = q["start"], q["start"] + q["dur"]
            spoken = [b for s_, b in cues if t0 <= s_ < t_end]
            tv = (max(spoken) if spoken else t0 + 4) + 0.3
            spans = [(t0, tv), (max(tv, t_end - args.think - 0.6), t_end)] if tv < t_end - args.think - 0.6 \
                else [(t0, t_end)]
            spans.append((a["start"], a["start"] + a["dur"]))
            for a0, a1 in spans:
                p = work / f"s{gi}_{len(pieces):03d}.mp4"
                d = a1 - a0
                run("-ss", f"{a0:.3f}", "-t", f"{d:.3f}", "-i", args.video, "-loop", "1", "-i", hdr,
                    "-filter_complex", layout_filter(hdr), "-map", "[v]", "-map", "0:a",
                    "-af", f"afade=t=in:d=0.03,afade=t=out:st={max(d - 0.04, 0):.3f}:d=0.04",
                    "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", p)
                pieces.append(p)
        # end card on the last answer frame
        endimg = work / f"e{gi}.png"
        end_png(endimg, [("Full 50-question quiz", 70), ("on our channel 👉", 70), ("@JustOneMoreQuiz", 64),
                         ("", 30), ("Comment your score! 👇", 62)])
        last = segs[f"a{qs[-1]:02d}"]
        still = work / f"still{gi}.png"
        run("-ss", f"{last['start'] + last['dur'] - 0.1:.3f}", "-i", args.video, "-frames:v", "1", still)
        p = work / f"s{gi}_end.mp4"
        run("-loop", "1", "-i", still, "-loop", "1", "-i", hdr,
            "-loop", "1", "-i", endimg, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-filter_complex", layout_filter(hdr).replace("[v]", "[v0]") + ";[v0][2:v]overlay=0:0[v]",
            "-map", "[v]", "-map", "3:a", "-t", "3", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k", p)
        pieces.append(p)
        lst = work / f"list{gi}.txt"
        lst.write_text("".join(f"file '{x.resolve()}'\n" for x in pieces))
        final = out / f"{quiz['id']}-short-{gi}.mp4"
        run("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", final)
        made.append({"file": final.name, "questions": qs, "hook": hook})
    (out / "shorts.json").write_text(json.dumps(made, indent=2, ensure_ascii=False))
    print(json.dumps(made, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
