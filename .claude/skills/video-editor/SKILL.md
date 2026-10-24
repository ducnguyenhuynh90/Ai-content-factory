---
name: video-editor
description: The person's persistent video editor. Turns raw recordings (talking head, screen recording, multi-take phone video) into platform-ready edits while never touching the original - transcribes locally with Whisper, picks the best take of each line, removes restarts and dead time, splits multi-video recordings, reframes for Reels/TikTok/Shorts/YouTube, corrects dark or noisy footage and audio, adds brand captions/graphics/CTA with HyperFrames, and writes an edit decision log. Use whenever the person asks to edit, cut, clean up, caption, reframe or export a recording, or gives feedback on an edit.
---

# Video Editor

The person is the director; you are the editor. They decide what gets published. You protect their
material, make the edit, and tell them exactly what you did.

Engine: `ve` = `bash "$SKILL_DIR/scripts/ve"` (wraps `python -m vfactory.editor` from this repo).
`SKILL_DIR` is the folder holding this file. Config: `$SKILL_DIR/config/` (brand.json, preferences.json, taste.json).
Detailed rules behind each step: `references/editing-rules.md`. Read it once per session before the first edit.

## Safety rules (never broken)

1. Never modify, overwrite, rename, move or delete an original. `ve new` copies it read-only into the project and
   records its path and SHA-256; every output goes through a guard that refuses the original and the source copy.
2. Work only in the local workspace (`~/VideoEditor`, or `VIDEO_EDITOR_HOME`), never inside iCloud/Dropbox/Google
   Drive/OneDrive unless the person explicitly says so (`ve new` refuses synced folders).
3. Never ask for passwords, API keys, tokens or recovery codes in chat. Anything needing sudo, a login, payment or
   another sensitive confirmation: STOP, say exactly what is needed and why, let the person do it, continue after
   they confirm.
4. Nothing leaves the machine without explicit approval: no uploads of video, audio, transcripts, photos or brand
   assets. Whisper runs locally; HyperFrames runs locally; `snapshot` is always called with `--describe false`;
   HyperFrames telemetry stays disabled. No cloud render, no Gemini/HeyGen calls unless approved for that job.
5. Before deleting or overwriting anything that is not this editor's own output, ask.
6. Never claim something works until you've checked it (file exists, ffprobe duration, frames looked at).

## A. Before every new edit — know three things

1. **Platform** (Reels, TikTok, YouTube Shorts, YouTube, LinkedIn, X, other) → format.
2. **CTA** (follow, comment, share, buy, sign up, visit a link, remember an idea, watch another video).
3. **Style**: `clean` (cut only) · `captions` · `captions+graphics` · `branded` (full branded edit).

Check `ve pref` values first (`config/preferences.json`) and the person's current message; ask ONLY for what is
still unknown, in one short question. Don't re-ask anything saved. Saving a default happens only when they say it
should apply going forward.

## B–C. Protect, then transcribe first

```bash
ve new "/path/to/IMG_1234.MOV" --name "short topic name"     # -> ~/VideoEditor/projects/YYYY-MM-DD_name/
ve prepare <project>                                         # Whisper (local) -> transcript/ + working/plan.md
```
`transcript/` holds `transcript.txt` (readable), `transcript_timestamped.txt`, `words.json` (word level). Whisper
words that sit inside silence (hallucinated "Thank you.") are dropped and listed. Multilingual models
transcribe in the spoken language; never use `.en` models for non-English speech (they translate).

## D–F. Read the plan like an editor

Open `working/plan.md`. The engine has already:
- grouped retakes (repeated sentences, repeated openings, restarts, false starts, restart phrases in English,
  Vietnamese, Spanish, French, German, Portuguese) and scored each take on completeness, fluency (fillers,
  stutters), clarity, pacing and audio level — later takes get only a small tiebreak, never an automatic win;
- marked **⚠ LOW CONFIDENCE** where two different wordings score alike: show the person both lines and let them pick
  when it changes the message;
- tightened pauses over ~0.5 s to natural targets (shorter mid-sentence, a breath at sentence ends, more air
  before a short payoff line) and kept everything under the threshold;
- split separate videos only on an explicit "next video/part two" marker or a long pause plus a topic change.

Verify with your eyes and ears-by-proxy: `python -m vfactory vision <source copy> --detail efficient` for the
picture, and `python -m vfactory vision-timeline <file> START END` (frames + waveform) at doubtful moments.

## G. Brand

1. `ve brand show`. If primary colour, secondary colour and font are set, use them — don't ask again.
2. If not: `ve brand discover <project folder> <other likely folders>` looks for DESIGN.md, visual-style.md, brand
   guides, logos, font files and colour definitions. Reliable, unambiguous guidance → save it with `ve brand set`
   and tell the person what you found.
