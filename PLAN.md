# Just One More Quiz — automation plan

Agreed 28 Oct 2026. This is the source of truth for what the pipeline does, what it doesn't do yet, and the build order.

## Goal

A free (no monthly charges) pipeline that produces quiz videos and Shorts every week, lets us review them in Claude, and uploads approved ones with scheduled publishing well ahead of release.

## Cadence

| Item | Rate |
|---|---|
| Long quizzes produced | 3 a week |
| Long quizzes published | 2 a week: Thursday 3pm and Sunday 1pm US Eastern (Fri 7am / Mon 5am Melbourne) |
| Buffer growth | Production minus publishing rate, into the upload pool |
| Shorts | 2–3 cut from each approved quiz, published 1 a day or every second day (agreed 29 Oct) |
| Upload lead time | Uploaded privately 3 days before publish (Monday for Thursday, Thursday for Sunday), then a processing check *(assumption: "well after upload"; earlier chat used ~30 hours)* |

All times live in one file, `data/publish_schedule.json` (US Eastern, same format as the rain repo), so a change is one edit.

## Pipeline

### 1. Writing — Claude scheduled task, weekly

- Picks 3 topics (adjusted over time from analytics)
- Writes 50 questions per quiz (may rise to 100 later; 25 in past videos) in Giulia's style: one plain sentence per question, punchy reveal with one emoji and a quip or myth-bust, capitals for emphasis, warm sign-off, Australian spelling, no AI tells. Full rules, including the AI-tell list the lint enforces: [`docs/STYLE_GUIDE.md`](docs/STYLE_GUIDE.md)
- Fact-checks every answer in a second pass. Each answer records **at least two independent sources** in `quiz.json`; contested answers are rewritten or dropped, and uncertain questions are flagged for review
- Checks every question against `data/question_bank.json` so nothing repeats: exact matches, near-matches (fuzzy wording), and the same answer under a similar question
- Writes title, description (existing caption template wording kept), tags, playlist and pinned-comment text
- Marks time-sensitive quizzes (e.g. Christmas, World Cup) with an expiry date
- Commits each quiz as `quizzes/<id>/quiz.json` and triggers the build

### 2. Building — Canva for the slides, GitHub for the rest

Canva builds what you see; code handles timing and sound. This keeps every slide editable by hand in Canva.

1. **Copy the template** (Claude, Canva connector): copy "Quiz Template - Asset Export" for each quiz. The master is never edited.
2. **Fill the slides:** question text, answer text and quiz number written into each page; tagline "Your bi-weekly dose of trivia".
3. **Place the GIFs:** found on GIPHY (Pixabay as fallback), uploaded to Canva by URL and placed, sized and cropped into each question and reveal frame.
4. **Export:** the filled design is exported from Canva as MP4 (one clip per page) and pulled into GitHub by the **Fetch asset** workflow.
5. **Assemble (GitHub Actions):** each page clip is looped or trimmed to the voiceover length. The 10-second countdown, music and captions are added, and the clips are joined into the full video.
6. **Voiceover:** Giulia's voice cloned with Chatterbox (CPU on free runners, speed and quality tested first).
7. **Thumbnail:** "JOMQ - Thumbnails 26" layout, duplicated and filled in Canva the same way, exported as PNG.
8. **Shorts:** 2–3 vertical clips cut from each quiz ("Can you get this one?").
9. **Output:** video, Shorts, thumbnail and metadata attached to a GitHub Release per quiz, used for previews.

Risks to test on the first quiz: about 100 Canva page edits per quiz through the connector (speed and Claude usage), and whether Canva's MP4 export keeps GIFs animated at the right length.

### 3. Review — two stages until we're happy, then video only

- **Stage 1, questions:** each quiz's 50 questions, answers and reveals are sent to Giulia in Claude before anything is built. Approved quizzes go to the build.
- **Stage 2, finished video:** every video is reviewed before upload while the pipeline is being proven. Once Giulia is happy, stage 1 is dropped and only stage 2 remains.


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

## Upload settings (from the 28 Oct settings chat)

| Setting | Value | How |
|---|---|---|
| Title, description, tags, chapters | Generated; caption template wording kept as is | Automatic |
| Schedule line in description | Must read Thursday 3PM & Sunday 1PM ET. Upload is blocked if it still says AEST | Automatic check |
| Category | Education | Automatic |
| Made for kids | Always No | Automatic |
| Language | English (Australia) | Automatic |
| Recording date | Upload date | Automatic |
| Paid promotion | No (`hasPaidProductPlacement: false`) | Automatic |
| Altered/synthetic content | Yes (`containsSyntheticMedia: true`, cloned voice) | Automatic |
| Licence, embedding, notify subscribers | Standard YouTube licence, embedding on, notify on | Automatic |
| Visibility | Private with `publishAt` | Automatic |
| Playlist | Created and assigned by Claude (none exist yet) | Automatic |
| Thumbnail, captions | Generated | Automatic |
| End screen | Studio template, end-screen target named in the outro voiceover | Browser task on Giulia's computer |
| Pinned comment | Posted by the pipeline, pinned by the browser task | Browser task |
| Caption certification, location (Melbourne), Shorts remixing on | Studio-only fields | Browser task |

