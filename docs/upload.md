# YouTube upload (GitHub Actions)

**Release pattern (same as the rain-sounds pipeline, 6 Nov 2026):**
1. Upload **private with no publishAt** and record `upload_completed_at`.
2. Add the captions, thumbnail A and the series playlist.
3. Wait for YouTube processing (up to 45 minutes).
4. Then set `publishAt` to the intended slot, but never sooner than **24 hours** after the transfer finished (`minimum_lead_minutes`).
5. Confirm the schedule with YouTube.

- **Resume:** a failed run leaves the video private, and re-running resumes the recorded video ID without uploading again.
- **Channel check:** the upload refuses to run unless the signed-in channel name contains "One More Quiz", or the ID matches `expected_channel_id` once that's set.
- **Score comment:** posted by **Post score comment** (`comment.yml`) 15 minutes after each Thursday 3pm and Sunday 1pm ET release, plus a daily 5:45pm ET catch-up. It only posts once the video is public and never posts twice. Pinning has no API, so the run summary gives an "Open and pin" link.

The **Upload to YouTube** workflow (`.github/workflows/upload.yml`, `scripts/upload_youtube.py`):

- **Runs daily at 8am Sydney.** It uploads the first quiz whose final video is approved and has no upload yet, or resumes an unfinished upload that has a video ID, into the next free slot (`next`). One quiz per run. Uploads run in GitHub's cloud and don't need anyone's computer.
- **Off switch:** set the repository variable `AUTO_UPLOAD` to `false`.
- **By hand:** it can also be run from the Actions tab (preview or upload).
- **Studio steps:** a daily Claude scheduled task at 10:13am Sydney does them in the Claude desktop app's built-in browser on Giulia's computer. Giulia and her partner have a computer on between 10am and 8pm Sydney, so that's when this runs. It does the Studio checklist below for new uploads and pins the score comment on released videos. Releases are Friday 7am and Monday 5am Sydney, so the pin lands the same morning.

## What it does

1. Checks that `quizzes/<quiz>/quiz.json` records the final video as approved, and takes the approved build's `release_tag`.
2. Downloads that build's video, captions and `build_report.json` from the draft release.
3. Builds the video details:
   - **Title:** from `quiz.json`.
   - **Description:** from `config/youtube.json`, with chapters taken from the real timings (`0:00 Intro`, `0:18 Question 1`, … `14:49 Thanks for playing`).
   - **Tags.**
   - **Description:** Giulia's house style: a series hook line, "🎯 How It Works", the @JustOneMoreQuiz link, like/comment/subscribe ("here for you every Thursday, Saturday & Sunday"), then chapters. Hook lines per series are in `config/youtube.json` (`description_hooks`); `quiz.json` can set its own `description_hook`.
   - **Tags:** series keywords first (`series_tags`, from vidIQ keyword research), then shared quiz tags (`tags`, including searches like "good weekend quiz"), trimmed to YouTube's 500-character limit. `quiz.json` can add its own `tags`.
   - **Schedule check:** blocked unless the description says "every Thursday, Saturday & Sunday", and blocked if it mentions AEST.
4. Picks the publish time:
   - `next` (default): the next free slot (Thursday 3pm, Saturday 1pm or Sunday 1pm US Eastern) at least 1 day ahead (and never less than 24 hours after the upload finishes), skipping slots already used in other `upload.json` files.
   - An exact US Eastern time, for example `2026-11-12T15:00`.
   - Blank: private with no schedule.
