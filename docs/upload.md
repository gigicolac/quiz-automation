# YouTube upload (GitHub Actions)

The **Upload to YouTube** workflow (`.github/workflows/upload.yml`, `scripts/upload_youtube.py`) is run by hand from the Actions tab. It isn't scheduled yet.

## What it does

1. Checks that `quizzes/<quiz>/quiz.json` records the final video as approved, and takes the approved build's `release_tag`.
2. Downloads that build's video, captions and `build_report.json` from the draft release.
3. Builds the video details:
   - **Title:** from `quiz.json`.
   - **Description:** from `config/youtube.json`, with chapters taken from the real timings (`0:00 Intro`, `0:18 Question 1`, … `14:49 Thanks for playing`).
   - **Tags.**
   - **Schedule check:** the build is blocked unless the description says "Thursday 3PM & Sunday 1PM ET", and blocked if it mentions AEST.
4. Picks the publish time:
   - `next` (default): the next free slot (Thursday 3pm or Sunday 1pm US Eastern) at least 3 days ahead, skipping slots already used in other `upload.json` files.
   - An exact US Eastern time, for example `2026-11-12T15:00`.
   - Blank: private with no schedule.
5. **mode = preview** (default) stops here and shows everything in the run summary. Nothing is sent to YouTube.
6. **mode = upload** uploads the video privately with `publishAt` and these settings:
   - category Education
   - language English (Australia)
   - made for kids: no
   - altered or synthetic content: yes
   - paid promotion: no
   - standard licence, embedding on, notify subscribers on

   It then:
   - uploads the English captions
   - sets the thumbnail, if `quizzes/<quiz>/thumbnail.png` exists
   - adds the video to its series playlist, for example "General Knowledge Quizzes". A playlist whose title already mentions the series is reused; otherwise a public one is created (mapping in `config/youtube.json`)
   - posts the score comment (pin it in Studio)
   - records everything in `quizzes/<quiz>/upload.json`

## Studio checklist (the YouTube API can't do these)

The upload's run summary and `upload.json` list these under `studio_tasks`. They're done in YouTube Studio by Giulia or as a Claude browser task on her computer:

- **End screen:** import the existing end screen from the previous quiz (two elements). Left = **Video: Most recent upload**. Right = **Playlist: the series playlist**, for example General Knowledge Quizzes.
- **A/B test (Test & Compare):**
  - titles: three variants are generated from `title_variants`
  - thumbnails: once 2–3 thumbnail variants exist
- **Pin** the score comment.

## Safety

- **Once per quiz:** if `upload.json` already holds a video ID, the upload is refused. If a run fails part-way, `upload.json` shows `status: uploading`. Check YouTube Studio before trying again.
- **What the record shows:** it keeps the file transfer and YouTube's processing status separately. An upload response alone doesn't prove the video is fine, so check Studio.

## Needs (one-time)

- `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN` secrets. See `docs/sign-in.md`.
- **The API audit:** YouTube locks videos uploaded through an unaudited API project as private, so `publishAt` won't make them public. Check Studio after the first upload. If the video shows as locked or restricted, apply for the YouTube API audit for the Google Cloud project.

## Not yet included

- **Thumbnails:** made in Canva from the template (A = red band, B = blue band), exported, and listed in `quizzes/<quiz>/thumbnails.json`. Committing that file runs **Attach thumbnails**, which adds them to the approved release. The upload sets thumbnail A; B is for the Test & Compare A/B test in Studio.
- **Shorts:** not uploaded yet.
- **Other Studio-only settings** stay manual or a browser task: caption certification and location.
