#!/usr/bin/env python3
"""Make a quiz's two YouTube thumbnails (A and B, for Studio's Test & Compare) in code, at 2560x1440.

Replaces the Canva thumbnail template (Giulia, 10 Nov 2026, on Quiz #10: the heading was too small and the
image wasn't sharp). Same layout as before, but the heading ("Disney Quiz #10") is sized to fill the full width
of the top band whatever the series name, and everything is drawn at twice YouTube's 1280x720 so it stays crisp.

  top band     heading: series (bold sans) + "Quiz #<n>" (italic serif), fitted to the full width
  middle       12 picture tiles from the quiz's own GIFs and images (2 rows x 6)
  bottom band  the hook line (quiz.json "thumbnail_tagline", else config/youtube.json thumbnail_taglines[series]),
               fitted to the same full width as the heading so the two read as one line of thought

A and B differ in one thing only, set in config/youtube.json "thumbnail_test" (default: the top band colour),
so the Test & Compare result says which one thing worked.

Usage: make_thumbnails.py --quiz quizzes/quiz-11 --out DIR [--tiles DIR_OF_IMAGES]
Without --tiles, the tile pictures are downloaded from gifs_selected.json (GIF first frames or chosen images).
Fonts: the original Canva thumbnail's own (Giulia, 10 Nov: "use the same fonts"). Its PDF export embeds
NunitoSans10pt-Bold (series and hook line) and TimesNRMTPro-Italic ("Quiz #n"). Nunito Sans is a free Google font;
Times New Roman Pro is licensed, so its free metric-compatible twin Tinos Italic (same letter shapes and widths)
stands in. Override with THUMB_SANS / THUMB_SERIF_ITALIC.
"""
import argparse
import io
import json
import os
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 2560, 1440
TOP, BOTTOM = 400, 1040         # top band ends / bottom band starts (equal bands, so both lines can match)
MARGIN = 70
SANS = os.environ.get("THUMB_SANS", "/usr/share/fonts/truetype/google-fonts/NunitoSans-Bold.ttf")
SERIF_I = os.environ.get("THUMB_SERIF_ITALIC", "/usr/share/fonts/truetype/google-fonts/Tinos-Italic.ttf")
MAX_BYTES = 2_000_000            # YouTube's thumbnail limit is 2 MB

STYLES = {  # top band fill: a solid colour, or a left-to-right gradient
    "red": ("solid", (255, 49, 49)),
    "blue": ("gradient", (0, 0, 0), (53, 51, 205)),
    "yellow": ("solid", (255, 204, 0)),
    "purple": ("gradient", (40, 8, 80), (156, 118, 244)),
}


def band(img, box, style):
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    if style[0] == "solid":
        d.rectangle(box, fill=style[1])
        return
    a, b = style[1], style[2]
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0 - 1)
        d.line([(x, y0), (x, y1)], fill=tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def text_colour(style):
    """White text, except on a light solid band."""
    c = style[1] if style[0] == "solid" else style[2]
    return (20, 10, 40) if sum(c) / 3 > 170 and style[0] == "solid" and c[2] < 100 else (255, 255, 255)


def fit_heading(series, number, max_w, max_h):
    """Largest size at which '<series> Quiz #<n>' fits in max_w x max_h. Returns (fonts, parts, width, height)."""
    lo, hi, best = 40, 600, None
    while lo <= hi:
        size = (lo + hi) // 2
        sans, serif = ImageFont.truetype(SANS, size), ImageFont.truetype(SERIF_I, round(size * 1.06))
        parts = [(series + " ", sans), (f"Quiz #{number}", serif)]
        w = sum(f.getlength(t) for t, f in parts)
        h = max(f.getbbox(t)[3] - f.getbbox(t)[1] for t, f in parts)
        if w <= max_w and h <= max_h:
            best, lo = (parts, w, h), size + 1
        else:
            hi = size - 1
    return best


def fit_line(text, font_path, max_w, max_h):
    lo, hi, best = 40, 400, None
    while lo <= hi:
        size = (lo + hi) // 2
        f = ImageFont.truetype(font_path, size)
        box = f.getbbox(text)
        if f.getlength(text) <= max_w and box[3] - box[1] <= max_h:
            best, lo = f, size + 1
        else:
            hi = size - 1
    return best


def draw_shadowed(img, xy, text, font, fill):
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((xy[0] + 6, xy[1] + 8), text, font=font, fill=(0, 0, 0, 150))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text(xy, text, font=font, fill=fill)


def cover(im, w, h):
    """Scale and centre-crop to exactly w x h."""
    im = im.convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def tile_sources(gifs, count=12):
    """Up to `count` picture URLs spread evenly across the quiz, answer pictures first."""
    def still(m):
        return m.get("still") if m.get("type", "gif") == "gif" else m.get("url")
    pool = [still(g[s]) for s in ("answer_gif", "question_gif") for g in gifs if g.get(s) and still(g[s])]
    step = max(1, len(gifs) // count)
    seen, out = set(), []
    for i in list(range(0, len(pool), step)) + list(range(len(pool))):
        if pool[i] not in seen:
            seen.add(pool[i])
            out.append(pool[i])
        if len(out) == count:
            break
    return out


def load_tiles(args, quiz_dir):
    if args.tiles:
        files = sorted(p for p in Path(args.tiles).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"))
        return [Image.open(p) for p in files][:12]
    gifs = json.loads((quiz_dir / "gifs_selected.json").read_text())
    out = []
    for url in tile_sources(gifs):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "quiz-automation thumbnails"})
            out.append(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())))
        except Exception as e:  # a missing picture just leaves room for the others
            print(f"::warning::thumbnail tile {url}: {e}")
    return out


