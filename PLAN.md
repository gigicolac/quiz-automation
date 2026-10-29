# Just One More Quiz — automation plan

Agreed 28 Oct 2026. This is the source of truth for what the pipeline does, what it doesn't do yet, and the build order.

## Goal

A free (no monthly charges) pipeline that produces quiz videos and Shorts every week, lets us review them in Claude, and uploads approved ones with scheduled publishing well ahead of release.

## Cadence

| Item | Rate |
|---|---|
| Long quizzes produced | 3 a week |
| Long quizzes published | **Pending** — days, times and cadence were set in a separate chat that couldn't be read from here. Placeholder: Thursday 3pm and Sunday 1pm US Eastern |
| Buffer growth | Production minus publishing rate, into the upload pool |
| Shorts | 2–3 cut from each approved quiz, published 1 a day or every second day (agreed 29 Oct) |
| Upload lead time | Uploaded privately at least 5 days before publish *(assumption)* |

All times live in one file, `data/publish_schedule.json` (US Eastern, same format as the rain repo), so a change is one edit.

## Pipeline

### 1. Writing — Claude scheduled task, weekly

- Picks 3 topics (adjusted over time from analytics)
- Writes 50 questions per quiz in Giulia's style: one plain sentence per question, punchy reveal with one emoji and a quip or myth-bust, capitals for emphasis, warm sign-off, Australian spelling, no AI tells
- Fact-checks every answer in a second pass; uncertain questions are flagged for review
- Checks every question against `data/question_bank.json` so nothing repeats
- Writes title, description (existing caption template wording kept), tags, playlist and pinned-comment text
- Marks time-sensitive quizzes (e.g. Christmas, World Cup) with an expiry date
- Commits each quiz as `quizzes/<id>/quiz.json` and triggers the build

### 2. Building — GitHub Actions

- **GIFs:** GIPHY API, Pixabay as fallback. Avoid film/TV clips where possible (Content ID risk)
- **Voiceover:** Giulia's voice cloned with Chatterbox (CPU on free runners — speed and quality to be tested first)
- **Video:** assembled in code (FFmpeg/Python) from premade assets exported once from Canva: intro, break, outro, question slide and reveal slide backgrounds. Text, GIFs, timer and music are layered on top
- **Captions:** `.srt` generated from the script
- **Thumbnail:** Canva template via the Canva connector; fallback is template image + text in code
- **Shorts:** 2–3 vertical clips per quiz ("Can you get this one?")
- **Output:** video, Shorts, thumbnail and metadata attached to a GitHub Release per quiz (also used for previews)

### 3. Review — page in Claude

Each quiz shows the preview (played from its GitHub Release), title, thumbnail and any fact-check flags, with four options:

| Decision | Result |
|---|---|
| Approve | Upload pool |
| Pass | Spare pool — used only when the upload pool is empty. Expired items are skipped |
| Revise | Sent back to Claude with notes and rebuilt, then returns to review |
| Reject | Never used. Questions released back to the bank |

Decisions are stored on the review page; a Claude scheduled task syncs them to `data/pools.json` in the repo for the upload step to read.

### 4. Upload — GitHub Actions, scheduled

- Takes the next quiz from the upload pool (spare pool if empty)
- Uploads privately with `publishAt`, thumbnail, captions, playlist, category Education, made for kids No
- Posts the pinned-comment text as a comment
- Uploads that quiz's Shorts with their own publish times

## Assets (inventory, 29 Oct)

Video template: Canva `DAHLUf1evdk` "02062026_OMQ_General Knowledge Quiz #1", 1920×1080, 53 pages.

| Page(s) | Use | Pipeline |
|---|---|---|
| 1 | Intro: title on blurred gradient, "Quiz!" logo top right | Export background; title drawn in code |
| 2 | Rules: "There is no multiple-choice…" | Export as-is |
| Odd 3–51 | Question: GIF panel left, question card right, 00:10 timer | Blank background exported; GIF, text and countdown drawn in code |
| Even 4–52 | Reveal: same layout, green "Answer:" pill | Blank background exported; image, text and answer pill drawn in code |
| 53 | Outro: "One more quiz?…", logo, Subscribe button | Export as-is; leave space for end screen elements |

Thumbnail template: Canva `DAHNRSzzcbE` "JOMQ - Thumbnails 26", 1280×720. Layout: topic in large white text + "Quiz # N" script on dark blue band, GIF still collage, "Everyone should know" band. No autofill fields, so thumbnails are rebuilt in code from this layout (fonts and colours matched), with Canva editing as a later option.

Voice: 12.5 s ElevenLabs render of Giulia's voice (Quiz 8 Friends). Usable as the Chatterbox reference; a 20–30 s raw recording would clone more faithfully than cloning a clone.

Downloading Canva exports is blocked from Claude's workspace, so the exported files need to be downloaded once and added to `assets/`.

Observations from Quiz #1 template:
- 25 questions per video (not 50) — confirm the target count
- Some reveal slides show the previous question's text (e.g. Condensation under the monkeys question). Generating slides in code removes this class of error
- Footer copy mixes "daily" and "bi-weekly" dose of trivia — pick one

## Manual steps that remain (YouTube API limits)

- **End screens:** cannot be set via the API. One click per video in Studio ("Import from video"); batch them since uploads are days ahead
- **Pinning the comment:** the API can post but not pin
- **Approving videos** on the review page

## Blockers to clear first

1. **YouTube API audit.** Uploads from an unaudited API project are locked to private, so `publishAt` won't work. The rain repo already uploads publicly with `publishAt`, so check one of its scheduled videos in YouTube Studio: if it went public on time, reuse that Google Cloud project (new OAuth token for the quiz channel). If it shows "Private (locked)" or "restricted", apply for the audit. Also check the OAuth consent screen is "In production", not "Testing" (Testing tokens expire every 7 days)
2. **Chatterbox on free runners.** Test speed and voice quality on a 50-question script
3. **Canva thumbnails unattended.** Test whether the Canva connector works from a scheduled run
4. **Assets.** Export intro, break, outro, slide backgrounds, fonts, music and timer from Canva/current setup into `assets/`

## Build order

1. Repo skeleton, quiz JSON format, question bank
2. Assets exported into `assets/`
3. One test video end to end (writing → GIFs → voice → video → captions → thumbnail), reviewed manually
4. Upload step (private, then scheduled once audited)
5. Review page and pool sync
6. Shorts
7. Weekly scheduled task switched on

## Decisions log

- 28 Oct 2026: Video built in code rather than filled in Canva; Canva kept for thumbnails only
- 28 Oct 2026: 3 quizzes a week (buffer), previews via GitHub, Shorts added, Revise option added, fact-check pass added
- 29 Oct 2026: Shorts 1 a day or every second day. Canva templates inventoried; thumbnails rebuilt in code from the Canva layout
