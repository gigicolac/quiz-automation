# Quiz #13: rebuild needed before approval

Build run 43825845442 (release quiz-13-preview-25) passed the basic numbers (50 questions, 50 answers,
voice -20.0 dB, music -36.6 dB, peak -0.3 dB, 3840x2160, 986 s), but on 16 Nov 2026:

- **Audio:** the report warned "no buzzer found in the Canva audio" for Q38-Q50, and the final video is
  quiet at those countdown ends (checked with volumedetect: Q36/Q37 peak -12 to -15 dB at the buzzer,
  Q38 -20 dB). PR #39 (claude/buzzer-fallback) reuses the nearest earlier buzzer when a page has none;
  it is merged into this branch so the rebuild is its preview build.
- **GIFs (full check, 3 frames x 100 slots):** real faces in Q17 (boy with a controller), A04 (live-action
  Harry Potter), A15 (man in a kitchen), A27 (man with an iPhone), A31 (man doing a puzzle); A30 showed an
  app screen with people's names and photos. Replaced by hand picks in gif_queries.json:
  Q17 901ojwtVHZAze, A04 W0I3epucnTjCYzRnKv (zoo owl), A15 KB8Nbefy94rneO3A3n (Sims tiny house),
  A27 O8mLgjaAIqxdsMFwjj, A30 3ilAlREEGJED7eaB49, A31 17EUIjkxrxeIo. Picks chosen by title (Giphy is
  blocked from the cloud shell), so check these six closely. The other 94 slots were cartoons, animals,
  objects or faceless/costumed figures (Q21 is a prosthetic alien, Q16/Q33 show no face).

Next progress run: once no Build video run is in progress or queued (Quiz #14 rebuild 43851205230
started 16 Nov 10:41 UTC), run `gh workflow run build-video.yml --ref claude/quiz-13 -f quiz=quiz-13`.
On success: check the report has no bare "no buzzer found" warning, listen/measure Q38-Q50 buzzers, check
all GIFs again, then merge PR #39 first, merge main into this branch, and approve. Delete this file in
the approval commit.

**17 Nov progress run:** rebuild 43910523670 (quiz-13-preview-28) fixed the buzzers (Q38-Q50 now peak -3 to -14 dB at
the countdown end, same as Q30-Q37; PR #39 merged). Full GIF check of that build: 99 of 100 slots fine (the five
hand picks for Q17, A04, A15, A30, A31 are an object/cartoon/owl/Sims house/hands), but **A27's hand pick
O8mLgjaAIqxdsMFwjj ("Apple Iphone GIF", rvmendozaonyourphone) is a man's face**. Replaced with
ig9frFqBku3wO1Xvze ("Phone App GIF by Meesho Tech", from row 27's question candidates), chosen by title. Next run:
check A27 in the new build closely, then approve.
