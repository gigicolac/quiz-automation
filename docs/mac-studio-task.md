# Mac scheduled task: Studio steps, Canva sign-in and the weekly report

The scheduled task "Quiz Studio steps on Giulia's Mac" runs at 10:13am Sydney on Tue, Fri, Sun and Mon. The cloud quiz tasks may also start it when the Canva sign-in needs renewing. Its prompt only says to follow this file, so changes are made here through a pull request rather than by editing the task. Giulia, 11 Nov 2026: "Can you make sure that i no longer need to approve anything ... I won't always be here."

Write in British English and keep the final report short. Channel: "One More Quiz!" (ID UCbP3HMh1h7XAWUruf_M8n7g). AGENTS.md applies: both standing authorisations, and the list of things that still need Giulia's OK.

## 1. Canva sign-in (every run, first)

Giulia authorised this on 10 Nov 2026 ("happy for you to 'use my mac' and do it yourself … You need to be fully autonomous").

1. In the cloud shell (Bash with gh, not device bash), list the latest Build video runs: `gh api "repos/gigicolac/quiz-automation/actions/workflows/build-video.yml/runs?per_page=5"`.
2. Renewal is needed if the most recent completed run failed and its log contains "Canva token refresh failed", and no Canva sign-in run (sign-in.yml) has succeeded since that failure.
3. If it is needed, follow docs/sign-in.md, "Renewing the Canva sign-in without Giulia (her Mac's browser)", exactly. It uses the built-in browser on this Mac, which is logged in to Canva.
   - Never type passwords. If Canva shows a login page, stop and say so under "Needs attention".
   - Never write the one-time code anywhere except the step 2 workflow input.
4. Then restart the failed build if no Build video run is in progress or queued: `gh workflow run build-video.yml --ref <its branch> -f quiz=<quiz> -f tts=chatterbox`.

## 2. Read first

From main (gh api or raw.githubusercontent.com):
- every `quizzes/*/upload.json` (long videos), `quizzes/*/shorts-upload.json` (Shorts) and `quizzes/*/quiz.json`
- docs/upload.md (Studio checklist), docs/hooks-playbook.md, config/youtube.json, config/shorts.json

In scope: records with a video_id whose status is "scheduled", or that are already public. Each long-video record has a "studio_tasks" list; treat it as the checklist for that video. It already has the right titles, playlist, level and A/B details.

## 3. Each long video (upload.json)

1. **End screen** (if missing)
   - "Import from video" and pick the previous quiz video. Two elements:
     - Left = Video: Most recent upload
     - Right = Playlist: the record's playlist
   - It runs over the last ~11 seconds (the ending slide).
2. **Details > Show more**
   - Video location = Melbourne, VIC.
   - Caption certification = "This content has never aired on television in the U.S."
   - Shorts remixing = Allow video and audio remixing.
   - Altered content = No.
   - Category Education, Type = Activity.
   - Problems = lines from the record's "problems", trimmed to 800 characters (whole lines, spread across the quiz).
   - Level = as the studio_tasks line says: the option closest to the quiz difficulty in quiz.json (fandom quizzes are hard).
   - Save.
3. **A/B Testing** (if no test yet)
   - quiz-10: leave it as it is. Giulia set a title-only test on purpose.
   - Every other quiz (quiz-11 onwards): "Title and thumbnail".
     - Row 1 = the current title and thumbnail A.
     - Row 2 = the second title from the record's studio_tasks and thumbnail B.
   - Thumbnail B: download `https://github.com/gigicolac/quiz-automation/releases/download/thumbnails/<quiz>-thumbnail-b.jpg` with curl in device bash into `~/Pictures/One More Quiz thumbnails/` (create the folder if needed), then upload it from there in Studio. If it isn't on that release, download `thumbnail-b.jpg` from the quiz's own release (`release_tag` in upload.json).
   - If thumbnail B truly can't be added, set a "Title only" test with the same two titles and say so under "Needs attention".
4. **Pin** (after release, once the record has comment_id): pin that comment (Studio > Comments, remove filters, ⋮ > Pin > Pin).

## 4. Each Short (shorts-upload.json): Giulia's standard settings

Giulia, 11 Nov 2026: "For every short ALWAYS…". These six are defaults for EVERY Short, every time, unless she says otherwise. Check every Short in scope on every run, and fix any that is missing one, not only new ones.

