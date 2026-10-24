# Creative playbook

The rules the factory encodes, written down so a director (you, or Claude) can
apply them on purpose and break them on purpose. Values are defaults that
shipped well, not laws — the look you pick sets most of them for you.

## 1. Structure: every film is open → build → peak → resolve → close

| Part | Job | Factory default |
|---|---|---|
| **Cold open** (0–4 s) | Earn the next 10 seconds. Start on the strongest moment: the best line, the most kinetic shot. | `cold_open`: auto-picked highest-energy line (talk) or highest-interest shot (montage) |
| **Title** (3–5 s) | Say what this is, with the confidence of a studio. | Smash cut to a title card with a hit, or title over the establishing shot |
| **Build** | Establish place, people, stakes. Longer shots. | first 20 % of shots use the look's longest beat count |
| **Peak** | Fastest cutting, most motion, the payoff. Around 60–75 % of runtime. | shot length accelerates toward ~70 % |
| **Resolve** | Breathe. One long, beautiful shot with a slow push-in. | longest shots again, calm/high-quality picks |
| **Close** | One idea, one call to action, then black. | end card: title lock-up + CTA (+ credits) → 0.4 s fade |

Never open on a logo. Never end on a hard cut to silence. The first frame and
the last frame are the two most-seen frames in the film.

## 2. Openings

- **The hook is 0.5 s, not 3 s.** Something moves, something is heard, something is read in the first half second.
- **Cold open → smash cut to black title** is the prestige grammar: momentum, then a breath. Put a low hit exactly on the title's first visible frame.
- **Title over picture** works when the first shot is strong and calm: 0.4 s after the cut, never on a busy frame without a scrim.
- **One thing at a time:** kicker → title → subtitle, staggered ~0.3–0.5 s. The eye can't read two new things at once.
- **Readable for ≥ 1.5 s** after it lands. If you can't read it at 1×, it isn't there.
- **Vertical/social:** the title is the hook — big, 2–3 words a line, lands with the first beat, captions start immediately after.

## 3. Endings

- **Decelerate into the end.** The last body shot is longer than the average and pushes in slowly; music starts resolving 2–3 s before the end card.
- **End card holds ≥ 3 s** with exactly one CTA. Credits (if any) come first, one pair at a time, ~1 s each.
- **Music fades under the end card**, not after it. Don't let the score's tail decay under black.
- **Out:** 0.4 s fade to black. No more than 1 s of black at the very end.

## 4. Typography

- **Two families, maximum.** One display face for titles, one utility face for kickers, lower thirds and captions.
- **Tracking:** spaced caps read premium (+0.10 to +0.20 em on titles, +0.3 to +0.6 em on small kickers). Lowercase display type wants tight tracking (−0.01 to −0.02 em).
- **Sizes (fraction of the frame's short side):** title 9–12 %, condensed trailer caps up to 20 %, kicker 2–2.6 %, lower-third name 3–4.2 %.
- **Captions:** 5–6.5 % of frame height; 2–3 words for social, 5–7 for documentary; break on pauses ≥ 0.3 s and sentence ends; never leave a 1–2 word orphan; never flash a cue shorter than 0.35 s.
- **Safe areas:** titles inside 84 % of width. Lower thirds at 6.5 % from the left edge. Vertical captions ~30 % from the bottom, clear of platform UI. With letterbox bars, captions sit just above the bar.
- **Contrast before decoration:** a soft radial scrim behind type over footage; dark ink only on the look's own light cards.
- **Fonts fail silently.** Load every face from an explicit path; a fallback face makes a studio title look like a slide.

| Look | Display | Utility | Why |
|---|---|---|---|
| prestige | Instrument Serif caps, wide tracking | Montserrat | Serif in open space = patience, authorship |
| editorial | Inter Display ExtraBold, tight | Inter | Swiss clarity; masked reveals feel engineered |
| blockbuster | Anton, condensed caps | Oswald | Takes the whole frame; slams on the beat |
| documentary | Space Grotesk | JetBrains Mono | Typed, factual, honest |
| luxury | Playfair Display Italic | Montserrat light, very wide | Breathes; italics feel hand-made |
| hype | Archivo Black caps | Syne | Loud, fast, built for a phone |

## 5. Motion

- **Never linear.** Reveals ease out (expo/quint) — fast start, soft landing. Exits ease in. Continuous moves ease in-out.
- **Overshoot sparingly** (`out_back`) — buttons and CTAs, not titles.
- **Blur-to-sharp + tracking convergence** reads cinematic; **mask rises** read editorial; **slams with shake** read trailer.
- **Hits:** every title animation reports the frames where something lands; sound design hits exactly there.

## 6. Picture

- **Cuts are the default** (80–90 % of transitions). A designed transition is punctuation — use it at section changes.
- **Dip to black** between acts and into the end card. **Dissolve** for time passing. **Flash/whip/zoom** only in energetic looks.
- **One grade for the whole film**, applied per shot before joining. Protect skin tones; desaturate before you push colour.
- **Texture is what makes digital look shot:** grain 3–8, subtle halation on highlights, vignette ≤ 0.35, slow push-ins of 2.5–6 % per shot.
- **Letterbox (2.39:1)** only for cinematic looks, never on vertical.
- **Light leaks:** ≤ 4 per film, at transitions or the title, never over faces mid-sentence.

## 7. Sound (half of "pro")

- Mix to **−14 LUFS integrated, true peak ≤ −1 dBTP**. Measure the delivered file — AAC can overshoot the mix.
- **Duck music ~12 dB under speech**; b-roll ambience sits ~14 dB under the score.
- **30 ms fades at every audio cut** or you will hear clicks.
- **Fewer effects:** ≤ ~8 per minute, each tied to something visible (a title landing, a whip, a lower third). Synthesized, so there are no licensing questions.
- **Cut on the downbeat:** the factory aligns a downbeat to the first body frame and cuts in whole beats.

## 8. Self-review before anyone sees it

1. `vfactory qa` — black/frozen frames, loudness, true peak, duration vs plan, contact sheet of every cut.
2. `vfactory vision FILM` — read every frame it lists; check grade consistency and title legibility.
3. `vfactory vision-timeline FILM t-1.5 t+1.5` at each cut you're unsure of — look for flashes, jumps, audio spikes.
4. Fix → re-render → re-check, at most 3 rounds. Then report what you checked and what you couldn't (you can't listen).
