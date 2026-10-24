---
name: lesson-video
description: Research, write and produce a narrated, animated lesson video (default 4:3, 3-5 minutes) that teaches a topic through a true story - a moment in history or a real person's decision - and leaves the viewer with 2-4 principles they can use. Writes the script with learning-science rules (misconception first, one idea per scene, a retrieval question, recap), fact-checks with sources, voices it locally (Kokoro TTS), animates it with HyperFrames (charts, timelines, quotes, principles) and renders it. Use when the person wants an educational, explainer, history, biography or "lessons from" video, a course episode, or a series on a subject such as investing.
---

# Lesson video

A lesson video is a story that leaves a principle behind. The viewer should finish it able to say the
principle in their own words and recognise it in their own life. Read `references/script-craft.md`
before writing; for investing read `references/investing-series.md` too.

Engine: `python -m vfactory.lesson` (repo root on PYTHONPATH). Scenes render with HyperFrames; narration is
local Kokoro TTS; music is synthesized. Nothing is uploaded.

## Workflow

1. **Brief** (ask only what's missing): topic and angle (`history` = a moment, `person` = a real investor's
   decision, `concept` = an idea told through cases); audience level; length (3-5 min default); aspect (4:3
   default; 16:9 YouTube, 9:16 shorts cut-down); series name; next episode. Brand comes from the video-editor
   config.
2. **Three storylines, in words only** (HyperFrames' story rule): three different films for the same lesson
   (e.g. "the genius who lost", "the crowd's view", "the man who sold at the top"). The person picks, unless they
   asked for no stops; then pick the one with the strongest misconception and the clearest turn.
3. **Research facts.** Every number, date, quote and claim needs a source; prefer primary sources (papers,
   letters, filings, the person's own writing). Two independent sources for anything central. Mark each beat's
   `certainty`: `established`, `estimate`, `disputed` or `attributed`, and SAY the uncertainty in narration
   ("about", "historians estimate", "it's attributed to him"). Popular myths are gifts: correct them on camera.
   If a site can't be reached, say so and use what can be cross-checked; never invent a figure.
4. **Write `lesson.json`** (`python -m vfactory.lesson new lessons/<series>/<nnn-slug> --title ...` scaffolds it;
   schema in `vfactory/lesson/schema.py`). Follow the beat arc in `references/script-craft.md`.
5. **Lint**: `python -m vfactory.lesson lint <lesson.json>`. Fix every error; treat warnings as notes from an
   editor. It writes `script.md`, the approval view (beats, principles, sources). Show it to the person and
   wait for approval or edits unless they asked for no stops.
6. **Build**: `python -m vfactory.lesson build <lesson.json> [--out DIR]` (draft render) → voice per beat, timing
   from real audio length, scenes, mix, `hyperframes check` (must be clean), snapshots, render.
   Look at `build/hf/.hyperframes/artifacts/snapshots/*/contact-sheet-*.jpg`, then at frames decoded from the
   MP4 near the end of every scene (`python -m vfactory vision <mp4> --detail balanced`). Fix and rebuild.
7. **Final**: `--final` for delivery quality. Report path, duration, resolution, LUFS, the sources list and
   any claims marked estimate/disputed/attributed.

## Scene types (visual.type)

`title` · `statement` (key phrase, highlighted words underline on cue) · `stat` (number counts on its cue word)
· `chart` (line draws itself; annotations land on their cue words) · `timeline` · `quote` (`attribution:
"attributed"` shows an ATTRIBUTED · NOT VERIFIED badge) · `portrait` (engraved medallion with initials — never a
generated likeness of a real person) · `principle` · `compare` · `list` (recap with checks) · `question` (pause
and think, countdown, answer) · `end` (next episode, CTA, sources, disclaimer).
`cue` fields name a word in that beat's narration; the visual lands when the word is spoken.

## Hard rules

- No invented facts, quotes or numbers. Uncertainty is spoken, not hidden in a footnote.
- No generated faces or voices imitating real people; a portrait is a typographic medallion.
- Investing lessons teach principles, never tips: no tickers to buy, no predictions, no "guaranteed". Every
  investing video carries the disclaimer (the linter enforces it).
- On-screen text is the key phrase, not the narration (redundancy principle); minimum 28 px at 1080.
- HyperFrames gates must pass clean (lint, layout, contrast, craft) before the final render.