def tagline(quiz):
    if quiz.get("thumbnail_tagline"):
        return quiz["thumbnail_tagline"]
    cfg = json.loads((ROOT / "config/youtube.json").read_text())
    return cfg.get("thumbnail_taglines", {}).get(quiz.get("series", ""), "Can you get them all?")


def render(quiz, tiles, style, line):
    img = Image.new("RGBA", (W, H), (26, 16, 53, 255))
    # tiles: 2 rows x 6, thin dark gaps
    cols, rows, gap = 6, 2, 6
    tw, th = (W - gap * (cols - 1)) / cols, (BOTTOM - TOP - gap * (rows - 1)) / rows
    pics = (tiles * 12)[:12] if tiles else []
    for i, pic in enumerate(pics):
        r, c = divmod(i, cols)
        x, y = round(c * (tw + gap)), round(TOP + r * (th + gap))
        img.paste(cover(pic, round(tw), round(th)), (x, y))
    # top band + heading, fitted to the full width
    band(img, (0, 0, W, TOP), STYLES[style])
    colour = text_colour(STYLES[style])
    parts, w, h = fit_heading(quiz.get("series", "Quiz"), quiz["number"], W - 2 * MARGIN, TOP * 0.86)
    x = (W - w) / 2
    for text, font in parts:
        top = font.getbbox(text)[1]
        y = (TOP - h) / 2 - top
        draw_shadowed(img, (x, y), text, font, colour)
        x += font.getlength(text)
    # bottom band + hook line: the same full width as the heading (Giulia, 10 Nov: in line with the top text,
    # as large as possible without spilling over), so it reads on from it: "Disney Quiz #10 / Only REAL fans would know"
    band(img, (0, BOTTOM, W, H), STYLES["blue"])
    f = fit_line(line, SANS, W - 2 * MARGIN, (H - BOTTOM) * 0.86)
    box = f.getbbox(line)
    lw = f.getlength(line)
    draw_shadowed(img, ((W - lw) / 2, BOTTOM + (H - BOTTOM - (box[3] - box[1])) / 2 - box[1]), line, f,
                  (255, 255, 255))
    return img.convert("RGB")


def save(img, path):
    for q in (95, 92, 88, 84, 80, 75):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if buf.tell() <= MAX_BYTES:
            break
    Path(path).write_bytes(buf.getvalue())
    return q, buf.tell()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiz", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tiles", help="folder of tile images (default: download from gifs_selected.json)")
    args = ap.parse_args()
    qdir, out = Path(args.quiz), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    quiz = json.loads((qdir / "quiz.json").read_text())
    cfg = json.loads((ROOT / "config/youtube.json").read_text())
    test = {**{"a": {"band": "red"}, "b": {"band": "blue"}}, **cfg.get("thumbnail_test", {})}
    tiles = load_tiles(args, qdir)
    if len(tiles) < 6:
        raise SystemExit(f"Only {len(tiles)} pictures for the thumbnail tiles")
    line = tagline(quiz)
    for v in ("a", "b"):
        spec = test[v]
        img = render(quiz, tiles, spec.get("band", "red"), spec.get("tagline") or line)
        q, n = save(img, out / f"thumbnail-{v}.jpg")
        print(f"thumbnail-{v}.jpg: {W}x{H}, JPEG quality {q}, {n / 1e6:.2f} MB, band {spec.get('band')}")


if __name__ == "__main__":
    main()
