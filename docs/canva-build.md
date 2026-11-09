# Canva slides built in GitHub

From Quiz #10, question slides are made by GitHub through the Canva Connect API. Nobody edits a deck by hand.

## Templates (Canva brand templates)

| Template | ID | Used for |
|---|---|---|
| OMQ Quiz Pair (large text, 116px) | `EAHaZJo0d7w` | questions up to 60 characters |
| OMQ Quiz Pair (medium text, 88px) | `EAHaZMCHgTI` | questions of 61–95 characters |
| OMQ Quiz Pair (small text, 68px) | `EAHaZCRO1wg` | questions of 96–170 characters |
| OMQ Intro, rules and outro | `EAHaZFWuBik` | page 1 "`<series>` Quiz" / "Quiz # `<n>`", page 2 rules, page 3 outro |

Fields in each pair template: `question`, `question_gif`, `question_repeat`, `answer`, `answer_gif`.
The green "ANSWER:" label is fixed in the template. The answer field is black, max 30 characters.
Giulia approved three text sizes on 9 Nov 2026, so long questions don't run off the card.

The Connect API can fill templates but can't create or edit them. Creating or changing a template is a one-off
job in Canva: edit the template's draft, then publish it. The master deck DAHTqtWQvFk is never edited.

## How a build runs

1. `quizzes/<quiz>/gif_queries.json` is pushed. **Find GIFs** searches GIPHY and commits `gifs_selected.json`:
   - Fandom quizzes set `allow_branded: true`, so GIFs come from the actual films (official Disney/Pixar accounts first).
   - A GIF is only used if its title contains one of the row's `match` terms.
   - If no GIF fits, the fallback is a still frame from the film, then the Wikipedia lead image.
   - GIPHY's free key allows about 100 searches an hour. Searches are cached in `gif_search_cache.json`, so a re-run continues where it stopped.
2. `quizzes/<quiz>/build.json` with a `canva_build` block is pushed. **Build video** runs `scripts/canva_build.py`:
   - uploads each GIF to Canva (if Canva can't fetch it, uses its still frame instead)
   - fills the right-sized template for each question
   - exports each pair as MP4 (4K)
   - joins the pairs into `slides.mp4`
   - fills the intro template and exports intro, rules and outro
   - then the usual voice-over, captions and video build.
3. Canva's refresh token works once only, so one job shares one access token (`CANVA_TOKEN_CACHE`). Canva jobs run one at a time (concurrency group `build-video`).

Quick test without a full build: commit `quizzes/<quiz>/canva-test.json` (`{"only": [3, 14]}`) on a branch.
That runs **Canva build (test)**: two pairs exported at 1080p and kept as a workflow artifact.

Tested 9 Nov 2026: Quiz #10 Q3 and Q14 were filled and exported from GitHub (designs DAHaZO4mNAQ and DAHaZAgBCDg).
