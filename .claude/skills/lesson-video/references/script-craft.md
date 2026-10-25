# Script craft for lessons that stick

Synthesised from: the Vox-style explainer guide (vox-explainer-skill), the whiteboard-video skill's
script rules, iart-ai's script-to-screen workflow, Mayer's multimedia learning principles, Derek Muller's
(Veritasium) misconception research, the testing effect, and classic story structure (And-But-Therefore,
the Story Spine). The linter enforces the parts marked (lint).

## 0. The first five seconds (lint enforces the starred rules)

The click came from the title and thumbnail; the hook's only job is to make leaving feel like a loss.
Learned from the hook-writing skill (thecraighewitt/skills) and HyperFrames' "first second" guidance.

1. **Frame 0 is the thumbnail and the hook (\*).** Never a title card or a logo. Open on the claim already on screen
   over the data that proves it (`visual.type: "hook"`). The branded title card comes AFTER the hook and open loop,
   as a 3-second silent sting with a sound accent.
2. **Paradox + specific + stakes in under ~5 s (\*, ≤ 16 words).** Context lean-in → scroll-stop.
   "Isaac Newton explained gravity. Then, in seventeen twenty, he lost a fortune to it." Lint wants a turn word
   (then/but/lost/never/why...) and a concrete anchor (a name, a year, a number).
3. **One hook, three channels.** Spoken words, picture and on-screen text say the same thing at the same moment:
   the line crashes, the orange line slams in and the sound hit lands ON the cue word ("lost").
4. **Open the loop in beat 2 (\*).** Snapback: why this matters to the viewer, and what they'll have by the end.
   "Not to fraud. Not to bad luck. To a mistake you have probably made yourself. In the next four minutes, you'll see
   how it happened, and three rules that stop it."
5. **Speak at once.** The hook's narration starts at 0.1 s (`lead`); music is present from frame 0.
6. **Re-hook every 2-3 minutes** with a new question or a myth about to be broken ("The number everyone quotes is wrong.").
7. **Never:** "Today we'll talk about", introductions, recapping the title, asking to follow before the payoff.
8. **Test it.** Compare the first 30 seconds of the retention curve between versions (YouTube Studio → Engagement);
   a steep early drop means the hook doesn't deliver what the title/thumbnail promised.

## 1. The arc (4-5 minutes ≈ 18-22 beats, ~600 words at ~145 wpm)

| Act | Beats | Job |
|---|---|---|
| **Hook** (lint: first) | 1 | Section 0: paradox + specific + stakes, ≤ ~5 s, frame 0 composed. |
| **Open loop** | 1 | What it costs the viewer and what they'll have by the end. Then the 3 s title sting. |
| **Misconception** (lint) | 1 | Name the wrong belief the viewer probably holds ("bubbles only catch fools"). Muller: confronting it roughly doubled learning vs. clear exposition, which can even *reinforce* the error. |
| **Context: the turn** | 2-3 | "To understand what happened, you have to go back to…" Who, where, what was at stake. One person to follow. |
| **Escalation** | 4-6 | The story step by step, each beat a little more surprising. Numbers, named specifics, a chart. AND… AND… |
| **Complication** | 1-2 | BUT: the cost, the reversal, the irony. This is where the principle is born. |
| **Truth vs. legend** | 0-1 | When the popular version is wrong, show both. It teaches source-thinking. |
| **Principles** | 2-4 (lint) | THEREFORE: one beat per principle, shown as a picture (§3b): name it in ≤ 6 words, then tie it to the story in one sentence, then generalise in one sentence. |
| **Bridge / second case** | 0-1 | A later figure who solved the problem (e.g. Graham after Newton). Transfer needs a second example. |
| **Retrieval question** (lint) | 1 | Pause and think: a new situation, 3 choices, 4-6 s countdown, then the answer. Testing beats re-reading. |
| **Recap** (lint) | 1 | The principles again, in the same words. |
| **Close** | 1 | Return to the hook with new meaning; the last line should be quotable. |
| **End card** | 1 | Next episode (open loop), CTA, sources, disclaimer. |

Other skeletons that fit the same beats: **Story Spine** (Once upon a time… every day… until one day… because of
that… until finally… ever since…) for biographies; **And-But-Therefore** for every paragraph.

## 2. Sentence rules (narration is for the ear)

- One idea per beat; ≤ 70 words per beat (lint), 25-45 is the sweet spot.
- Present or simple past, active voice, concrete nouns. Vary rhythm: a long sentence, then three words. It lands.
- Numbers as spoken words: "seventeen twenty", "a thousand pounds" (lint flags digits). Put the digits on screen.
- Name sources in the narration when it matters: "historian Andrew Odlyzko, rebuilding his accounts…".
- Uncertainty out loud (lint): "about", "estimates", "is said to", "attributed".
- Personalisation: "you" sparingly and deliberately ("Now test yourself.").
- Read every beat aloud. If you stumble, the TTS will too. Add tricky names to `pronounce`.

