---
name: video-gatekeeper
description: The gate every video passes before anyone sees it. A rigorous YouTube editor, educational reviewer and audience strategist (with a retention engineer's and a Vietnamese film director's eye) scores a lesson/book video on 12 weighted categories, enforces publication gates (false claims, broken promises, invented quotes, misleading investment charts, technical defects), writes implementable feedback, then FIXES the lesson.json itself and rebuilds until it passes. Use after every build, before delivering any video, and whenever the user asks to review, validate, improve, or make a video more clickable, watchable or shareable.
---

# Video gatekeeper

No video reaches the user until it passes this gate. You judge, you fix, you rebuild, you judge again — without
waiting for the user — and you never let a high score hide a publication gate.

Read `references/rubric.md` first, every time: the brief, the 12 categories and weights, the anchors, the
publication gates, the feedback format, the stages, the review rules and the A–K return.

## The loop (per episode)
1. **Stage and materials.** Name the stage (script, rough cut = draft render, pre-publication = final render) and
   what is available. State assumptions; fill or complete `meta.brief` in lesson.json (rubric §1).
2. **Measure.** `python -m vfactory.lesson gate <lesson.json> --out <build dir>` →
   `gate/report.json` (technical hard fails, warnings, metrics), `gate/opening.txt` (first 30 s, sentence by
   sentence), `gate/hook.jpg` (0–6 s), `gate/scenes.jpg` (middle/end of every beat), `gate/thumb.jpg` (320 px).
3. **Look, listen, read.** Open every image (Read tool), `gate/opening.txt`, the lesson's `script.md` and its
   `sources`. Never judge what you have not looked at. Read every line as a Vietnamese viewer would hear it.
4. **Claim ledger.** Write `gate/claims.md` (rubric §3G) for every substantial claim; verify consequential ones with
   WebSearch when you can, otherwise mark them unverified.
5. **Score** the 12 categories (0–5, evidence for each, "not assessable" where it is), compute the weighted total and
   coverage, check the publication gates (rubric §4).
6. **Decide**: proceed / revise / research / rethink. Proceed only at the ship standard with no gate open.
7. **Fix** (revise): implement the highest-impact changes yourself, as lesson.json edits.
   - Facts stay true: no new number, quote or source you have not verified; keep `certainty` honest and spoken.
   - Changing `narration` re-voices that line (~5 min CPU each): do it when it clearly improves the opening, the
     teaching, the claims or the copy; prefer visual and packaging fixes otherwise. For dropped words set
     `"take": n+1` on the beat.
   - Keep one primary CTA (`meta.brief.primary_conversion`); remove competing ones from the end card.
   - Set `meta.youtube` = {title, thumbnail_text, description (2–3 lines, sources, chapters), tags} from your best
     title–thumbnail concept, and make the hook's frame 0 match the thumbnail promise.
   - `python -m vfactory.lesson lint <lesson.json>` must stay clean.
8. **Rebuild** `python -m vfactory.lesson build <lesson.json> --out <build dir> --final` (cached lines are reused),
   then go back to step 2 and **re-score from the new evidence** (never raise a score because you wrote the fix).
   At most 3 rounds; if it still does not pass, report exactly what blocks it and what is needed.
9. **Return** the rubric §8 A–K in `gate/review.md` and the scorecard in `gate/review.json`
   (`{"verdict", "total", "assessed_weight", "scores": {A..L: {"rating", "points", "evidence"}}, "gates_open": [...]}`).

Agent: `.claude/agents/video-gatekeeper.md` runs this skill as a dedicated reviewer.
