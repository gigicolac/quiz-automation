# Canva Autofill route (Quiz #10 onwards): plan and setup

**Goal:** stop filling slides through Claude's Canva connection (about 100 tool calls per quiz). Instead, GitHub fills a Canva brand template through the Canva Connect API. Claude's part shrinks to writing the questions and reviewing.

**Status:** not built yet. It needs the one-time setup below from Giulia.

## How it will work

1. **Brand template "OMQ Quiz Pair"**, made once from a question and answer pair in Quiz #9 and published as a brand template. Its data fields are:
   - `question`: text on both the question and answer page
   - `answer`: answer pill text
   - `question_gif`: video on the question page
   - `answer_gif`: video on the answer page
2. **A second brand template "OMQ Quiz Intro"** with the fields `title` and `quiz_number`, for the intro page. The "Drop your score" and ending slides don't change, so they are exported once and reused.
3. **A new workflow, `canva-build.yml`**, which runs for each quiz:
   1. Uploads the 100 GIPHY MP4s to Canva as assets. GitHub can reach GIPHY, unlike Claude's sandbox.
   2. Runs 50 autofill jobs, one per pair.
   3. Exports each pair as MP4.
   4. Hands the files straight to `build_video.py`.

   Exporting per pair also gives exact page boundaries. Font-size rules for long questions and answers are applied by choosing between template variants (normal, long or extra long).
4. Claude's work per quiz drops to:
   - writing `quiz.json`
   - choosing GIFs (`find_gifs.py`, already in GitHub)
   - the two reviews

## Setup needed from Giulia

1. **Plan and security.** Canva says Autofill needs "a Canva plan that includes Autofill, such as Canva Pro, Canva Teams, or Canva Enterprise". The account also needs multi-factor authentication turned on.
2. **Developer integration.**
   1. Go to canva.com/developers > Your integrations > Create an integration.
   2. Under Configuration, turn on these scopes:
      - `design:content` (read and write)
      - `design:meta` (read)
      - `brandtemplate:meta` (read)
      - `brandtemplate:content` (read)
      - `asset` (read and write)
   3. Add the redirect URL `http://127.0.0.1:3001/oauth/redirect`.
3. **Secrets.** Add `CANVA_CLIENT_ID` and `CANVA_CLIENT_SECRET` as repository secrets. Claude will then add a one-time sign-in helper to get the refresh token.
   - Canva refresh tokens can change each time they're used, so the workflow will need to save the new token back as a secret. That needs a fine-grained GitHub token, `GH_SECRETS_TOKEN`, scoped to this repo with "Secrets: read and write".
4. **Brand templates.** In Canva, the data fields are tagged with Bulk Create ("Connect data"), then the design is published as a brand template. Claude can prepare the source design, but publishing needs the Canva plan feature above.

Once steps 1–3 are done, Claude builds `canva-build.yml` and a test run on Quiz #10.

Source: Canva Connect [Autofill guide](https://www.canva.dev/docs/connect/autofill-guide/), checked 3 Nov 2026. Brand templates: none exist on the account yet (checked 3 Nov 2026).
