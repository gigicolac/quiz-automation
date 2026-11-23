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
3. **A/B Testing: a Title and thumbnail test must always be running on every long video** (Giulia, 16 Nov 2026: "We should always be running thumbnail tests across all quiz videos."). Check every video in scope, every run:
   - **No test, or a title-only test:** stop any title-only test and start "Title and thumbnail".
     - Row 1 = the current title and thumbnail A.
     - Row 2 = the second title from the record's studio_tasks and thumbnail B.
   - **A test has finished:** YouTube keeps the winner. Start the next test straight away: the current title and thumbnail (the winner) against a new title B and the next thumbnail in the queue in config/youtube.json `thumbnail_test`. If the next thumbnail isn't on the `thumbnails` release yet, say so under "Needs attention" so the cloud task makes it.
   - **Thumbnail B, uploaded without a file picker** (the built-in browser has none; worked out 16 Nov 2026): the build copies every quiz's thumbnails to the `studio-thumbnails` branch, which Studio's page can fetch. In the A/B test dialog, find the thumbnail upload input (`input[type=file]` with `accept` containing `image/jpeg`, inside the test dialog's B row; search shadow roots), then run in the page:
     ```js
     const r = await fetch('https://raw.githubusercontent.com/gigicolac/quiz-automation/studio-thumbnails/<quiz>-thumbnail-b.jpg');
     const f = new File([await r.blob()], '<quiz>-thumbnail-b.jpg', {type: 'image/jpeg'});
     const dt = new DataTransfer(); dt.items.add(f); input.files = dt.files;
     input.dispatchEvent(new Event('change', {bubbles: true, composed: true}));
     ```
     Check the B row then shows the new picture (an `img` with a `data:image/jpeg` source) before setting the test. If the file isn't on the branch, fall back to downloading it from the `thumbnails` release into `~/Pictures/One More Quiz thumbnails/` and using the file picker with computer use.
   - **Steps that worked (Quiz #11, 16 Nov 2026)**, all by JavaScript with a shadow-root search:
     1. Running test: button `aria-label="View test report"` → in the report dialog, **New test** → in `ytcp-creator-experiment-delete-confirmation-dialog`, **Continue**. (No test yet: the **A/B Testing** button, `#select-button` inside `ytcp-thumbnails-experiment-editor`.)
     2. The `ytcp-dialog` containing "Test and compare" opens. Check the **Title and thumbnail** radio. Row 1 already holds the current title and thumbnail.
     3. Load thumbnail B into the second `ytcp-thumbnail-uploader`'s file input (above). Type title B into the second `#textbox` (focus, `document.execCommand('selectAll')`, then `document.execCommand('insertText', false, title)`).
     4. **Set test**, then the page's **Save** (`#save`). Deleting the old test only takes effect on Save, so leaving the page without saving changes nothing.
     5. Reload, open **View test report** and check it says "Title and thumbnail" with two custom thumbnails.
   - **When the browser pane is hidden** the page's timers are throttled, so long scripts with `await`/`setTimeout` stall and dialogs can fail to open. Use short synchronous calls with a `wait` between them. If the A/B dialog still won't open, say "show the browser pane" under "Needs attention" and try again next run.
   - **Never fall back to a title-only test.** If thumbnail B can't be uploaded, leave the video without a new test, say exactly why under "Needs attention", and try again next run.
4. **Pin** (after release, once the record has comment_id): pin that comment (Studio > Comments, remove filters, ⋮ > Pin > Pin).
   - **Check a pin on the public watch page**, not in Studio: open `https://www.youtube.com/watch?v=<video_id>`, scroll to the comments and look for "Pinned by @JustOneMoreQuiz" on the score comment. Studio's comment list can show a stale state for a while after a reload (on 16 Nov it showed Quiz #12 unpinned while it was pinned).
   - Report a pin as missing only if the watch page doesn't show it on two runs in a row.

## 4. Each Short (shorts-upload.json): Giulia's standard settings

Giulia, 11 Nov 2026: "For every short ALWAYS…". These six are defaults for EVERY Short, every time, unless she says otherwise. Check every Short in scope on every run, and fix any that is missing one, not only new ones.

Only the entries under `"shorts"` in shorts-upload.json are live Shorts. Entries under `"replaced"` are old uploads that were swapped for a new version (e.g. the 5-second countdown, 13 Nov 2026); they are private with no publish time. Leave them alone and don't set anything on them.

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
- **Reply to every new comment on a Short** (Giulia, 23 Nov 2026: no comments or engagement on Shorts). Reply warmly in one short line, about their score or the question they mention, ending with a nudge to the full quiz ("7/7! Try the full 50 👉 link in the related video"). Never argue, never reply to spam or anything unkind (leave those for Giulia), never ask for likes.

## 5. Mondays only: weekly report (after the Studio steps)

Giulia asked on 10 Nov 2026 for a weekly report, emailed to her and Shoma.

1. **Gather in YouTube Studio** (built-in browser, read only). Cover the last 7 days and lifetime, for every quiz and Short released in the last 14 days:
   - views, impressions, impressions click-through rate, average view duration, average percentage viewed, subscribers gained
   - the audience retention curve: where viewers drop off, e.g. "40% left by question 5"
   - each A/B test's result (Studio > the video > A/B Testing): winner, watch-time share, status
   - comments that mention difficulty
   - **channel click-through rate for the last 7 days and the 7 days before** (Studio > Analytics > Content > Videos, "Impressions click-through rate"; the Analytics API can't give CTR)
2. **Read docs/weekly-report-notes.md** and cover every "Open" item. Read `reports/channel-stats.json` on main (written by the Stats workflow at 6am every Monday).
3. **Check tags** for the coming week's topics with vidIQ keyword research (vidIQ connector, load with ToolSearch).
4. **Write the report**: short, with dot points. Make clear what is measured and what is a recommendation.
   - **Start with the KPI table** (Giulia, 23 Nov 2026). Three rows, from the last entry of `weeks` in `reports/channel-stats.json`, plus CTR from Studio:

     | | This week | Change vs last week | Target now | On track? |
     |---|---|---|---|---|
     | Total subscribers | `subs_at_end` | `subs_net` (gained `subs_gained`, lost `subs_lost`), and that against the week before (`subs_net_change`) | `target_subs` | yes / no, and the gap |
     | Watch hours | `watch_hours` this week; `watch_hours_12m_at_end` over 12 months | `watch_hours_change` | `target_watch_hours_12m` (12-month) | yes / no, and the gap |
     | Click-through rate | channel CTR, last 7 days (Studio) | against the 7 days before | 4.0% | yes / no, and the gap |

   - **Then a 2–3 line summary** of how the channel is tracking against the forecast targets. If any row is behind, say plainly what will change next week to close the gap (one or two specific actions, e.g. which test, which topic, which retention fix) and when we expect to see it in the numbers. Don't invent or round numbers in our favour.
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

## 6. First Monday of each month: forecast sheet

Giulia's forecast model (config/targets.json `sheet`, tab "P-Tracker FY27 - OMQ") holds one row per month (row 8 = Oct 26, row 9 = Nov 26 ... row 16 = Jun 27). On the first Monday of the month, after the report, update the row for the month that just ended with the Google Sheets connector:
- column C actual subscribers: `months["YYYY-MM"].subs_at_end` from `reports/channel-stats.json`
- column E actual 12-month watch hours: `months["YYYY-MM"].watch_hours_12m`
- column G actual CTR, as a fraction (0.031 for 3.1%): the month's channel CTR from Studio (Analytics, Content, that calendar month)
- column H: a short note saying where each number came from and anything unusual
- Never change columns A, B, D or F (targets and formulas). Also refresh the current month's row with month-to-date figures, marked "month to date" in column H.
- Say in the report that the sheet was updated.

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