5. **mode = preview** (default) stops here and shows everything in the run summary. Nothing is sent to YouTube.
6. **mode = upload** uploads the video privately (no `publishAt` until processing finishes) with these settings:
   - category Education
   - language English (Australia)
   - made for kids: no
   - altered or synthetic content: **no** (Giulia's instruction, 6 Nov 2026)
   - paid promotion: no
   - standard licence, embedding on, notify subscribers on

   It then:
   - uploads the English captions
   - sets the thumbnail, if `quizzes/<quiz>/thumbnail.png` exists
   - adds the video to its series playlist, for example "General Knowledge Quizzes". A playlist whose title already mentions the series is reused; otherwise a public one is created (mapping in `config/youtube.json`)
   - records everything in `quizzes/<quiz>/upload.json`

## Studio checklist (the YouTube API can't do these)

The upload's run summary and `upload.json` list these under `studio_tasks`. They're done in YouTube Studio by Giulia or as a Claude browser task on her computer:

- **End screen:** import the existing end screen from the previous quiz (two elements). Left = **Video: Most recent upload**. Right = **Playlist: the series playlist**, for example General Knowledge Quizzes.
- **A/B test (Test & Compare), "Title and thumbnail":** the current title with thumbnail A against a research-based title (`title_variants`) with thumbnail B.
- **Category Education:** Type **Activity**, and **Problems** = the `problems` list in `upload.json` (one line per question: timecode, question).
- **Pin** the score comment, after release, once **Post score comment** has posted it.
- **Caption certification:** "This content has never aired on television in the U.S."
- **Shorts remixing:** allowed.

## Safety

- **Once per quiz:** if `upload.json` already holds a video ID, the upload is refused. To re-upload (for example a sharper 4K build), run with **replace**: the old copy is taken off the schedule first (left private, never deleted; delete it in Studio) and recorded under `replaced`. If a run fails part-way, `upload.json` shows `status: uploading`. Check YouTube Studio before trying again.
- **What the record shows:** it keeps the file transfer and YouTube's processing status separately. An upload response alone doesn't prove the video is fine, so check Studio.

## Needs (one-time)

- `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN` secrets. See `docs/sign-in.md`.
- **The API audit:** YouTube locks videos uploaded through an unaudited API project as private, so `publishAt` won't make them public. Check Studio after the first upload. If the video shows as locked or restricted, apply for the YouTube API audit for the Google Cloud project.

## Shorts

The **Shorts** workflow also runs daily at 9:30am Sydney, after the 8am upload. It picks the first approved quiz whose long video is scheduled and whose Shorts aren't all scheduled yet. It cuts 7-question Shorts from the final video, uploads them privately and schedules each to the next free 8am or 6pm US Eastern slot, at least 24 hours after its upload. A quiz whose Shorts are all scheduled is skipped, so Shorts posted by hand aren't redone. Repository variable `AUTO_UPLOAD=false` pauses this as well. The Studio task on Giulia's Mac does the Studio-only Shorts settings (location, paid promotion, related video, level, pinning).

**Countdown:** each Short shows a 5-second counter (Giulia, 13 Nov 2026; `think_seconds` in config/shorts.json). While the question is read the timer is held on 00:05, then the last 5 seconds of the slide's countdown play with the buzzer. Where the reading runs into those 5 seconds, the music is muted there so the voice isn't heard twice.

**Replacing Shorts not yet live:** run Shorts with `mode=replace` for a quiz. Every Short that hasn't gone live (more than 90 minutes before its slot) and wasn't made with the current countdown is re-made and uploaded again. The new upload takes the old one's slot. The old upload is kept private with its schedule removed (never deleted) and is listed under `"replaced"` in shorts-upload.json. Captions that YouTube refuses straight after an upload ("video not found") are retried.

## Not yet included

- **Thumbnails:** made in code by `scripts/make_thumbnails.py` at 2560x1440 (twice YouTube's size, so they stay sharp), at the end of each build and by the **Thumbnails** workflow (commit `quizzes/<quiz>/thumbnails-request.json`). The heading ("Disney Quiz #10") is fitted to the full width; the hook line comes from `thumbnail_taglines` and stays clear of the video-length badge. A and B change one thing only (`thumbnail_test` in config/youtube.json). They go on the build release and, as `<quiz>-thumbnail-a.jpg` / `-b.jpg`, on the public `thumbnails` release for the Studio task. Every quiz from #11 tests **title and thumbnail** together; results go in the weekly report.
- **Changing tags or thumbnail A after upload:** run **Upload** with mode `update`. It refreshes the tags (quiz.json `tags`, from vidIQ keyword research, then the series and channel tags) and thumbnail A; title, description, schedule and visibility are untouched.
- **Other Studio-only settings** stay manual or a browser task: caption certification and location.
