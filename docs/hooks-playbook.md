# Hooks playbook: titles, thumbnails, descriptions, Shorts

Read this before writing any title, thumbnail text, description, Short hook or quiz intro line. Every one of them must work as a hook. After each weekly analytics check, add what won and what flopped to the "Results log" at the bottom.

Sources:
- Giulia's notes, 9 Nov 2026: a post analysing 1,000+ viral hooks.
- vidIQ, "9 YouTube Hooks That Keep Viewers Watching" (Dec 2025).
- vidIQ outlier research on quiz videos (6 Nov 2026).

## The test every hook must pass
1. **It's about the viewer, not us.** "Can you…", "you", their score, their memory.
2. **It opens a loop the video closes.** A question, a contradiction, or a challenge they can only settle by watching.
3. **It's specific.** A real question from the quiz, a real number, a real place. Never "some trivia".
4. **It's true.** No invented stats ("only 1 in 10 people…") unless we can back them up. "Most people get these wrong" is OK only as a light challenge, never as a fake figure.
5. **The hook comes first.** Shorts titles are cut at about 40–50 characters on mobile, so the hook goes in front and "General Knowledge Quiz #9" goes last.
6. **It sounds human.** The best 2025 hooks don't read like hooks. They sound like something a person would genuinely say.

## Patterns that work (with quiz versions)
| Pattern | Why it works | Quiz example |
|---|---|---|
| **Contradiction / contrast** (~30% of top viral hooks) | Unresolved tension; the brain can't scroll past it | "Big Ben isn't actually the clock 🤯" · "Easy questions. Hard score. 😬" |
| **Specificity** | Hyper-specific feels lived and credible | "Smallest bone in your body? It's not in your hand 👂" |
| **Timeframe tension** | Short, punchy timeframes start a curiosity loop | "7 questions. 5 seconds each. Go! ⏱️" · "Prove it in 60 seconds" |
| **POV (advice in disguise)** | Defences drop; feels relatable | "POV: you're the one who always wins pub trivia" |
| **Curiosity question** | Open loops | "Saturn or Jupiter: which has more moons? 🪐" |
| **Drop into the action** | Starts mid-moment | "Question 1, no warm-up: what's the capital of Australia?" |
| **Audience-centric challenge** | They're the hero | "How much do you REALLY know? 🤔" (the Friends title style that worked) |
| **Raise the stakes** | Something on the line | "Get 7/7 and you're officially the quiz captain" |
| **Contrarian** | Flips expectations (must be true) | "Stop guessing 'Sydney'" |
| **Visual first** | An image they can't ignore (thumbnail and first frame) | The picture card from the question, a big bold number |
| **Shocking stat** | Only with a real, sourced number | (use only when verifiable) |
| **Unanswered question** | Self-reflection | "When did you last get a pub quiz 100% right?" |

The best hooks **stack 2–3 patterns**, for example a specific question plus a contradiction plus a challenge.

## Long-video titles
- Keep the proven series title as variant A, e.g. "General Knowledge Quiz #9 | 50 Questions Everyone Should Know".
- Variant B (Test & Compare) is a hook title built from this playbook and vidIQ outliers, e.g. "Can You Pass This General Knowledge Quiz? 🧠 50 Trivia Questions | Quiz #9".
- Fandom quizzes: "How well do you REALLY know Friends?" style. An audience challenge plus a capitalised emphasis word.
- Score each candidate with vidIQ `score_title` (5 credits) only for the final 2–3.

## Thumbnails
- One idea, readable on a phone: 3–5 words max, high contrast, big category word + quiz number.
- A = series style (red band). B = a variation that tests one thing only (band colour, a hook word, a stand-out picture).
- The picture should be the most surprising or recognisable image in the quiz (visual-first hook).
- Shorts use the same thumbnail as their long video unless a test says otherwise.

## Descriptions
- **First line = the hook again**, in a fuller sentence (it shows in search and under Shorts).
- Long videos: Giulia's house style (series hook line, 🎯 How It Works, @JustOneMoreQuiz, like / comment / subscribe "every Thursday, Saturday & Sunday", chapters).
- Shorts: the default template below. Vary the opening line each time to match the Short's title.

### Shorts default template (Giulia, 9 Nov 2026)
```
Sneak peek 👀 How many can you get right before the timer runs out?

This is just a taste of this week's {series} Quiz #{number}, with {count} questions everyone should know. No multiple choice, just pure memory. 🧠

👉 Watch the full quiz here: {full_quiz_link}

Drop your score in the comments and challenge a friend to beat it! New quizzes every Thursday, Saturday and Sunday, so subscribe and you won't miss one.

#shorts #quiz #{series_tag} #trivia #quiztime #brainteaser #justonemorequiz
```
- "#shorts" goes in the description, not the title.
- Links in Shorts descriptions aren't clickable, so set the **Related video** to the full quiz (Studio).

## Shorts titles
- Lead with the most surprising question or answer in that Short (specificity), or a challenge with a number ("Can you get 7/7?").
- Giulia's chosen default style: "Most people get these WRONG 😬 General Knowledge Quiz #9". Rotate patterns across a week's Shorts so we learn which pattern wins.
- Don't spoil the hook question's answer in the title unless the contradiction itself is the hook.

## On-screen Short hooks (header text)
Rotate the hooks in `config/shorts.json`, using the patterns above. Keep each under about 30 characters so it fits the header.

## Weekly refinement loop
1. After 3+ days, compare each video and Short at the same age: impressions, click-through rate, views, average view duration, subscribers gained, and which A/B variant won.
2. Note the pattern each title, thumbnail and hook used, and log the result below.
3. Next week: use more of the winning patterns, drop the losers, and always keep one new experiment.

## Results log
| Week | Item | Pattern | Result |
|---|---|---|---|
| 9 Nov 2026 | Quiz #9 Short 1 "Most people get these WRONG 😬" | challenge / contrast | (pending) |
