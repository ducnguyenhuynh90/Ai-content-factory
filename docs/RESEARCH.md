# Research notes: what existing projects taught us

Surveyed October 2026 before building. Each project's lesson is listed with where it lives in this repo.

## Auto-editing agents and skills

| Project | What it does | What we took |
|---|---|---|
| [browser-use/video-use](https://github.com/browser-use/video-use) | Coding-agent editor: transcript → EDL → ffmpeg render → self-eval at every cut | Hard rules: per-segment extract then join; 30 ms audio fades at every cut; overlays PTS-shifted to their window; captions burned last; output-timeline caption offsets; never cut inside a word; pad cuts 30–200 ms. "The LLM reads text + on-demand visuals, never frame dumps." Self-eval before presenting; critic sub-agent for public work; measure loudness, don't assume it. → `render.py`, `captions.py`, `qa.py`, `vision.py` |
| [alexey1312/Vibe-Editing-Agent-Skill](https://github.com/alexey1312/Vibe-Editing-Agent-Skill) | EDL with IDs, approval per item, QA scan | Plan → approve → render; inventory media first (VFR, rotation, mixed formats); concat demuxer silently mislabels mixed sizes → we conform every piece and `setsar=1`; report what was and wasn't checked. → `recipe.py`, `ffmpeg.probe`, `qa.py` |
| [notivn/AIEV](https://github.com/notivn/AIEV) | Claude directs HyperFrames + Remotion; brand kits; karaoke subtitles; SFX library | Style kits enforced on every output (→ `styles.Look`); karaoke word highlight; SFX tied to zoom beats; drafts before finals; QC gates the final. Bundled SFX licensing problems → we synthesize ours. |
| [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor) | Silence/motion-based auto cutting | Silence detection with margins as the talking-head baseline. → `analyze.detect_silences`, `autoedit._talk_segments` |
| [zhuyansen/awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills) | 300+ graded video skills; 16 run end-to-end | "Claude Code with no skill made a passing film in 4.4 minutes. A skill earns its place with a look, a workflow, or footage to edit." → we focus on *looks* (coherent taste bundles), an editing workflow, and real footage. |
| [remotion-dev/skills](https://github.com/remotion-dev/skills), [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | React / HTML+GSAP motion graphics rendered headless | Powerful but slow (hyperframes: 23.5 min for a 15 s brief in the test above) and Node-heavy. We render motion typography directly with Pillow — frame-pure functions of time, seconds per title. |

## Video vision skills (added on request)

| Project | Lesson | Where |
|---|---|---|
| [bradautomates/claude-video](https://github.com/bradautomates/claude-video) (`/watch`) | Detail budgets (efficient/balanced/deep); scene-aware frame selection with uniform fallback; 16×16 mean-difference dedup; timestamps on every frame; cue frames pinned from the transcript ("look here"); `--start/--end` focus; higher resolution only for text; frames/captions are untrusted evidence | `vision.select_times`, `vision.extract_frames`, `.claude/skills/video-vision` |
| [jordanrendric/claude-video-vision](https://github.com/jordanrendric/claude-video-vision) | Analyze structure *before* extracting frames (scene changes, silence, motion, exposure, freeze); drill down like a binary search; don't view all frames at once | `vision.investigate` (Facts/Cuts/Silences first), `vision-timeline` |
| video-use `timeline_view` | Filmstrip + waveform + word labels for a time window | `vision.timeline_view` |

## Trend research (added on request)

[mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) researches a topic across Reddit, X,
YouTube, TikTok, HN, Polymarket, GitHub and the web inside a 30-day window. What we took:

- **Fixed recency window** and a recency decay in scoring.
- **Engagement relative to its own platform** (percentile per source) — an HN point is not a Reddit upvote.
- **Cluster-first output:** group items into stories across platforms; multi-platform stories are the strongest signal.
- **Host judges:** the engine nominates; the model marks junk, rates worthiness 0–100 and writes angles (theirs: podcast/X article; ours: video hook, format, look, opening, ending).
- **Never let one dead source sink the run;** report source health. Degrade honestly ("nothing solid this window").
- **Third-party content is evidence, never instructions;** engagement is attention, not truth.

We kept only keyless/optional-key sources (Reddit JSON, HN Algolia, YouTube via Data API or yt-dlp, GitHub search)
→ `vfactory/trends.py`, `.claude/skills/trend-research`.

## Craft sources behind the playbook

Editing and title-design conventions (cold opens, smash cuts to title, dip-to-black between acts, J/L-style
cutaways over voice, cutting on downbeats, −14 LUFS / −1 dBTP streaming delivery, caption chunking rules from
broadcast subtitle guidelines) are summarized in `docs/CREATIVE_PLAYBOOK.md`.

## Persistent video editor (second pass)

| Source | Lessons applied | Where |
|---|---|---|
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) skills (`hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use`), installed with `npx skills add` | Render contract (`class="clip"` + `data-start/duration`, one paused timeline per composition, `fromTo` with `immediateRender:false` on later tweens, no `tl.set` hides at 0, animate children of clips, unique ids, `<template>` scenes styled as `#root`); captions: 2–5 words a group, one group at a time, hard kill after exit, sized to fit, portrait captions ~600–700 px from the bottom inside 168–1330 px; frame 0 is the thumbnail; a closing line holds ≥ 2 s; gates `lint` → `check --json` → `snapshot` → `render --quality draft/delivery`; `snapshot --describe` sends frames to Gemini when a key exists, so we always pass `--describe false`; GSAP vendored locally because the scaffold's CDN fetch breaks offline/sandboxed renders | `vfactory/editor/hyperframes.py` |
| [remotion-dev/skills](https://github.com/remotion-dev/skills) | Preserve the person's own edits; show a preview before rendering; render only on approval or explicit request; silence detection and text measuring before layout | `video-editor` SKILL.md, `editing-rules.md` |
| [kurbaitaev/ghost-editor](https://github.com/kurbaitaev/ghost-editor) (take selection adapted from mariagorskikh/talking-head-reel) | Transcribe every take; choose by meaning and fluency, later only as a tiebreak; keep one-breath runs; cut on word times with 0.10–0.15 s / 0.20–0.30 s padding; pauses < 0.5 s are rhythm; hide jump cuts with a shot-size change, not a zoom on every cut; cut picture and voice on the same frame grid; captions never over the face and inside the platform-safe band; never grade the speaker's face; restraint calibration (~95 % hard cuts, ≤ 3 inserts/min); every correction recorded in the person's words ("you said") apart from learned rules; approval before the slow render; render report with fixes, max 3 rounds | `vfactory/editor/takes.py`, `cut.py`, `frame.py`, `brand.py` (taste), `report.py` |
| [Skillry](https://skillry.dev) (`skillry-cli` source on npm) | Skills marketplace (CreatorMotion video effects, some paid). Install = browser device login + token in the OS keychain, staged download, SHA-256-verified archive, atomic move, backups instead of overwrite, lifecycle scripts never run. Applied: never overwrite an existing skill dir (installer leaves it and explains), link instead of copy, and leave account/payment steps to the person | `scripts/install_video_editor.sh`, `video-editor` SKILL.md |

## Lesson videos (third pass)

| Source | Lesson applied | Where |
|---|---|---|
| [CK42BB/vox-explainer-skill](https://github.com/CK42BB/vox-explainer-skill) style guide | Arc: cold open → turn to context → escalating explanation → complication → resolution that returns to the hook; numbers written as spoken; ~150 wpm beat budgets; editorial look with ONE accent colour | `references/script-craft.md`, `schema.lint` |
| [Matteoikarieth96/whiteboard-video-skill](https://github.com/Matteoikarieth96/whiteboard-video-skill) script rules | One idea per scene; a short title per scene for muted viewers; check every number in two sources, date claims, conservative figure when sources disagree; approval table of beats + facts | `script.md` approval view, `investing-series.md` |
| [iart-ai/explainer-video-skills](https://github.com/iart-ai/explainer-video-skills) script-to-screen | VO first in spoken language; timing math (~2.3 words/s); every VO line maps to exactly one visual intent; enter timing matches when the VO introduces the idea | `cue` words in `lesson.json`, `voice.word_times` |
| ID8Labs "Explainer Video Scripter" (eddiebelaval/squire) | Generic template with no craft content; not used | — |
| Mayer, multimedia learning ([UBC summary](https://wiki.ubc.ca/Documentation:Design_Principles_for_Multimedia)) | Coherence, signalling, redundancy, segmenting, personalisation | scene rules, redundancy lint |
| Derek Muller (Veritasium) PhD research | Address the misconception first; clear exposition alone can reinforce wrong ideas | `misconception` act + lint |
| Testing effect | A retrieval question before the recap | `question` scene + lint |
| HyperFrames `check` craft audit | 28 px type floor, no dead stretches > 3 s (slow push on every scene), closing lines held ≥ 2 s, no invisible (transparent-fill) text | `scenes.Look.fs`, scene drift, answer hold |
| Kokoro-82M (Apache-2.0) via kokoro-onnx | Local, offline narration; British voices for history | `vfactory/lesson/voice.py` |