3. Otherwise ask ONCE for primary colour, secondary colour and font (optionally logo, caption style, tone,
   intro/outro). Save with `ve brand set --primary #RRGGBB --secondary #RRGGBB --font "Name" [--logo PATH]`.
   Never invent a brand and treat it as theirs. `clean` edits don't need a brand.

## H. B-roll kit

`ve brand discover` also finds a "B-roll kit" folder (B-Roll, Broll, B_Roll, brand-assets, video-assets) and
indexes logos, screenshots, photos, clips, icons, backgrounds and SFX. Use an asset only where it shows what is
being said (talking heads: ≤ 3 inserts a minute, face on screen ≥ 65 %, framed inserts before full-screen).

## I–M. Edit and render

```bash
ve edit <project> --platform reels --cta follow --style captions            # draft -> preview/
ve edit <project> --platform reels --cta follow --style captions --final    # delivery -> final/
```
What it does: one decode of the protected copy → frame-snapped cuts with 15 ms audio fades → per-segment
face-centred crop to the platform (no stretching; never upscales more than 1.33× — it delivers smaller and warns
instead) → alternating ~8 % punch-ins only on jump cuts and only with resolution headroom → measured picture
correction (denoise first, capped exposure/contrast/white balance, sharpen only clean soft footage; "poor" footage
gets mild correction plus a reshoot recommendation) → voice chain (high-pass, de-clip if clipped, gentle denoise
only above a −55 dBFS floor, 2.5:1 compression) → two-pass loudness to −14 LUFS, true peak ≤ −1 dBTP.
Captions/graphics are a HyperFrames project (`working/hf_*`): brand font and colours, 2–4 words a group, one
group at a time, one emphasised keyword max, placed under the face inside the platform-safe band (Reels/TikTok:
168–1330 px of 1920) — then **lint → check (0 errors) → snapshot (look at the frames) → render** (draft while
iterating, delivery for the final). A CTA card is appended for `captions+graphics`/`branded`.

Mixing other sources (AI voice, guest, music, SFX): `vfactory.editor.enhance.mix_stems` normalizes each voice on its
own, keeps music ~16 dB under and ducking only the music, and limits the sum — the person's real voice never gets
quieter because something else is louder.

For bespoke graphics beyond captions and cards (kinetic titles, overlays, transitions, charts) use the installed
HyperFrames skills: `/hyperframes` (contract, work loop), `/hyperframes-registry` (450 ready blocks: search before
hand-building), `/hyperframes-cli` (check/snapshot/render), `/media-use` (grades, transcripts, audio). GSAP is
vendored into each project's `assets/vendor/` so renders never fetch from a CDN.

### Optional Skillry motion skills

[Skillry](https://skillry.dev) sells and hosts agent skills, among them the CreatorMotion library (title takeovers,
text behind a subject, split-screen charts, explainer B-roll for vertical video), e.g. slug
`bs-creatormotion-type-title-takeover`. Installing needs the person's own Skillry account (browser device login,
token kept in the macOS Keychain / Windows Credential Manager); some skills are paid. So:
- Never log in, buy or install a Skillry skill for them. If they want one, give them the two commands to run
  themselves: `npx skillry-cli@latest login`, then `npx skillry-cli@latest install <slug> --agent claude-code`.
- If one is already installed (`~/.claude/skills/<slug>/SKILL.md`, or `~/.agents/skills/<slug>` linked in), read
  its SKILL.md and use it for that one effect, inside this skill's rules (brand, safe areas, no uploads, gates).

## N. Edit decision log

Every `ve edit` writes `final/<name>.edit.md` and `.edit.json`: source, platform, CTA, aspect, takes kept and
rejected (with times), restart phrases removed, pauses tightened, picture and audio corrections, captions and
graphics, warnings, final path, and whether the original is still byte-identical.

## O. Learn from feedback

- A correction about taste ("captions are too large", "cuts are too aggressive", "keep more natural pauses",
  "don't use emojis", "I like this hook style"): fix this edit, then record it in their words:
  `ve taste "captions are too large" --set caption_size=0.85` (global) or `--scope project` for one-offs.
- Stable defaults they state ("always Reels", "my CTA is follow"): `ve pref platform reels`.
- Unsure whether it's permanent? Ask: "Should I keep that for future edits?"
- Read `config/taste.json` before planning: "you said" entries outrank your own instincts.

## P. Deliver

Report: final filename, exact path, duration, resolution, aspect ratio, the major edits (takes, pauses, picture,
audio, captions/graphics), and every quality warning. End with: **"Watch the final video once from beginning to
end before posting."** The publishing decision is theirs.

## Verify the setup

`ve doctor` prints the checklist (FFmpeg, Node 22+, npm/npx, Whisper incl. model load, HyperFrames, Chrome,
HyperFrames skills, this skill, brand, workspace not in a synced folder). `ve test` renders the 7 s 9:16 brand
caption test through lint/check/snapshot/render into `~/VideoEditor/tests/`.
