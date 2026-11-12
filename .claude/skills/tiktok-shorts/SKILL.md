---
name: tiktok-shorts
description: Run a faceless TikTok / Reels / Shorts channel end to end - channel bible, trend-backed ideas, fact-checked 25-60 s scripts with a 3-second hook, AI voice (Vietnamese or English), animated 9:16 video with karaoke captions, cover + caption + hashtags + posting checklist, then TikTok Studio analytics fed back into the next scripts. Use when the person wants TikTok/short-form videos, a content calendar or batch of shorts, a "faceless channel", an AI content agent for short video, or wants to know which of their shorts worked and why.
---

# TikTok shorts agent

One person, one studio: research → script → voice → animate → publish kit → analytics → learnings.
Engine: `python -m vfactory.shorts` (repo root). Rules of the craft: `references/tiktok-playbook.md` — read it before
writing any script. Talk to the person in their language (Vietnamese by default for `lang: vi` channels).

## 0. The channel (once)

A channel is a folder OUTSIDE this repo (default `~/TikTokChannels/<name>`):
`python -m vfactory.shorts init ~/TikTokChannels/<name> --name "..." --niche "..." --lang vi --handle @x`.
Fill `channel.json` with the person: niche, audience, promise (one sentence), 3 pillars, voice, theme
(`night` | `paper` | `neon`), base hashtags, series name, CTA, posting slots, avoid-topics, disclaimer.
Ask only what's missing; never invent their handle or brand.

**Before every new script read** `channel.json`, `learnings.md` and (if present) `insights.md`. Learnings beat taste.

## 1. Ideas (grounded, not guessed)

- Run the `trend-research` skill for the niche (last 30 days). Add web searches for TikTok specifically:
  TikTok Creative Center trending hashtags/songs for the person's region, `"<topic>" site:tiktok.com`, Google Trends.
  Say which sources were live. Engagement is attention, not truth.
- Evergreen beats trend for explainers: a trend is a doorway into an evergreen story ("everyone's talking about X —
  it happened before in 1720").
- Write 5 concepts into `ideas.md`, each: working title, pillar, format, hook (≤ 12 words), the one picture that carries
  it, why now (evidence), fact risk (low/med/high), series potential. Score 1-5 on hook, picture, share-worthiness,
  checkability; propose the top 1-3.

## 2. Research the facts

Every number, date, quote and claim gets a source in `sources`; two independent sources for anything central; prefer
primary/academic. Mark beats `certainty: estimate | disputed | attributed` and SAY it ("khoảng", "ước tính",
"được cho là", "theo sử gia…"). Myths are gifts: correct them on camera. If a site can't be reached, say so; never fill
a gap with a plausible number. No real person's generated face or cloned voice — a real person is played by an emoji
character or named in text.

## 3. Write the short

`python -m vfactory.shorts new <channel> --title "..."` scaffolds `shorts/NNN-slug/short.json` with channel defaults.

1. **Hook first** (playbook §1): write 3 hooks of different `hook_type`, ≤ 12 words / ≤ 3 s spoken, each with a
   concrete anchor (name, number, year) and a turn. Pick the one whose frame 0 can SHOW it. `beats[0]` is
   `visual.type: "hook"`: line 1 is on screen at frame 0, line 2 slams in on `punch_cue`.
2. **Open the loop** in beat 2: why the viewer should stay ("a mistake you're probably making too").
3. **Escalate** in 2-4 s beats, each a new picture: `stat` (number lands on its word), `picture` (a familiar 3D
   emoji object acting the idea out: grow, fall, shake, bounce; `count` for crowds), `text`, `compare`, `image`/`clip`
   (the person's own media or images they generated and may use), `list`.
4. **Re-hook** around the middle with a twist or the number everyone gets wrong.
5. **Payoff**, then optionally a `question` (3 choices, countdown, answer) to drive comments.
6. **End** (`end` card): the last line loops back to the hook or teases part 2; ONE CTA.
7. Fill `meta`: `format`, `hook_type`, `pillar` (analytics groups by them), `caption` (context + a question that
   invites comments), 3-6 `hashtags`, `cover_text` (3-5 words), `disclaimer` for finance/health.

Field reference: `vfactory/shorts/schema.py` (VISUALS) and the worked example
`shorts/examples/001-newton-bong-bong/short.json`. Picture names come from Fluent Emoji 3D:
`python -c "from vfactory.lesson import assets; print(assets.search('balloon'))"`.

## 4. Lint and approve

`python -m vfactory.shorts lint <short.json>` → `script.md`. Fix every ERROR; treat warnings as an editor's notes.
Show the person `script.md` (hook, beats, caption, sources) and wait for approval unless they said "no stops".
For a batch, show all scripts in one message and take edits per number.

## 5. Build, look, fix

- Draft: `python -m vfactory.shorts build <short.json>` (540x960, fast). Voice: `meta.voice` = an edge-tts voice
  (`vi-VN-NamMinhNeural` male, `vi-VN-HoaiMyNeural` female; needs internet + `pip install edge-tts`; the TEXT is sent to
  Microsoft's TTS service), `kokoro:<voice>` (offline, English), a beat-level `"audio": "my_take.wav"` (the person's own
  voice — usually the best-performing option), or `--voice none` (music + captions only).
- **Look at it** before saying anything about it (`video-vision` skill, or decode frames near the end of every scene):
  text inside the safe area, nothing hidden by the right rail / bottom caption area, every number landing on its word,
  no empty scene, captions readable. Fix the JSON and rebuild (voice is cached; only pictures re-render).
- Final: `--final` (1080x1920, 30 fps, H.264, −14 LUFS). Also writes `*_nomusic.mp4` for adding a trending sound in-app
  and `*_frame0.png` (what the feed shows first). Batch: `python -m vfactory.shorts batch <channel> --final --only-new`.

## 6. Publish kit

`python -m vfactory.shorts package <short.json>` → `publish/cover.jpg`, `post.md` (caption, hashtags, pinned sources
comment, checklist incl. the AI-generated content label), `post.json`. The person posts (we never post for them or
touch their account). Then: `python -m vfactory.shorts log-post <short.json> --url <tiktok link>`.

## 7. Learn

After 48-72 h (and again at 7 days): the person exports TikTok Studio → Analytics as CSV;
`python -m vfactory.shorts metrics import <channel> <file.csv>` (or `metrics add <channel> <slug> --views ... --avg-watch-s ...`),
then `python -m vfactory.shorts insights <channel>` → `insights.md` + new lines in `learnings.md`.
Read them with the person: rank on watched %, shares/1k, follows/1k — not views. Turn each finding into a concrete
change for the next 3-5 videos (a hook type to try, a length, a pillar to drop) and write it to `learnings.md`.
Small samples lie: call it a hypothesis until it repeats.

## Hard rules

- No invented facts, quotes, numbers, testimonials or earnings claims. Uncertainty is spoken.
- No impersonation: no generated likeness or cloned voice of a real person; no fake news-anchor framing.
- Label AI-generated content when posting; respect TikTok's community guidelines and the person's local law.
- Finance/health: principles and stories, never tips or diagnoses; disclaimer on the end card and in the caption.
- Originality over volume: TikTok limits unoriginal, mass-duplicated content. Every short needs its own research,
  its own hook and its own pictures — templates are for structure, not for copy-paste.
- Outputs live in the channel folder, never inside this repo.