## 3. Screen rules (Mayer)

- **Coherence:** nothing decorative that doesn't carry the idea.
- **Signalling:** reveal the element on the word that introduces it (`cue`); highlight one phrase, not five.
- **Redundancy:** on-screen text = the key phrase or number, never the sentence being spoken (lint).
- **Segmenting:** one scene per idea; the progress bar and series rail show where we are.
- **Contiguity:** labels sit on the chart point they describe, not in a legend.

## 3b. Show the idea so a four-year-old gets it (lint)

Charts and numbers prove; pictures make an idea stick. Dual coding: an idea held as words and as an image is
remembered far better than either alone, and the image is what the viewer replays later ("the balloon popped and
only the coin was left"). Two tests for every picture scene:

- **Sound off:** watch the pictures alone and they still tell the story (HyperFrames story rule).
- **Four-year-old:** a small child could say what happened ("the sheep followed the sheep", "the face was happy,
  then crying"). Abstract shapes, stick figures and diagrams fail this test; familiar things with faces pass it.

Rules:

- **Familiar things only:** balloons, coins, sheep, faces, a lock, a mirror, a tree, a boat — never a diagram of an idea.
- **Feelings on faces:** a happy face turning into a crying face beats any arrow. Characters react to what happens.
- **One action per scene, on the word** (`cue`): the balloon pops on "burst", the lock drops on "before".
- **One picture per idea, kept for the whole lesson.** If price is a balloon, it is a balloon in the story, in the
  lesson, and in the recap icon. A recurring picture is a promise the viewer can follow.
- **Every principle and every turn of the story is a stage scene** (lint); no three text-only scenes in a row (lint).
- **Speech bubbles carry at most four words** (validation): "Sold!", "Follow me!", "No, thanks!".
- **No likenesses:** a real person is played by a generic emoji character (Newton = Man scientist) with their name as
  a label; never a generated face meant to look like them. No invented numbers on screen: "£££" / "£" mean high / low.

`visual.type: "stage"` (engine: `vfactory/lesson/stage.py`) = a **world** (`meadow`, `sky`, `sea`, `room`, `night`,
`plain`) + **actors** (any of 1,594 Fluent Emoji 3D pictures; `python -c "from vfactory.lesson import assets;
print(assets.search('crying'))"`) that **enter** (`pop`, `drop`, `rise`, `slide-left`, `slide-right`, `fade`) and **act**
(`bounce`, `jump`, `shake`, `wobble`, `grow`, `shrink`, `pop`, `fall`, `walk`, `fly`, `swap`, `say`, `count`, `fade`, `tilt`,
`glow`) on cue words. `repeat` makes a row (a flock). Layout: feet on the ground line (y 0.68), 2-6 actors, sizes
0.12-0.44 of the frame height, nothing above y 0.1 (the series rail), the caption band below.

Picture bank (any topic):

| Idea | Picture |
|---|---|
| Price vs value; hype; a bubble | a **balloon** (price, all air) next to a **coin** (value); it grows, then pops or shrinks to coin size |
| A crash, a loss | the balloon pops; happy faces swap to crying faces |
| Following the crowd, FOMO | **sheep** following a ram that says "Follow me!" toward a balloon that pops |
| Selling early, watching others win | the hero hands the balloon to a buyer and gets a money bag; then watches friends' balloons grow |
| Moods, volatility (Mr. Market) | a **face** that swaps from star-struck ("Buy at £££!") to crying ("Sell for £!"); "You" says "No, thanks!" |
| Rules, discipline, margin of safety | a rule book; a **lock** drops onto it; a storm cloud shakes but the book holds |
| The risk is us, biases | a **mirror**: the hero sees himself |
| A company, a voyage, trade | a **boat** sailing to an island; a scroll for the real cargo |
| Growth, compounding | a seedling → a tree; a snowball rolling bigger |
| Risk, safety | an umbrella in the rain; eggs in one basket |

## 4. Facts

- Primary first (the paper, the letter, the filing, the person's book); two sources for anything central.
- Date it: "about £1,000 by summer 1720", "as of 2026".
- When sources disagree, use the conservative figure, say "about", and record both in `sources`.
- Quotes: exact wording from the source, or mark `attribution: "attributed"` and say so.

## 5. Approval view

`script.md` (written by `lint`) is what the person reviews: beats with act, narration and visual; principles;
sources; lint notes. Change the script there in conversation, then update `lesson.json`.