1. **Paid promotion:** "No, my video doesn't include paid promotion". The upload also sets it through the API (`paid_promotion` in the record); confirm the "No" button is selected in Studio.
2. **Tags:** the quiz's researched tags (vidIQ/Apify; quiz.json `tags`) are set by the upload through the API, so check they're there. If a Short has only generic tags, run `shorts.yml` with `mode=defaults` for that quiz (cloud shell, `gh workflow run shorts.yml --ref main -f quiz=<quiz> -f mode=defaults`). If the quiz has no `tags` in quiz.json, say so under "Needs attention".
3. **Video location:** Melbourne, VIC.
4. **Category Education:** Type = Activity, and Problems = the record's "problems" (the Short's questions, one per line, with their timecodes), trimmed to 800 characters. This is the same as for long videos.
5. **Level:** from the quiz difficulty in quiz.json: hard = Advanced, medium = Intermediate, easy = Beginner (config/shorts.json `studio.level_by_difficulty`; a missing difficulty counts as medium). Fandom quizzes are hard.
6. **Related video:** the full quiz (full_quiz_video_id in `quizzes/<quiz>/shorts.json`, or the quiz's upload.json video_id).

Also:

- **Playlist:** the Short must be in the series playlist (e.g. "General Knowledge Quizzes"); add it if missing.
- **Recording date:** the record's recording_date. If none, pick a date 2–7 days before the upload date, varied between Shorts.
- **Altered content:** No.
- **Shorts remixing:** allowed.
- **Save** after the changes, then reload once to confirm they stuck.
- **Pin** the score comment after release, once the record has comment_id.

## 5. Mondays only: weekly report (after the Studio steps)

Giulia asked on 10 Nov 2026 for a weekly report, emailed to her and Shoma.

1. **Gather in YouTube Studio** (built-in browser, read only). Cover the last 7 days and lifetime, for every quiz and Short released in the last 14 days:
   - views, impressions, impressions click-through rate, average view duration, average percentage viewed, subscribers gained
   - the audience retention curve: where viewers drop off, e.g. "40% left by question 5"
   - each A/B test's result (Studio > the video > A/B Testing): winner, watch-time share, status
   - comments that mention difficulty
2. **Read docs/weekly-report-notes.md** and cover every "Open" item.
3. **Check tags** for the coming week's topics with vidIQ keyword research (vidIQ connector, load with ToolSearch).
4. **Write the report**: short, with dot points. Make clear what is measured and what is a recommendation.
   - Headline numbers per video and Short.
   - Each A/B result (Quiz #10 = title-only test; Quiz #11 onwards = title and thumbnail), with what won and by how much.
   - Difficulty and retention, with a recommendation: keep or change (e.g. fandom quizzes hard vs medium).
   - **Thumbnail and hook changes based on the data:** the next single thing to test (colour, format, style, fonts or hook), with the reason.
   - Tags.
   - Anything that needs Giulia.
5. **Email it** (see Email). The cloud "write this week's 3 quizzes" task reads it at 1:37pm and applies its recommendations.
   - To giuliacolaci97@gmail.com, CC shoma.ike97@gmail.com.
   - Subject: "One More Quiz weekly report – <date>".
   - Nobody else.

## Email

- Send with the Gmail connector's send_message (load with ToolSearch: `select:mcp__Gmail__send_message`).
- If that fails, try Composio's GMAIL_SEND_EMAIL. If neither works, report "Email not sent: <reason>".
- Only ever to giuliacolaci97@gmail.com, CC shoma.ike97@gmail.com.

## How

- **Browser**
  - Load the built-in-browser skill first.
  - Use the built-in browser in the Claude desktop app on this Mac (`mcp__remote-devices__Claude_Browser__*`). It is signed in to YouTube and Canva.
  - Never sign out, change credentials or touch other channels.
  - If a site asks for access, request it with scope "site" so later runs don't need it again.
- **Before any change:** confirm Studio shows One More Quiz!. Check the current state first and skip anything already done (Giulia sometimes does items by hand).
- **"Oops, something went wrong":** reload once; if it persists, stop and report.
- **Never:**
  - change visibility, publish times, main titles, descriptions or tags
  - add playlists other than as described above
  - delete anything, upload videos, or commit to the repo
- **Allowed:** running the sign-in and Build video workflows as described above.
- **Downloads:** only thumbnail files, into `~/Pictures/One More Quiz thumbnails/`.
- **Nothing to do:** if nothing needs doing and it isn't Monday, finish without opening the browser.

## Report

- One short line per video or Short: link, items done / already done / not possible (with the reason), pinned yes/no.
- Add "Canva sign-in: fine / renewed / failed (why)".
- On Mondays add "Weekly report sent: yes/no".
- Start with "Needs attention:" if anything failed.
