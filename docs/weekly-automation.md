# Weekly automation: three quizzes a week, no manual steps

Giulia (10 Nov 2026): "From next week all three quiz creation, upload, and scheduling should all be automatic. Please notify me each time a quiz and the subsequent shorts have been uploaded." She also asked for no approval stops (6 Nov), and gave a standing merge authorisation for quiz-only pull requests (see AGENTS.md).

This is the runbook the scheduled tasks follow. They start with no memory of earlier chats, so everything they need is here or linked from here.

## The week at a glance (Sydney time)

| When | What | Where |
|---|---|---|
| Mon 10:13 | Studio steps, then the **weekly report** email to Giulia and Shoma (Studio-only numbers: A/B results, retention) | Mac scheduled task (Giulia's MacBook) |
| Mon 1:37pm | **Plan and write** the week's 3 quizzes, start their GIF searches | Cloud scheduled task "weekly quizzes" |
| Every 3 h, Mon 4:41pm to Thu | **Move the quizzes along**: start the next build, check finished builds, approve, merge | Cloud scheduled task "weekly quizzes: progress" |
| Daily 8:00am | Upload the next approved quiz on main to the next free slot (Thu 3pm / Sat 1pm / Sun 1pm US Eastern) | GitHub `upload.yml` |
| Daily 9:30am | Make and upload Shorts (5 per quiz, 8am and 6pm US Eastern) | GitHub `shorts.yml` |
| Daily 11:47am | Email Giulia and Shoma about anything uploaded in the last day | Cloud scheduled task |
| Tue/Fri/Sun/Mon 10:13am | Studio-only settings (end screen, location, level, A/B test, pinning) | Mac scheduled task |

Release slots for the week the quizzes are written in: Thursday 3pm, Saturday 1pm and Sunday 1pm US Eastern (Fri 6–7am, Sun 4–5am and Mon 4–5am Melbourne).

## 1. Plan (Monday)

1. Read `config/categories.json` and every `quizzes/*/quiz.json` (`category`, `topic`) on main and on open `claude/quiz-NN` branches. The next quiz number is one more than the highest `quizzes/quiz-NN`, counting any open `claude/quiz-NN` branches too.
2. Pick 3 categories by going round `rotation` in order from the most recent quiz's category. Never use the same category twice in a row. Follow every line of `rules`.
   - **Fandom:** research what people love and search for right now: vidIQ keyword research and outliers, YouTube trending. Pick a franchise not quizzed in the last 365 days (`history` plus quiz.json `topic`s).
   - **Education:** a Victorian Curriculum unit for one year level from 7 to 12.
   - **Family-friendly only.** If a topic could be sexual, violent, hateful or otherwise unsuitable, pick another.
3. Read the latest weekly report email in Giulia's Gmail ("One More Quiz weekly report", sent by the Mac task that morning). Apply what it recommends: difficulty, thumbnail test (`config/youtube.json` `thumbnail_test`), hook wording, tags. Note what you changed for the next report.

## 2. Write each quiz (Monday)

One branch per quiz: `claude/quiz-NN` from current `origin/main`. Copy the shape of the latest quiz folder (for example `quizzes/quiz-12`).

- **`quiz.json`**
  - `id`, `number`, `series`, `difficulty`, `title`, `description_hook`, `thumbnail_tagline`, `tags`, `tags_research`, `status: "questions_written"`.
  - `review.questions`: decision `auto-approved`, with a note saying who wrote and fact-checked them and when.
  - `questions`: 50 of them, each with `n`, `question`, `answer` (short, with one emoji) and `reveal` (one fun sentence).
- **Questions**
  - 50 per quiz. Easy to hard across the quiz. Mostly medium; fandom quizzes are hard unless the report says otherwise.
  - Each fact is checked against a reliable source; leave a question out if in doubt.
  - No trick wording, and no answers that are now out of date.
  - Movies: include well-known classics (for example Marvel, Pixar, Star Wars, Harry Potter) alongside others (Giulia, 10 Nov).
- **Title** in the house style: "How Well Do You REALLY Know <Topic>? <emoji> 50 <Topic> Trivia Questions | <Series> Quiz #NN". Score the final 2–3 with vidIQ `score_title`. The second title for the A/B test comes from `config/youtube.json`.
- **Thumbnail hook** (`thumbnail_tagline`) reads on from the heading as one sentence ("Disney Quiz #10 … Only REAL fans would know"). The defaults are in `config/youtube.json` `thumbnail_taglines`. See `docs/hooks-playbook.md`.
- **Tags** come from vidIQ keyword research for the topic (search volume and competition), not guesses. Record the research in `tags_research`.
- **`gif_queries.json`**: a question and an answer search per question, plus `match` words.
  - Never use real people's faces: actors, celebrities, sports stars, politicians. Prefer animated characters, objects and scenes.
  - Hand-pick (`question_pick` / `answer_pick`) where the default search would show a real person.
  - Set `allow_branded: true` only for film or TV topics.
- **Category and topic** go in `quiz.json` as `"category"` (a rotation name) and `"topic"` (e.g. "Pokemon"). Quiz-only PRs may only touch the quiz's own folder, so the rotation history is `config/categories.json` `history` (quizzes up to #12) **plus** the `category`/`topic`/release of every `quizzes/*/quiz.json` and `upload.json` on main. Don't edit `config/categories.json` from the weekly task.

Commit `quiz.json` and `gif_queries.json` and push: **Find GIFs** runs automatically. Then check `gifs_selected.json`:
- Every question and answer has a picture.
- Nothing shows a real person or anything unsuitable (check titles and slugs, and the candidates' `match`).
- Clips under 2 seconds have become stills; that's expected.

Fix picks and push again if needed.

## 3. Build (one at a time)

`build-video.yml` allows **one running and one waiting** build per repository, and a newer waiting build cancels the older waiting one. Canva's sign-in is also single-use: a run that waited while another build renewed it would hold a stale copy. The build now spots that and queues itself again rather than using it, but don't rely on it.

So start a build only when **no** Build video run is in progress or queued:

```
gh api "repos/gigicolac/quiz-automation/actions/workflows/build-video.yml/runs?per_page=5" --jq '.workflow_runs[] | select(.status != "completed") | .id'
```

That must print nothing. Then start the build by committing `quizzes/quiz-NN/build.json`, a copy of the previous quiz's with the number changed (4K Canva slides, Chatterbox voice), and pushing. After a failure, start it again with `gh workflow run build-video.yml --ref claude/quiz-NN -f quiz=quiz-NN`.

A build takes about 3 hours. If one fails with "Canva token refresh failed … Run the Sign in workflow", the Canva sign-in is gone. Stop starting builds and start the Mac scheduled task "Quiz Studio steps on Giulia's Mac" now (fire it with the scheduled-task tools). It renews the sign-in in the browser on Giulia's Mac (docs/sign-in.md, "Renewing the Canva sign-in without Giulia") and restarts the failed build. Email Giulia (CC Shoma) only if that fails, for example because the Mac is off or Canva asks for a login.

## 4. Check, approve, merge (progress task)

When a build succeeds:
1. **Report:** download `build_report.json` from the build's draft release (`gh api .../releases`, tag `quiz-NN-preview-<run number>`). Check:
   - 50 `qNN` and 50 `aNN` segments plus the intro and outro
   - voice about -20 dB RMS, music about -36 dB, peak no higher than -0.3 dB
   - warnings are only minor timing notes (under 1 s)
2. **Frames:** extract frames straight from the release asset with ffmpeg. Get the asset URL with `curl -sS -o /dev/null -w '%{redirect_url}' -H "Authorization: Bearer $(gh auth token)" -H "Accept: application/octet-stream" https://api.github.com/repos/gigicolac/quiz-automation/releases/assets/<id>`, then run `ffmpeg -ss <s> -i "$url" -frames:v 1`. Use the segment start times in the report.
   - **What to look at:** the intro, a question and its answer, one more question near the middle, and the outro.
   - **What to check:** text fits its box, the GIF matches the question, there are no real people's faces and nothing unsuitable, and the video is 3840×2160.
   - **Every GIF, not just a sample.** On 10 Nov a sample looked fine, but a full check found 16 of Quiz #11's 100 GIFs and 15 of Quiz #12's showing real faces: memes, actors, a K-pop group, Stan Lee. One was also album-cover art. So also take one frame per `qNN`/`aNN` segment (start + 3 s, at 640 px wide), crop the GIF box (about x 46–290, y 82–258 at that size), tile them into labelled sheets of 25 and look at all 100.
   - Faces seen from behind, tiny distant figures, crowds, masked or costumed characters and cartoons are fine. A clear human face is not.
   - **Fixing a pick:**
     - Giphy is blocked from the cloud shell. Choose from `gif_candidates.json`: prefer titles that say animation, cartoon or illustration, or name an object.
     - On Giulia's Mac, the built-in browser can show the candidates. Open giphy.com, then replace the page with a grid of the candidates' `still` images.
     - If every candidate is a person, change that row's query to an object (for example "speedometer", "megaphone", "oil can"). For film quizzes, add a word from the new query to the row's `match` list.
     - Push; Find GIFs runs again. Check the new picks, then rebuild.
3. **Thumbnails:** download `thumbnail-a.jpg` and `-b.jpg` from the same release and look at them.
   - The heading and hook are both full width and readable.
   - The fonts are Nunito Sans Bold and Tinos Italic.
   - The pictures are suitable.
4. **Approve:** record `review.video` in `quiz.json`, in the same format as quiz-10:
   - decision `approved`, by, date
   - **evidence:** run ID, the numbers above, and which frames you looked at
   - `source_commit`, `duration_s`, `release_tag`
5. **PR:** open a pull request for the branch. It must change files in `quizzes/quiz-NN/` only. Then:
   - run `python -m unittest discover -s tests`
   - **merge** under Giulia's standing authorisation (AGENTS.md), saying so in the PR description with the run and checks
   - **Merge one quiz at a time, in number order**, so the daily upload takes them in order: lowest number to the earliest slot.

If a build fails: read the failing step's log, fix what's within the quiz folder (a bad GIF pick, a too-long answer), and start it again once. Anything that needs a code or workflow change: fix it on its own branch and PR, merge main in, run the tests, and merge it under Giulia's standing authorisation for pipeline changes (AGENTS.md). Email her what changed. Then update the quiz branch from main and restart the build.

## 5. Upload, Shorts and emails (automatic)

- **Upload:** the daily upload at 8am Sydney takes the lowest-numbered approved quiz on main without an upload and schedules it in the next free slot. It does one quiz per day, so merge by Tuesday evening for all three to make that week's Thu/Sat/Sun slots. If a quiz will miss its slot, run `upload.yml` by hand on main with `mode=upload` and `publish_at=next` (or an exact US Eastern time).
- **Shorts:** made and uploaded by `shorts.yml` after the long video is scheduled.
- **Emails:** the daily email task tells Giulia and Shoma what was uploaded.

## 6. Weekly report (Monday)

Giulia wants a report every Monday covering:
- **Analytics** for the past week's videos and Shorts: views, impressions, click-through rate, average view duration and audience retention, and subscribers gained.
- **Every A/B result:** title and thumbnail. Say which won, by how much, and the next single change to test (colour, format, style, fonts or hook).
- **Difficulty and retention:** where viewers drop off, and whether the difficulty should change.
- **Tags:** re-checked against vidIQ.
- **Open items** in `docs/weekly-report-notes.md`.

Test & Compare results and retention exist only in YouTube Studio, so the **Mac Studio task writes and sends the report** on its Monday run, after its Studio steps:
- **Subject:** "One More Quiz weekly report – <date>"
- **To and CC:** Giulia, with Shoma in CC

The Monday cloud task reads that email to decide the week's changes. If there's no report email by 1:30pm Monday (the Mac was off), the cloud task sends a shorter report itself using public numbers (YouTube Data API views, likes and comments, and vidIQ). It says that the Studio-only numbers follow when the Mac is on.

## Safety rails

- **Never** publish immediately, change visibility, or delete videos, releases or upload records.
- **Never** commit generated media, credentials or private audio.
- Don't mark anything approved without having actually checked it (AGENTS.md).
- If something is uncertain, and above all after an upload error, check YouTube before retrying. Don't upload twice.
- **Emails** go only to giuliacolaci97@gmail.com, with shoma.ike97@gmail.com in CC.
