# The gatekeeper's rubric

Two minds review every cut. **The retention engineer** (MrBeast's school): every second must earn the next one;
the click is won by title + thumbnail, the stay is won in the first 30 seconds, and the audience leaves at the first
moment it can predict what comes next. **The Vietnamese film director**: every picture is composed and means
something, the Vietnamese is natural and beautiful to the ear, the mood is consistent, and nothing is cheap,
careless or culturally off.

Score each axis 1–10. A cut ships only when **every axis ≥ 7 and the average ≥ 8**, with no hard fail from the gate.

## 1. Packaging: title, thumbnail, promise (does anyone click?)
- Title ≤ 60 characters, in natural Vietnamese, with a curiosity gap that the video actually pays off. Specific beats
  vague ("1.435 công ty, chỉ 11 thành vĩ đại" beats "Review sách Good to Great"). No clickbait the video doesn't deliver.
- Thumbnail = frame 0 (the hook). ≤ 5 big words, readable at 320 px wide (check `gate/thumb.jpg`), one focal point,
  strong contrast, an emotion or a tension (a number, a crash, a paradox). Not a title card, not a logo.
- Title and thumbnail say different things that complete each other (never the same words twice).
- Write/refresh `meta.youtube` = {"title", "thumbnail_text", "description" (2–3 lines + chapters), "tags"}.

## 2. Hook: the first 5–30 seconds (does anyone stay?)
- Frame 0 is the claim itself, over the picture that proves it. Speaking starts by 0.6 s. The paradox lands by ~5 s.
- The hook has: a concrete anchor (name, year, number), tension (but / yet / only / lost), and stakes for the viewer.
- By ~15 s the open loop is set: what the viewer will have by the end ("ba bài học…"), and why it matters to THEM.
- Never: "xin chào", "hôm nay chúng ta", channel intros, asking to subscribe before giving value, a slow logo.
- Test: say the first 10 seconds out loud. Would a stranger scrolling at 1 a.m. stop? If not, rewrite.

## 3. Story and value (is it worth the time?)
- One clear spine: a real person, a real moment, a turn. Specific details over summaries.
- 2–4 lessons the viewer can USE, each tied to the story and then generalised. A myth broken on camera.
- Honesty: the book's limits or critics are named (credibility is retention on a channel).
- Re-hook every 45–75 s: a question, a twist, a broken myth, a "nhưng…". (gate metric `longest_without_rehook_s`.)
- The ending pays off the hook with new meaning and leaves one quotable line; the end card asks the viewer
  something specific they want to answer in the comments.

## 4. Pictures and metaphors (does every frame say something?)
- Mute test: with the sound off, each shot alone tells you what is being said. A picture that is merely decorative,
  or the literal opposite of the line (a tea cup under "what is your flywheel?"), is a defect.
- Metaphors are correct and precise: luck = dice, momentum = flywheel, swings = pendulum, settling for good =
  climb/ledge, a myth = something struck and swapped, one-of-many = funnel, a protective buffer = shield.
- Variety: no picture type twice in a row; no frame that looks like a slide of bullet points.
- Composition: one focal point, nothing clipped, nothing overlapping, labels near what they name, safe margins.
- Look at `gate/scenes.jpg` (middle and end of every beat) and `gate/hook.jpg` (0–6 s): any glitch, blank frame,
  half-drawn element, overlap, unreadable caption → defect.

## 5. Pacing and motion (is it alive?)
- Something new happens every 2–3 s; a single picture rarely holds more than 5–6 s; no frozen screen > 3 s
  (a question's countdown excepted). Lines must stay on screen long enough to read (0.5 s + 0.3 s per word).
- Motion carries meaning (the wheel speeds up as momentum builds), never decoration loops.
- Rhythm varies: a fast run of shots, then a held beat before a payoff.

## 6. Vietnamese copy and voice (is it beautiful to the ear?)
- Natural spoken Vietnamese, not translated English. Short sentences, varied rhythm, warm "mình/bạn" voice.
  Watch for: calques ("điều đó có nghĩa là" repeated), stiff Sino-Vietnamese where a plain word is warmer, filler,
  repeated words, sentences too long to say in one breath, ambiguous pronouns, wrong register.
- Numbers said as words; English names in their original spelling and recognisable by ear (gate `names`).
- Pace 160–240 syllables/min, a real pause after a question (≥ 0.55 s), no dropped words (gate hard fail).
- On-screen text: key phrase only, correct diacritics, consistent capitalisation, no typos.

## 7. Typography and brand (is it clean and consistent?)
- Every character drawn by the bundled fonts (gate `fonts.missing` = hard fail): Vietnamese marks must not fall back.
- Hierarchy: one display line, one kicker, small labels; never more than three sizes in a frame.
- Accent colour carries meaning (the one word that matters), not decoration.

## 8. Sound
- Integrated −16 LUFS ±1, true peak < −1 dBFS; music under the voice; hits only on visible events.

## Verdicts
- **PASS** — ships. (Still list 1–3 ideas that would make the NEXT episode better.)
- **REVISE** — fix now; list every fix as a concrete edit, apply them, rebuild, re-gate.
- **BLOCK** — a hard fail (dropped words, broken glyphs, frozen screen, factual error, misleading claim) or any axis
  < 5. Must be fixed before anything else.
