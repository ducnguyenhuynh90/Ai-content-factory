# AI Content Factory — `vfactory`

Raw footage in, studio-grade film out: a cold open, a kinetic title sequence, beat-synced cutting,
b-roll cutaways over voice, a film grade with grain/halation/letterbox, lower thirds, karaoke captions,
designed sound effects, ducked music mastered to −14 LUFS, and an end card with credits and a CTA.

It is built to be **directed by Claude Code** (three skills in `.claude/skills/`) and to run on nothing but
`ffmpeg`, `numpy` and `Pillow`.

```
footage/ ──analyze──▶ analysis.md ──direct──▶ recipe.json ──render──▶ final.mp4 ──qa/vision──▶ contact sheet, report
            (shots, speech,      (auto-director's       (cuts, titles,        (black frames, LUFS,
             music beats)         first cut; edit it)    grade, mix)           true peak, every cut)
```

## Quick start

```bash
pip install -e .            # needs ffmpeg/ffprobe on PATH (with libass for captions)
python -m vfactory looks    # the six looks

# no footage? synthetic clips + voice + music -> finished films
python -m vfactory demo --look prestige --mode montage,talk --preview

# your footage
python -m vfactory auto ./footage --look prestige --title "The Long Road Home" \
    --kicker "A Northlight Film" --cta "Watch the film" --handle northlight.studio \
    --music ./score.mp3 --credit "Directed by=Mai Tran"
```

Step by step (what the `video-factory` skill does):

```bash
python -m vfactory analyze ./footage --music score.mp3          # -> footage/edit/analysis.md
python -m vfactory direct  ./footage --look editorial --title "Launch" --aspect 9:16
#   edit footage/edit/recipe_editorial.json: story order, cold open, title copy, cutaways...
python -m vfactory render  ./footage/edit/recipe_editorial.json --preview   # fast half-res + QA
python -m vfactory vision  ./footage/final_editorial_9x16_preview.mp4       # look at it
python -m vfactory render  ./footage/edit/recipe_editorial.json             # final
```

## Looks

Each look is one coherent set of taste decisions — type, palette, grade, texture, transitions, pacing,
title motion, opening/ending grammar, captions and sound — so nothing feels templated.

| Look | Title motion | Type | Picture | Cutting |
|---|---|---|---|---|
| `prestige` | letters converge from wide tracking, blur→sharp, hairline | Instrument Serif caps | warm film stock, halation, grain, 2.39:1 | patient; cuts + dissolves; dip between acts |
| `editorial` | accent bar wipe, words rise from behind a mask | Inter Display ExtraBold | clean neutral punch | crisp; smooth slides at sections |
| `blockbuster` | words slam on the beat with shake + flash | Anton condensed | teal-orange, contrast, 2.39:1, light leaks | fast; flashes, whips, risers into hits |
| `documentary` | mono kicker + typed title with block cursor | Space Grotesk / JetBrains Mono | honest, slightly desaturated | observational; dissolves |
| `luxury` | italic serif breathes in word by word over a gold rule | Playfair Display Italic | creamy bloom, gold | slow dissolves, light leaks |
| `hype` | heavy caps slam, karaoke captions | Archivo Black | saturated punch | very fast; zooms and whips |

Override anything per film: `"look_overrides": {"grain": 0, "letterbox": null, "palette": {"accent": "#FF3366"}}`.

## Claude Code skills

| Skill | Use |
|---|---|
| `.claude/skills/video-factory` | Creative-director workflow: inventory → look → first cut → direct the recipe → preview → self-review → final |
| `.claude/skills/video-vision` | Let Claude *see* a video: structure first (cuts, silences, motion, exposure, loudness), then a budgeted set of timestamped scene-aware frames, a filmstrip, and filmstrip+waveform drill-downs (`vision`, `vision-timeline`) |
| `.claude/skills/lesson-video` | Research → script (lint enforces misconception-first, retrieval question, recap, sourced facts, spoken uncertainty) → local voice → HyperFrames scenes → render |
| `.claude/skills/video-editor` | Your persistent editor for raw recordings: protected originals, Whisper transcript, retakes, pauses, reframing, brand captions, edit log |
| `.claude/skills/trend-research` | What's trending in the last N days across Reddit, Hacker News, YouTube and GitHub → stories clustered across platforms → Claude judges and writes video concepts (hook, format, look, opening, ending) |

