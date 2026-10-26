# AI Content Factory

`vfactory` turns raw footage into a studio-grade edit (Python + ffmpeg + Pillow, no other deps).

- Editing a video → use the `video-factory` skill (`.claude/skills/video-factory/SKILL.md`).
- Looking at / reviewing any video → `video-vision` skill. Never describe a video you haven't looked at.
- "What should we make a video about / what's trending" → `trend-research` skill.
- Editing the person's own recordings (retakes, pauses, captions, platform export) → `video-editor` skill.
- A lesson / explainer / "lessons from history" video on any topic → `lesson-video` skill
  (`python -m vfactory.lesson`; example: `lessons/investing/001-newton-south-sea-bubble`).
- A video made from code, not footage (listicle, explainer, 3D intro, motion graphics) → `motion-stack` skill
  (choose between Remotion, Motion Canvas, GSAP, three.js, FFmpeg ... and make the animation exportable).
- Taste rules live in `docs/CREATIVE_PLAYBOOK.md`; read it before directing.
- Run `python -m pytest -q` after changing engine code; `python -m vfactory demo --preview` for an end-to-end check.
- Outputs belong next to the user's footage, never inside this repo.
