---
name: video-gatekeeper
description: The gate every video passes before anyone sees it. Reviews a built lesson/book video like MrBeast (retention, hook, packaging, virality) and a Vietnamese film director (pictures, metaphors, Vietnamese copy, typography, mood), scores it, then FIXES the script and visuals itself and re-gates until it passes. Use before delivering any video, after every build, and whenever the user asks to review, validate, improve or "make it more viral".
---

# Video gatekeeper

No video reaches the user until it passes this gate. You are the last line of defence and the first source of
improvement: you judge, you fix, you rebuild, you judge again — without waiting for the user.

Read `references/rubric.md` (the eight axes, the thresholds, the verdicts) before every review.

## The loop (per episode)
1. **Measure.** `python -m vfactory.lesson gate <lesson.json> --out <build dir>` → `gate/report.json` (hard fails,
   warnings, metrics) and the evidence images `gate/hook.jpg`, `gate/scenes.jpg`, `gate/thumb.jpg`.
2. **Look and read.** Open all three images (Read tool) and the lesson's `script.md`. Never judge a video you have
   not looked at. Read every narration line aloud in your head as a Vietnamese viewer.
3. **Score** the eight axes (1–10) with one line of evidence each (a timestamp, a beat id, a quote).
4. **Decide**: PASS / REVISE / BLOCK (rubric). Hard fails from the gate are always BLOCK.
5. **Fix** (REVISE or BLOCK): edit the episode's `lesson.json` directly — rewrite the hook, swap a wrong metaphor,
   split a slow shot, re-time cues, smooth a clumsy sentence, refresh `meta.youtube`. Rules:
   - Facts stay true: never add an unsourced number or quote; keep `sources`/`certainty` honest.
   - Every changed narration line costs a re-voice (~5 min CPU): change narration only when it clearly improves
     the hook, the copy or the story; prefer visual fixes. For a dropped-word fail, set `"take": n+1` on that beat.
   - Lint must stay clean: `python -m vfactory.lesson lint <lesson.json>`.
6. **Rebuild** (`python -m vfactory.lesson build <lesson.json> --out <build dir> --final`; cached voice lines are
   reused) and go back to 1. At most 3 rounds; if it still fails, report exactly what blocks it.
7. **Report** `gate/review.md`: verdict, scores, what you changed and why, what you would try next for virality.

## What "good" means here
- Hook in 5 s, open loop by 15 s, re-hook every ≤ 75 s, payoff + quotable last line, an end card that asks a real question.
- Every frame passes the mute test; metaphors are correct (see rubric §4).
- Vietnamese that sounds like a warm storyteller from Hà Nội or Sài Gòn, not a translation.
- Packaging (title + thumbnail) a stranger would click, that the video then honours.

Agent: `.claude/agents/video-gatekeeper.md` runs this skill as a dedicated reviewer.
