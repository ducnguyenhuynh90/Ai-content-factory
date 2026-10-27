# AI Content Factory

`vfactory` turns raw footage into a studio-grade edit (Python + ffmpeg + Pillow, no other deps).

- Editing a video → use the `video-factory` skill (`.claude/skills/video-factory/SKILL.md`).
- Looking at / reviewing any video → `video-vision` skill. Never describe a video you haven't looked at.
- "What should we make a video about / what's trending" → `trend-research` skill.
- Editing the person's own recordings (retakes, pauses, captions, platform export) → `video-editor` skill.
- A lesson / explainer / "lessons from history" video on any topic → `lesson-video` skill
  (`python -m vfactory.lesson`; example: `lessons/investing/001-newton-south-sea-bubble`).
- Taste rules live in `docs/CREATIVE_PLAYBOOK.md`; read it before directing.
- Run `python -m pytest -q` after changing engine code; `python -m vfactory demo --preview` for an end-to-end check.
- Outputs belong next to the user's footage, never inside this repo.
- **No video is delivered before it passes the gate**: run the `video-gatekeeper` agent/skill after every build
  (`python -m vfactory.lesson gate <lesson.json> --out <build dir>`); it reviews, fixes and rebuilds until PASS.