```bash
python -m vfactory vision film.mp4 --detail balanced --cues 0:04,0:31
python -m vfactory vision-timeline film.mp4 12.0 16.0 --words words.json
python -m vfactory trends "ai video editing" --days 30 --subreddit editors
```

## What makes it look "produced"

- **Opening:** strongest moment first (cold open), smash cut to a black title card with a sub hit on the frame the
  title lands — or the title over a calm establishing shot with a soft scrim.
- **Typography:** two families max, generous tracking on caps, sizes as fractions of the frame, safe areas,
  explicit font files (bundled OFL fonts — never a silent fallback face).
- **Motion:** every animation eases (expo/quint/cubic), one element at a time, and reports its hit frames.
- **Picture:** one grade for all shots, slow push-ins, grain, halation, vignette, letterbox — applied per shot
  before joining; designed transitions only at section changes, cuts everywhere else.
- **Sound:** music ducked under speech, b-roll ambience under the score, cuts on the downbeat,
  ≤ ~8 synthesized effects per minute each tied to something visible, two-pass loudnorm to −14 LUFS,
  true peak verified *after* AAC encoding.
- **Ending:** decelerate, credits one at a time, title lock-up + one CTA, fade to black.

Full rules: [`docs/CREATIVE_PLAYBOOK.md`](docs/CREATIVE_PLAYBOOK.md). What we learned from other projects:
[`docs/RESEARCH.md`](docs/RESEARCH.md).

## Lesson videos (`python -m vfactory.lesson`)

Story-driven 3–5 minute lessons (4:3 by default) on any topic, written with learning-science rules and fact
sources, narrated locally with Kokoro TTS and animated with HyperFrames (charts that draw themselves, timelines,
quotes with "attributed" badges, principles, a pause-and-think question, recap, end card).

```bash
pip install -e .[lesson]
python -m vfactory.lesson lint  lessons/investing/001-newton-south-sea-bubble/lesson.json   # -> script.md for approval
python -m vfactory.lesson build lessons/investing/001-newton-south-sea-bubble/lesson.json --final
```

Craft rules: `.claude/skills/lesson-video/references/script-craft.md`; investing series bible:
`.claude/skills/lesson-video/references/investing-series.md`.

## Captions

Pass word timings (any word-level ASR: ElevenLabs Scribe, Deepgram, WhisperX, faster-whisper) in source time:
`[{"source": "A", "word": "Hello", "start": 1.2, "end": 1.48}]`, or set `"captions": {"transcribe": true}` with
`pip install -e .[transcribe]`. The engine maps them through every cut and speed change to the output timeline.

## Layout

```
vfactory/
  analyze.py     silences, speech, shots, per-moment interest, music bpm/downbeats/drop
  autoedit.py    heuristic auto-director -> recipe (structure, pacing curve, cutaways, cold open)
  recipe.py      the recipe schema + validation
  render.py      pieces -> join (concat/xfade) -> overlays -> finishing -> mix -> verify
  motion/        Pillow motion engine: titles (5 animations), lower thirds, end cards, light leaks
  captions.py    word mapping, chunking, karaoke ASS
  audio.py       synthesized SFX (whoosh/hit/riser/tick), ducking mix, two-pass loudnorm
  qa.py          black/freeze/loudness/duration checks + contact sheet of every cut
  vision.py      video investigation for Claude (report + frames + filmstrip + timeline)
  trends.py      multi-source trend research (last N days)
  styles.py      the looks
  assets/fonts/  OFL fonts with licenses
tests/           unit tests + an end-to-end render smoke test
```

## Tests

```bash
python -m pytest -q
```
