# Video build (GitHub Actions)

The slides come from Canva. Everything you hear is added in GitHub by `.github/workflows/build-video.yml` and `scripts/build_video.py`.

## What the build does

1. Reads `quizzes/<quiz>/build.json`, which holds the Canva MP4 export links:
   - `slides`: the 100-page quiz design
   - `intro`, `rules`, `outro`: pages 1–3 of the intro and outro design
2. Keeps a copy of those exports on a draft release called `<quiz>-canva`, because Canva links expire after a few hours.
3. Decrypts the private audio using the `ASSET_KEY` secret:
   - music: Game Show Groove
   - the hooray sound
   - the voice reference
4. Writes the voiceover script from `quiz.json` using the templates in `config/video.json`:
   - Emoji are removed from what is spoken but stay on the slides.
   - Numbers are written out as words for the voice, for example 130 becomes "one hundred and thirty" and 1945 becomes "nineteen forty-five". Captions keep the digits.

   It then voices the script with Chatterbox (a voice clone of the reference, running on the free CPU runner). Voice lines are cached, so a rebuild only re-voices lines that changed.
5. Finds the question and answer pages in the slides export. Question pages have the black timer box; answer pages have the peach answer pill.
6. Assembles the video:
   - **Question slides** keep Canva's 10-second countdown and are cut at 10.6 s, just after "00:00". Canva pads some pages to the length of their GIF. The question is read from 0.3 s.
   - **Answer slides** last as long as the answer and quip take to read, plus about 0.9 s, with a minimum of 3 s. Short GIFs loop and long pages are trimmed.
   - **Intro and "Drop your score" slides** are held on their last frame until their lines finish.
   - **Ending slide:** the hooray plays at the start, then four outro lines are timed to the slide's animation (set in `config/video.json`): "How did you go?" at 1.8 s, "Drop your score…" at 4.9 s, "like and subscribe" at 8.2 s and "One more quiz?…" at 14.7 s. The slide plays in full, about 26 s.
7. Mixes the audio:
   - Canva's own audio is dropped, apart from the buzzer: the countdown's "time's up" buzzer (10 s into each question page) is kept, levelled to about −19 dBFS.
   - Music runs under the whole video at about 13 dB below the voice. It dips a further 6 dB while someone is speaking and fades in and out over 3 s.
8. Writes captions (`.srt`) from the voiceover timings.
9. Uploads the video, captions, `voiceover.json` and `build_report.json` to a **draft** release `<quiz>-preview-<run>`. Drafts are visible only to repo collaborators.
10. Commits `quizzes/<quiz>/build_result.json`, which records the status, the release tag, the levels and the end of the build log.

Nothing is uploaded to YouTube.

## One-time setup (Giulia)

Add a repository secret named `ASSET_KEY`:

1. Go to Settings > Secrets and variables > Actions > New repository secret.
2. Name it `ASSET_KEY` and paste the value from the key file Claude sent in chat.

The key decrypts `assets/private/*.enc`. The audio files are committed only in encrypted form (AES-256), because the repo is public. If the key is ever lost, re-encrypt the originals with a new key:

```bash
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:ASSET_KEY -in music.flac -out assets/private/music.flac.enc
```

## Running a build

- **Automatic:** commit `quizzes/<quiz>/build.json` with fresh Canva export links. The build starts on push.
- **Manual:** Actions > Build video > Run workflow, then enter the quiz folder (for example `quiz-09`). `dummy` voice is a fast test that uses a tone in place of the voice.

## Tuning

Adjust these in `config/video.json`:

- Loudness, ducking and fades
- Timing gaps
- The spoken intro, rules, question, answer and outro wording

Test the assembly locally without the voice model:

```bash
python scripts/build_video.py --quiz quizzes/quiz-09 --slides slides.mp4 --intro intro.mp4 \
  --rules rules.mp4 --outro outro.mp4 --private private/ --out out/ --tts dummy
```

## Limits and open items

- First real build (preview #3, 3 Nov 2026):
  - Chatterbox voiced all 103 lines on the free runner. The whole run took about 1 h 55 min, almost all of it the first-time voicing.
  - Video length 15.3 min. Voice about −20 dBFS RMS, music about −35 dBFS.
  - Found in that build and fixed afterwards: emoji were read out in a few answers (a02, a05, a07, a10, a11, a30), and "The answer is The…" had a capital T.
- Quiz #9 check (3 Nov 2026), run locally on the real Canva exports with a placeholder voice:
  - all 100 pages detected
  - total length 14.0 min
  - voice about −20 dBFS RMS, music about −33 dBFS (−39 when ducked)
  - fade in and out confirmed
  - hooray at the start of the ending slide
- If the slides export detects the wrong number of pages, the build stops with a message rather than guessing.
- The countdown ticks are not used, only the buzzer. To add the ticks, take more of the Canva audio (`buzzer.from` in `config/video.json`).
