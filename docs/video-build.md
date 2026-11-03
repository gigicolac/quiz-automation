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
4. Writes the voiceover script from `quiz.json` using the templates in `config/video.json`, then voices it with Chatterbox (a voice clone of the reference, running on the free CPU runner). Voice lines are cached, so a rebuild only re-voices lines that changed.
5. Finds the question and answer pages in the slides export. Question pages have the black timer box; answer pages have the peach answer pill.
6. Assembles the video:
   - **Question slides** keep Canva's 10-second countdown. The question is read from 0.3 s.
   - **Answer slides** are looped (the GIF keeps playing) until the answer and quip have been read, plus about 0.9 s.
   - **Intro and "Drop your score" slides** are held on their last frame until their lines finish.
   - **Ending slide:** the hooray plays at the start, the outro line at 1.6 s, and the slide ends 3 s after the line.
7. Mixes the audio:
   - Canva's own audio is dropped.
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

- Chatterbox speed and voice quality on the free runner are untested until the first real build.
- If the slides export detects the wrong number of pages, the build stops with a message rather than guessing.
- No countdown tick sound is added. Canva's own audio is dropped so nothing doubles up with the music.
