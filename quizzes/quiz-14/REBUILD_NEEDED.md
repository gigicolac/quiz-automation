# Quiz #14: rebuild needed before approval

Build run 43796125808 (release quiz-14-preview-24) passed its report checks (50 questions, 50 answers,
voice -20 dB, music -36 dB, peak -0.3 dB, one 0.4 s timing note, 3840x2160), but the full GIF check on
16 Nov 2026 found two bad answer GIFs:

- A23: live-action Velma (a real actress's face)
- A33: a Simpsons crucifix gag (unsuitable for a family quiz)

Both picks were replaced in gif_queries.json (commit 80562cc; Find GIFs updated gifs_selected.json in 3efa8dc).
The other 98 GIFs were all cartoons/animation or animals. Note: Q07 and Q20 use the same TMNT clip (acceptable).

Next progress run: once no Build video run is in progress or queued (Quiz #13 started 16 Nov 07:43 UTC), run
`gh workflow run build-video.yml --ref claude/quiz-14 -f quiz=quiz-14`, then check the new A23 and A33 (and the
rest as usual). Delete this file in the approval commit.
