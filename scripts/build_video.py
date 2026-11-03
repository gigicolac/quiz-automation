#!/usr/bin/env python3
"""Assemble a quiz video from Canva exports, a cloned voiceover, music and captions.

Inputs (all local files):
  --slides  one MP4 of the quiz design (question/answer pages alternating)
  --intro / --rules / --outro  one MP4 per intro-design page
  --private folder holding music.wav/.flac, hooray.m4a and voice_ref.wav
            (decrypted at run time; never committed in plain form)

Canva audio is dropped. All sound is added here: voiceover, background music
(quiet, ducked under the voice, 3 s fade in and out) and the hooray on the
ending slide.

Outputs in --out: <quiz>.mp4, <quiz>.srt, voiceover.json (the spoken script)
and build_report.json (timeline and warnings).
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000
ROOT = Path(__file__).resolve().parent.parent


def log(msg):
    print(msg, flush=True)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def ffmpeg(*args):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)])


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True).stdout
    return float(out.strip())


# ---------------------------------------------------------------- audio utils

def load_audio(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def save_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1",
                    "-i", "-", str(path)], input=pcm, check=True)


def rms_db(x):
    x = x[np.abs(x) > 1e-4] if np.any(np.abs(x) > 1e-4) else x
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def set_rms(x, target_db):
    return x * 10 ** ((target_db - rms_db(x)) / 20)


def trim_silence(x, thresh_db=-45, pad=0.05):
    mask = np.abs(x) > 10 ** (thresh_db / 20)
    if not mask.any():
        return x
    idx = np.nonzero(mask)[0]
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(x), idx[-1] + int(pad * SR))
    return x[a:b]


def loop_to(x, n, xfade):
    """Repeat x to length n with a crossfade at each join."""
    xf = int(xfade * SR)
    if len(x) >= n:
        return x[:n].copy()
    out = x.copy()
    ramp = np.linspace(0, 1, xf, dtype=np.float32)
    while len(out) < n:
        out[-xf:] = out[-xf:] * (1 - ramp) + x[:xf] * ramp
        out = np.concatenate([out, x[xf:]])
    return out[:n]


def envelope(active, attack, release, block):
    """One-pole smoothing of a 0/1 activity signal (per block) -> 0..1."""
    a_up = 1 - np.exp(-block / max(attack, 1e-3))
    a_dn = 1 - np.exp(-block / max(release, 1e-3))
    env = np.zeros(len(active), dtype=np.float32)
    v = 0.0
    for i, t in enumerate(active):
        v += (t - v) * (a_up if t > v else a_dn)
        env[i] = v
    return env


# ---------------------------------------------------------------- script

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍⬀-⯿]")


def clean(text):
    text = EMOJI.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def build_script(quiz, cfg):
    s = cfg["script"]
    qs = quiz["questions"]
    lines = [{"id": "intro", "kind": "intro", "text": s["intro"].format(
        series=quiz.get("series", ""), number=quiz["number"], count=len(qs))},
        {"id": "rules", "kind": "rules", "text": s["rules"]}]
    for q in qs:
        n = q["n"]
        answer = clean(q["answer"]).rstrip("!. ")
        lines.append({"id": f"q{n:02d}", "kind": "question", "n": n,
                      "text": s["question"].format(n=n, question=clean(q["question"]))})
        lines.append({"id": f"a{n:02d}", "kind": "answer", "n": n,
                      "text": clean(s["answer"].format(answer=answer, reveal=clean(q.get("reveal", ""))))})
    lines.append({"id": "outro", "kind": "outro", "text": s["outro"]})
    return lines


# ---------------------------------------------------------------- voiceover

class DummyTTS:
    """Tone placeholder for testing the pipeline without the voice model."""
    name = "dummy"

    def generate(self, text, out):
        dur = 0.4 + 0.055 * len(text)
        t = np.arange(int(dur * SR)) / SR
        save_wav(out, 0.2 * np.sin(2 * np.pi * 220 * t).astype(np.float32))


class ChatterboxVoice:
    name = "chatterbox"

    def __init__(self, ref, vcfg):
        import torch  # noqa: F401
        from chatterbox.tts import ChatterboxTTS
        log("Loading Chatterbox (CPU)…")
        self.model = ChatterboxTTS.from_pretrained(device="cpu")
        self.ref = str(ref)
        self.vcfg = vcfg

    def generate(self, text, out):
        import torchaudio
        wav = self.model.generate(text, audio_prompt_path=self.ref,
                                  exaggeration=self.vcfg["exaggeration"],
                                  cfg_weight=self.vcfg["cfg_weight"])
        torchaudio.save(str(out), wav, self.model.sr)


def make_voiceover(lines, tts, cache, ref, vcfg):
    cache.mkdir(parents=True, exist_ok=True)
    ref_hash = hashlib.sha1(Path(ref).read_bytes()).hexdigest()[:10] if ref and Path(ref).exists() else "none"
    clips = {}
    for i, line in enumerate(lines):
        key = hashlib.sha1(json.dumps([tts.name, ref_hash, vcfg.get("exaggeration"),
                                       vcfg.get("cfg_weight"), line["text"]]).encode()).hexdigest()[:16]
        path = cache / f"{line['id']}-{key}.wav"
        if not path.exists():
            log(f"  voice {i + 1}/{len(lines)} {line['id']}: {line['text'][:60]}")
            tmp = path.with_suffix(".tmp.wav")
            tts.generate(line["text"], tmp)
            tmp.rename(path)
        audio = set_rms(trim_silence(load_audio(path)), vcfg["target_rms_db"])
        clips[line["id"]] = audio
    return clips


# ---------------------------------------------------------------- slides

PEACH = np.array([255, 231, 194])


def classify_slides(path, fps):
    """Label each frame Q (timer box) or A (answer pill) from the strip under the cards."""
    w, h = 37, 9
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
         f"fps={fps},crop=370:90:760:900,scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    labels = []
    size = w * h * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        px = np.frombuffer(buf, np.uint8).reshape(-1, 3).astype(int)
        peach = (np.abs(px - PEACH) < [40, 40, 45]).all(axis=1).mean()
        labels.append("A" if peach > 0.3 else "Q")
    proc.wait()
    return labels


def find_pages(labels, fps, expected, min_run=0.4, window=5):
    # majority vote over a short window smooths transition flicker
    b = np.array([lab == "A" for lab in labels], dtype=float)
    pad = window // 2
    sm = np.convolve(np.pad(b, pad, mode="edge"), np.ones(window) / window, mode="valid")
    labels = ["A" if v > 0.5 else "Q" for v in sm]
    runs = []
    for i, lab in enumerate(labels):
        if runs and runs[-1][0] == lab:
            runs[-1][2] = i + 1
        else:
            runs.append([lab, i, i + 1])
    # absorb flickers (transitions) into the previous run
    merged = []
    for lab, a, b in runs:
        if merged and (b - a) / fps < min_run:
            merged[-1][2] = b
        elif merged and merged[-1][0] == lab:
            merged[-1][2] = b
        else:
            merged.append([lab, a, b])
    pages = [(lab, a / fps, b / fps) for lab, a, b in merged]
    seq = "".join(p[0] for p in pages)
    if len(pages) != expected or seq != "QA" * (expected // 2):
        raise SystemExit(f"Slide detection found {len(pages)} pages ({seq[:40]}…), expected {expected}. "
                         "Check the slides export.")
    return pages


def render(src, start, length, out, target, cfg, mode):
    """Encode src[start:start+length] at the house format, extended to `target` seconds.

    mode 'loop' repeats the clip (answer GIFs), 'hold' freezes the last frame."""
    vf = f"fps={cfg['fps']},scale={cfg['width']}:{cfg['height']},setsar=1,format=yuv420p"
    enc = ["-an", "-c:v", "libx264", "-preset", cfg["preset"], "-crf", cfg["crf"]]
    extra = target - length
    if extra <= 0.02:
        ffmpeg("-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", src, "-vf", vf, *enc, out)
    elif mode == "hold":
        ffmpeg("-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", src,
               "-vf", f"{vf},tpad=stop_mode=clone:stop_duration={extra:.3f}", *enc, out)
    else:
        tmp = out.with_suffix(".base.mp4")
        ffmpeg("-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", src, "-vf", vf, *enc, tmp)
        ffmpeg("-stream_loop", "-1", "-i", tmp, "-t", f"{target:.3f}", "-vf", vf, *enc, out)
        tmp.unlink()


# ---------------------------------------------------------------- captions

def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def caption_chunks(text, max_chars=84):
    words, chunks, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def wrap2(chunk, width=42):
    if len(chunk) <= width:
        return chunk
    words, top = chunk.split(), ""
    while words and len(top) + len(words[0]) + 1 <= max(width, len(chunk) // 2 + 1):
        top = f"{top} {words.pop(0)}".strip()
    return top + "\n" + " ".join(words)


def write_srt(cues, path):
    out, i = [], 1
    for start, dur, text in cues:
        chunks = caption_chunks(text)
        total = sum(len(c) for c in chunks)
        t = start
        for c in chunks:
            d = dur * len(c) / total
            out.append(f"{i}\n{srt_time(t)} --> {srt_time(t + d)}\n{wrap2(c)}\n")
            i += 1
            t += d
    path.write_text("\n".join(out), encoding="utf-8")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiz", required=True, help="quiz folder, e.g. quizzes/quiz-09")
    ap.add_argument("--slides", required=True)
    ap.add_argument("--intro", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--outro", required=True)
    ap.add_argument("--private", required=True, help="folder with music.(wav|flac), hooray.m4a, voice_ref.wav")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tts", choices=["chatterbox", "dummy"], default="chatterbox")
    ap.add_argument("--cache", default=".cache/voice")
    ap.add_argument("--config", default=str(ROOT / "config" / "video.json"))
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    vcfg, mcfg, pcfg = cfg["voice"], cfg["music"], cfg["pages"]
    quiz_dir = Path(args.quiz)
    quiz = json.loads((quiz_dir / "quiz.json").read_text())
    out = Path(args.out)
    work = out / "work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    private = Path(args.private)
    warnings = []

    # 1. script and voiceover
    lines = build_script(quiz, cfg)
    (out / "voiceover.json").write_text(json.dumps(lines, indent=2, ensure_ascii=False))
    log(f"Script: {len(lines)} lines")
    ref = private / "voice_ref.wav"
    tts = DummyTTS() if args.tts == "dummy" else ChatterboxVoice(ref, vcfg)
    vo = make_voiceover(lines, tts, Path(args.cache), ref, vcfg)
    vlen = {k: len(v) / SR for k, v in vo.items()}

    # 2. find question/answer pages in the slides export
    n_q = len(quiz["questions"])
    detect_fps = 30
    pages = find_pages(classify_slides(args.slides, detect_fps), detect_fps, 2 * n_q)
    log(f"Slides: {len(pages)} pages found")

    # 3. render segments: (file, voice cues [(line_id, offset)], extras)
    segs = []

    def add(src, start, length, target, mode, cues, name, extra=None):
        path = work / f"{len(segs):03d}-{name}.mp4"
        render(src, start, length, path, target, cfg, mode)
        segs.append({"file": path, "cues": cues, "name": name, "extra": extra or []})

    d = duration(args.intro)
    add(args.intro, 0, d, max(d, pcfg["intro_min"], 0.5 + vlen["intro"] + 0.8), "hold",
        [("intro", 0.5)], "intro")
    d = duration(args.rules)
    add(args.rules, 0, d, max(d, pcfg["rules_min"], 0.3 + vlen["rules"] + 1.0), "hold",
        [("rules", 0.3)], "rules")
    for i in range(n_q):
        n = i + 1
        (_, qs, qe), (_, as_, ae) = pages[2 * i], pages[2 * i + 1]
        qid, aid = f"q{n:02d}", f"a{n:02d}"
        q_need = vcfg["question_start"] + vlen[qid] + 0.3
        if q_need > qe - qs:
            warnings.append(f"Q{n}: question voice ({vlen[qid]:.1f} s) runs past the timer; slide held")
        add(args.slides, qs, qe - qs, max(qe - qs, q_need), "hold", [(qid, vcfg["question_start"])], qid)
        a_need = vcfg["answer_start"] + vlen[aid] + vcfg["answer_tail"]
        add(args.slides, as_, ae - as_, max(ae - as_, a_need), "loop", [(aid, vcfg["answer_start"])], aid)
    d = duration(args.outro)
    o_need = pcfg["outro_voice_start"] + vlen["outro"] + pcfg["outro_tail"]
    add(args.outro, 0, d, max(d, o_need), "hold", [("outro", pcfg["outro_voice_start"])], "outro",
        extra=[("hooray", cfg["hooray"]["start"])])

    # 4. join video and lay out the timeline from real encoded durations
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{s['file'].resolve()}'\n" for s in segs))
    video = work / "video.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", video)
    t = 0.0
    for s in segs:
        s["start"] = t
        s["dur"] = duration(s["file"])
        t += s["dur"]
    total = duration(video)
    n = int(total * SR) + SR

    # 5. audio: voice, hooray, music bed
    voice = np.zeros(n, np.float32)
    cues = []
    for s in segs:
        for lid, off in s["cues"]:
            a = int((s["start"] + off) * SR)
            clip = vo[lid][: n - a]
            voice[a:a + len(clip)] += clip
            cues.append((s["start"] + off, len(clip) / SR, next(l["text"] for l in lines if l["id"] == lid)))
    fx = np.zeros(n, np.float32)
    hooray = set_rms(trim_silence(load_audio(private / "hooray.m4a")), cfg["hooray"]["rms_db"])
    for s in segs:
        for _, off in s["extra"]:
            a = int((s["start"] + off) * SR)
            clip = hooray[: n - a]
            fx[a:a + len(clip)] += clip

    music = load_audio(next(private.glob("music.*")))
    music = set_rms(music, mcfg["rms_db"])
    bed = loop_to(music, n, mcfg["loop_crossfade"])
    block = int(0.01 * SR)
    nb = n // block
    act = (np.abs(voice[: nb * block]).reshape(nb, block).max(axis=1) > 0.01).astype(np.float32)
    env = envelope(act, mcfg["duck_attack"], mcfg["duck_release"], 0.01)
    gain = 10 ** (mcfg["duck_db"] * np.repeat(env, block) / 20)
    bed[: nb * block] *= gain
    end = int(total * SR)
    fi, fo = int(mcfg["fade_in"] * SR), int(mcfg["fade_out"] * SR)
    bed[:fi] *= np.linspace(0, 1, fi)
    bed[end - fo:end] *= np.linspace(1, 0, fo)
    bed[end:] = 0

    mix = (voice + fx + bed)[:end]
    peak = np.abs(mix).max()
    if peak > 0.97:
        mix *= 0.97 / peak
    audio = work / "mix.wav"
    save_wav(audio, mix)

    # 6. mux and captions
    slug = quiz["id"]
    final = out / f"{slug}.mp4"
    ffmpeg("-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final)
    write_srt(cues, out / f"{slug}.srt")

    report = {
        "quiz": slug, "tts": tts.name, "duration_s": round(total, 2),
        "segments": [{"name": s["name"], "start": round(s["start"], 2), "dur": round(s["dur"], 2)} for s in segs],
        "slide_pages": [{"kind": k, "start": round(a, 2), "end": round(b, 2)} for k, a, b in pages],
        "levels_db": {"voice_rms": round(float(rms_db(voice[:end])), 1),
                      "music_rms": round(float(rms_db(bed[:end])), 1),
                      "mix_peak": round(float(20 * np.log10(np.abs(mix).max() + 1e-12)), 1)},
        "warnings": warnings,
    }
    (out / "build_report.json").write_text(json.dumps(report, indent=2))
    shutil.rmtree(work)
    log(f"Done: {final} ({total / 60:.1f} min), {len(warnings)} warning(s)")
    for w in warnings:
        log(f"  ! {w}")


if __name__ == "__main__":
    sys.exit(main())
