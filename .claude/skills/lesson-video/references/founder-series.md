# Series bible: Founder Stories (startups)

Promise: one true founder story per episode, 3-5 minutes, 16:9 (9:16 cut-downs later). Entertaining first, then
2-3 principles a founder can use on Monday. Tone: warm, curious, a little wry; respect the founder, puncture the myth.

Storytelling borrowed from the stickman explainer playbook (kaomei/stickman-video-director): a visual hook in
the first three seconds, a 5-stage emotional arc (calm → pressure → crisis → turn → release), physical comedy on
the cue word, and one visual punchline per scene. Our arc in `script-craft.md` already maps onto it:
hook/loop = calm with a crack in it, story/escalation = pressure, turn/complication = crisis, truth vs. legend +
principles = turn, close = release.

## Look: stickmen + emoji props on paper

- World: `"world": "paper"` (warm white paper, hand-drawn ground line, black ink, red accent) for every stage scene.
- People are code-drawn stickmen: `"Stick <pose> [<face>] [<colour>] [cap] [glasses]"` (engine: `vfactory/lesson/stick.py`).
  Poses: stand, wave, cheer, point, think, shrug, shocked, hold, facepalm, slump, run, walk, sit.
  Faces: happy, joy, sad, worried, shocked, neutral, determined, smirk, tired.
  Act a mood change with `swap` on the cue word: `Stick hold worried red` → `Stick cheer joy red` on "won".
- Hook stage: `"frame0": true` and actors with `"enter": "none"`, so frame 0 (the thumbnail) already shows the claim.
- Props are Fluent Emoji 3D (airplane, money bag, battery, light bulb...).
- No likenesses: the founder is a generic stickman with a name label (or the `portrait` medallion).

## Casting constants (keep identical across episodes)

| Who / what | Picture |
|---|---|
| The episode's founder | stickman, **red tie**, name label |
| Co-founders | stickmen, **blue** / **orange** ties |
| Investors, banks, big companies | stickmen, **grey** tie, `glasses` |
| Customers | stickmen, **green** tie |
| Cash / runway | **Battery** → **Low battery** |
| The idea | **Light bulb** (glows when it's right) |
| A gamble, luck | **Joker** / **Game die** / **Slot machine** |
| Time bought | **Hourglass not done** |
| A deal, belief, investors saying yes | **Handshake** |
| A network, parts that only work together | **Puzzle piece** (row) |
| Growth | **Chart increasing**, **Seedling → Deciduous tree** |

## Principle library (reuse names so the series builds a vocabulary)

| Principle | Born in | Reuse in |
|---|---|---|
| Cash is oxygen | FedEx 1973 (No. 1) ✔ | Airbnb cereal, Nike/Shoe Dog, Tesla 2008 |
| A gamble buys time, not a business | FedEx (No. 1) ✔ | Tesla 2008 last round |
| Some ideas only work at full size | FedEx network (No. 1) ✔ | Airbnb two-sided market, Uber cities |
| Do things that don't scale | Airbnb photographing listings (No. 2) | Stripe "Collison installation" |
| Ugly early ideas are the cheap ones | Airbnb (No. 2) | Twitter/Odeo, Slack/Glitch |
| Notice what already works (pivot) | Slack from Glitch | Instagram from Burbn, YouTube |
| Growth eats cash | Nike, Shoe Dog | Tesla Model 3 ramp |

## Episode ideas

1. The Night FedEx Went to Vegas: Fred Smith, 1973 ✔ (`lessons/founders/001-fedex-blackjack`)
2. Cereal for a Startup: Airbnb's Obama O's and Cap'n McCain's, 2008
3. The Game That Failed Twice: how Glitch became Slack
4. Shoe Dog: Phil Knight, the bank that froze Nike's account
5. Burbn to Instagram: deleting most of your product
6. Tesla, Christmas 2008: the funding round that closed on the last day
7. The Collison Installation: Stripe's founders setting up customers by hand
8. Dyson's 5,127 prototypes

## Rules on top of the lesson-video hard rules

- Founder myths are the hook, not the content: tell the legend, then the record. Mark `attributed`/`disputed`
  and SAY it ("as the story goes", "reportedly").
- Never glamorise gambling, burnout or law-breaking: show what it cost and what actually worked.
- Company numbers: say "about", cite the source, prefer filings, the founder's own book, or a founding executive's book.
