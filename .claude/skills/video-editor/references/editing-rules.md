# Editing rules (why the engine does what it does)

Collected from GhostEditor (kurbaitaev/ghost-editor), HyperFrames' own skills, Remotion's skills, video-use and
Vibe-Editing, plus the person's own instructions. "Hard" rules are correctness; the rest are defaults to adapt.

## Takes
- The recording is a script read two or three times; the transcript is the map. Transcribe all of it; choose
  from the table, never by scrubbing. Cut on WORD times, never Whisper segment times.
- Pick by meaning first, then fluency (no stumble, no filler they'd cut), then clarity, pacing and audio level.
  Later takes win only ties: people warm up, but the last take is not automatically the best.
- Keep one-breath runs together (one cut instead of four). Splice from another run only for one-liners and only
  when framing and light match.
- Cut points: start = first word − 0.10…0.15 s, end = last word + 0.20…0.30 s, never past the next spoken word.
- A Whisper word lasting > 1 s hides something (a restart, a cough): look at the waveform before cutting near it.
- Lines never said never appear — not as captions, not as cards.
- Low confidence + different wording = ask the director. Same wording = just pick.

## Pauses
- Under ~0.5 s: the speaker's rhythm, keep. Over: tighten, don't erase — a breath at sentence ends (~0.45 s),
  less mid-sentence (~0.25 s), more before a short payoff or punchline (~0.6 s).
- Pace presets: tight / natural / relaxed (`ve pref pace ...`). "Auctioneer on espresso" is a failure.

## Jump cuts
- Hide with a shot-size change (alternate 100 % / ~108 %), at most on genuine jump cuts, never a zoom on every cut.
  No punch-in without resolution headroom (no upscaling past the source).
- Cut picture and voice at the same frame-snapped instants or the voice drifts (~50 ms after 20 cuts).

## Framing
- 9:16 from 16:9: static crop per segment on the median face position; eyes ~36 % from the top. No wobbly
  auto-pan. Never stretch. Never upscale more than 1.33×; deliver smaller and say "record in 4K for sharper reels".
- Captions and cards never cover the face; Reels/TikTok/Shorts text lives between 168 and 1330 px of 1920, clear of
  the right-hand action rail.

## Picture
- Measure first; correct only past thresholds; denoise before any gain; cap exposure/contrast/white balance so
  skin keeps texture. Never grade the speaker's face into a "look". Very dark or noisy footage: mild correction and
  a clear reshoot recommendation ("face a window, or one soft key light").

## Sound
- Each voice normalized on its own; music ducks under speech (sidechain) and sits ~16 dB under; effects relative
  to the voice; limit the sum. Never lift the finished mix to fix one source.
- High-pass 75 Hz; denoise only above a −55 dBFS floor and capped (~12 dB) so voices don't turn watery; de-clip
  only if clipping is detected; light compression. Deliver −14 LUFS, true peak ≤ −1 dBTP, measured on the delivered
  file (AAC can overshoot).
- 15–30 ms fades at every audio cut.

## Captions (HyperFrames)
- 2–3 words for high energy, 3–5 conversational, 4–6 calm; break at sentence ends and pauses ≥ 150 ms.
- One group visible at a time; open at the first word, hard-kill after the exit; first caption ≥ 0.1 s in.
- One emphasised word per group at most (a number, else the strongest content word). No emojis unless asked.
- Size to fit (base 78 px portrait, min 42); strong contrast (scrim sized to the text, not a full-width bar).
- HyperFrames contract: `fromTo` with `immediateRender: false` on every later tween of the same target; no
  `tl.set` at 0 for initial hides; animate children of `.clip`, never `display`/`visibility`; ids unique; fonts
  bundled or `@font-face` to a local file; GSAP vendored locally.
- Gates: `lint` → `check --json` must have 0 errors (fix warnings or justify them) → `snapshot` and LOOK →
  draft render → delivery render. Frame 0 is the thumbnail: never empty. A closing line holds ≥ 2 s.

## Restraint (calibration from GhostEditor's audit of top reels)
- ~95 % of transitions are hard cuts; median shot ~3 s; B-roll 20–35 % of runtime; ≤ 3 inserts a minute on
  talking heads; audible SFX on graphics, not on cuts. Default to less.

## Process (from Remotion & HyperFrames)
- Preserve the person's own edits made outside the conversation; never overwrite them silently.
- Preview before final render; render the final only when the person approves or asked for no stops.
- Every correction the person makes is taste: record it in their words; your own learned rules are marked as yours.
