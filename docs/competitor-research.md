# Competitor research: quiz videos with 1M+ views

Giulia, 16 Nov 2026: "Use VIDIQ to research competitors and replicate their topics based on the most viewed. Aim to research quizzes that have 1m + views and replicate their: Thumbnails, Titles, types of questions, questions and formats."

The Monday writing run repeats this research every week (docs/weekly-automation.md, section 1) and adds what it finds to the log at the bottom. Copy **what works** (topic, title formula, thumbnail layout, question type, format), never a competitor's wording: write every question, title and thumbnail ourselves. Copying another channel's questions or thumbnails word for word risks copyright claims and YouTube's "reused content" rule, which can stop monetisation.

## How to research (each Monday, about 30 vidIQ credits)

1. `vidiq_outliers` with `minViews: 1000000`, `sort: viewCount`, `language: en`, long-form, for the week's categories (e.g. "pop culture trivia quiz", "tv show quiz", "music quiz"), plus "general knowledge trivia quiz" as a control. Widen to `publishedWithin: twoYears` and `minViews: 500000` if there are fewer than 5 relevant results.
2. Keep only videos in **our format**: spoken or written questions, then the answer. Note "guess the X by emoji/voice/song" videos separately as format ideas (section "Formats we don't make yet").
3. Look at the thumbnails (`vidiq_get_images`) of the top 5 in our format. Note the layout, colours, words and numbers.
4. Pick topics and a title formula from the results. Record the source videos (ID, views) in the log below and in `quiz.json` `tags_research`.

## What 1M+ quiz videos in our format do (16 Nov 2026)

| Video (channel) | Views | Title formula | Thumbnail |
|---|---|---|---|
| General Knowledge Trivia Quiz! 100 Questions Everyone Should Know – Do You? (Fun Quiz Questions, 3ShqXh5tI1s) | 5.2M | Category + big count + "Everyone Should Know" + challenge | Red top band "GENERAL KNOWLEDGE", 8-picture grid, purple bottom band "EVERYONE SHOULD KNOW" (our current style) |
| How Well Do You Know Animals? General Knowledge Trivia Quiz (Quiz Blitz, B_5uPsFgzgI) | 4.1M | "How well do you know X?" | One question on the thumbnail ("Whose bite is strongest..?") with two pictures and A/B labels |
| General Knowledge Trivia Quiz! 101 Questions EVERYONE Should Know! Part 2 (Fun Quiz Questions, GRqQD4n0UVc) | 3.2M | Same, numbered series | Same grid style |
| Can You Pass the U.S. Citizenship Test? 50 Questions (Trivia Square, LvmaZmry60s) | 2.8M | "Can you pass the ___ test?" + count | "CAN YOU PASS?" huge, "35 RIGHT TO PASS", round "50 QUESTIONS" badge, one big photo |
| Can You Pass This Math Quiz? Easy to Impossible (Quiz Blitz, ZEqdETrX-zI) | 2.0M | "Can you pass" + difficulty ladder | One question shown huge with answer options |
| Can You Score 50/100 on This General Knowledge Quiz? (Wisdom Time, wmwwuCi7gx0) | 1.2M | Score threshold | One question ("Which food never spoils?") with four options |
| Your IQ Is Above Average If You Get 45+ Right in This GK Quiz, 80 Questions (Wisdom Note, JdyNYQxSaIE) | 1.1M | Score threshold + IQ claim | One question with four options |
| Are You Well Educated? Score At Least 4/10! (GK Studio Pro, -shDOWURZSM) | 1.1M | Ego challenge + score threshold | Big yellow/red text "TRY TO SCORE AT LEAST 4/10!" |
| How Well Do You Know Michael Jackson? (WhizQuizz, 48j1845B3Zo) | 1.2M | "How well do you know X?" fandom | Subject's picture + one question with three options |
| General Knowledge Trivia Quiz, 101 Questions MOST People Get Wrong! (Quiz Madness, w8gk6Oycsqc) | 0.7M | "Most people get wrong" | Huge "101 QUESTIONS" number + 4-picture grid with green ticks |
| Christmas Trivia Quiz, 60 Festive Questions (Cunning Quizzes, Q37seYslkvQ) | 0.5M | Seasonal + count | Cartoon Santa, "MERRY QUIZMAS!" |

### What to copy

- **Titles:** (1) "{count} Questions Everyone Should Know" (already ours), (2) a **score threshold** ("Can you score 40+?", "Try to score at least…"), (3) "Can you pass this ___ quiz/test?", (4) "How well do you know ___?" for fandom, (5) "Most people get these wrong". Our Quiz #9 B title "every dummy should know" (cheeky challenge) is leading its A/B test 59% to 41%, which fits (1) + (2).
- **Thumbnails:** the grid + "Everyone should know" style we use is proven (5.2M). The next styles to test against it: a **huge question count** ("50 QUESTIONS") with a 4-picture grid, and **one real question on the thumbnail** with a picture (no multiple-choice options, because our quizzes have none). Bold yellow/white text on blue or red, 3–6 words.
- **Question types:** mostly famous, recognisable facts ("everyone should know"). Start easy and get harder ("easy to impossible"). Mix pictures people know on sight (characters, landmarks, flags, animals, foods).
- **Formats:** 50–100 questions, 15–35 minutes; numbered series ("Part 2", "#4") build repeat viewers.
- **Topics with 1M+ views in our format:** general knowledge, animals, citizenship/"can you pass" tests, maths, music icons (Michael Jackson), seasonal (Christmas).

### Formats we don't make yet (ideas, need pipeline work)

"Guess the movie/word/player by emoji", "guess the song/character by voice", "A to Z" (name a country for each letter), "would you rather", "people vs quiz" (real people competing). These dominate 1M+ views (e.g. 10.1M, 3.0M, 2.7M) but need new slide types, audio clips or real people, so they're proposals for Giulia, not something the weekly run changes on its own.

## Log

| Date | Searches | Applied to |
|---|---|---|
| 16 Nov 2026 | "trivia quiz questions general knowledge", "how well do you know quiz fandom movie trivia", "disney quiz…", "pop culture tv show music trivia quiz 50 questions" (minViews 0.5–1M) | Title B formula (config/youtube.json), thumbnail test queue, difficulty curve, week of 16 Nov topics |
| 16 Nov 2026 (weekly run) | vidIQ outliers (minViews 0.5M, by views): "pop culture trivia quiz", "tv show trivia quiz", "music trivia quiz"; keyword research "cartoon quiz", "2000s quiz" | Quiz #13 2000s pop culture: "Can you pass this ___ quiz?" title (Quiz Blitz QTg9gUYjtGE 844k, Trivia Square LvmaZmry60s 2.8M; vidIQ score 95). Quiz #15 Music: 5 family-friendly Michael Jackson questions (MJ quizzes 1.2–1.3M: 48j1845B3Zo, WCbCp41kqjk). Quiz #14 Cartoons ("cartoon quiz" ~18k searches/month). Most 1M+ music/pop culture hits are "guess the song/singer" formats (not ours yet) |