Browser task: runs the day after upload with Giulia's computer on and the Claude desktop app open, checks every setting and alerts if one is wrong.

## On-screen wording

- Tagline everywhere: "Your bi-weekly dose of trivia" (fixes slides that said "daily")
- Credit: "created by Giulia Colaci & Lucas Shugg"
- Slides are generated from the quiz file, so each reveal always shows its own question

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

Voice: 12.5 s ElevenLabs render of Giulia's voice (Quiz 8 Friends) — agreed as the Chatterbox reference. Stored privately, never committed while the repo is public.

Also available: Giulia's **original 3 min 13 s recording** (sent 28 Oct; mono, 48 kHz, −22.2 LUFS integrated, peak −1.4 dBFS). Audition reference clips cut from it alongside the 12.5 s render. The original is the safer source: ElevenLabs' terms prohibit using its output as training data for competing AI models, and the original is more natural. **Storage:** where the voice file lives for hosted runs (private repo or Google Drive) is to be agreed by Giulia and Shoma (29 Oct). Until then it stays out of this public repo.

In repo: `assets/video/intro.mp4` (16.9 s), `rules.mp4` (13.4 s), `outro.mp4` (11.7 s), and stills of pages 1–4 in `assets/canva/`. Canva exports are pulled in with the **Fetch asset** workflow (Claude exports, GitHub downloads). Still needed: blank question and reveal backgrounds (no text, GIF or timer).

Observations from Quiz #1 template:
- 25 questions per video; new videos use 50 (decided 29 Oct)
- Some reveal slides show the previous question's text (e.g. Condensation under the monkeys question). Generated slides remove this
- Footer copy said "daily"; now "bi-weekly" (decided 29 Oct)

## Manual steps that remain (YouTube API limits)

- **End screens:** cannot be set via the API. Handled by the browser task (above). If that fails, the fallback is one click per video in Studio ("Import from video"), batched since uploads are days ahead
- **Pinning the comment:** the API can post but not pin, so it's handled by the browser task. Fallback: pin by hand after release
- **Approving videos** on the review page

## Known risks accepted

- **GIFs from GIPHY (28 Oct):** GIPHY's API terms say not to "cache or store copies of GIPHY's media assets", and GIPHY's user terms bar commercial use. TV and film GIFs belong to the studios whatever the source. Giulia accepted this for now. **Switch to licensed media (Pixabay or similar) before applying to the YouTube Partner Program.** Every GIF records its GIPHY ID so a claim can be traced and swapped. If the GIPHY key is limited or revoked, Pixabay is the automatic fallback
- **Public repo (29 Oct):** this repo stays public for unlimited free Actions minutes. That makes quiz files and anything attached to GitHub Releases (preview videos, Shorts, thumbnails) visible to anyone **before** release. Accepted by Giulia. Keep answers out of workflow logs and keep preview retention short. The voice recording stays out of this repo (see Assets)

## Blockers to clear first

1. **YouTube API audit.** Uploads from an unaudited API project are locked to private, so `publishAt` won't work. The rain repo already uploads publicly with `publishAt`, so check one of its scheduled videos in YouTube Studio: if it went public on time, reuse that Google Cloud project (new OAuth token for the quiz channel). If it shows "Private (locked)" or "restricted", apply for the audit. Also check the OAuth consent screen is "In production", not "Testing" (Testing tokens expire every 7 days)
   - **Update 29 Oct:** the OAuth consent screen is now **In production** (confirmed by Giulia's screenshot: External, 3 of 100 user cap). The rain repo's records show a **public** 3-hour upload completing from this project on 2 Oct ([run 36974548325](https://github.com/gigicolac/rain-sounds-automation/actions/runs/36974548325)), which suggests no audit lock. Still worth confirming one scheduled rain video went public on time. The rain channel's refresh token was issued during Testing, so reissue it once. Make sure the `youtube.force-ssl` scope is added under Data Access (needed for captions, comments and playlists)
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
- 29 Oct 2026: Slides built in Canva (copy of the master template per quiz) and exported; voice, timer, music and captions added in GitHub. Two-stage review (questions, then video) until the pipeline is trusted. Upload 3 days ahead confirmed.
- 29 Oct 2026: 50 questions; "bi-weekly" tagline; cloned ElevenLabs clip used as voice reference; settings table adopted from the 28 Oct settings chat; Notion Quiz Queue approval replaced by the video review page.
- 29 Oct 2026: Shorts 1 a day or every second day. Canva templates inventoried; thumbnails rebuilt in code from the Canva layout
- 29 Oct 2026: OAuth consent screen moved to Production. Repo stays public (free Actions minutes), with the risks above accepted. Voice file storage to be agreed with Shoma. Style guide added as `docs/STYLE_GUIDE.md` (dashes, groups of three and inflated vocabulary banned in scripts; caption template exempt). Two sources per answer. GIPHY risk and the switch-before-monetisation rule recorded
