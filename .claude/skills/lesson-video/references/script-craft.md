# Script craft for lessons that stick

Synthesised from: the Vox-style explainer guide (vox-explainer-skill), the whiteboard-video skill's
script rules, iart-ai's script-to-screen workflow, Mayer's multimedia learning principles, Derek Muller's
(Veritasium) misconception research, the testing effect, and classic story structure (And-But-Therefore,
the Story Spine). The linter enforces the parts marked (lint).

## 1. The arc (4-5 minutes ≈ 18-22 beats, ~600 words at ~145 wpm)

| Act | Beats | Job |
|---|---|---|
| **Hook** (lint: first) | 1 | Start inside the story with a concrete, surprising fact or paradox. Never "Today we'll talk about…" (lint). ≤ 10 s. |
| **Misconception** (lint) | 1 | Name the wrong belief the viewer probably holds ("bubbles only catch fools"). Muller: confronting it roughly doubled learning vs. clear exposition, which can even *reinforce* the error. |
| **Context: the turn** | 2-3 | "To understand what happened, you have to go back to…" Who, where, what was at stake. One person to follow. |
| **Escalation** | 4-6 | The story step by step, each beat a little more surprising. Numbers, named specifics, a chart. AND… AND… |
| **Complication** | 1-2 | BUT: the cost, the reversal, the irony. This is where the principle is born. |
| **Truth vs. legend** | 0-1 | When the popular version is wrong, show both. It teaches source-thinking. |
| **Principles** | 2-4 (lint) | THEREFORE: one beat per principle: name it in ≤ 6 words, then tie it to the story in one sentence, then generalise in one sentence. |
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

## 4. Facts

- Primary first (the paper, the letter, the filing, the person's book); two sources for anything central.
- Date it: "about £1,000 by summer 1720", "as of 2026".
- When sources disagree, use the conservative figure, say "about", and record both in `sources`.
- Quotes: exact wording from the source, or mark `attribution: "attributed"` and say so.

## 5. Approval view

`script.md` (written by `lint`) is what the person reviews: beats with act, narration and visual; principles;
sources; lint notes. Change the script there in conversation, then update `lesson.json`.
