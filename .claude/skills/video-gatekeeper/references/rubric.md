# The gatekeeper's rubric (editorial standard for the "Review sách" channel)

**Channel promise:** *Giúp người tò mò học tốt hơn, nghĩ rõ hơn, và ra quyết định đầu tư khôn ngoan hơn.*
(Help curious people learn better, think clearly, and make wiser investment decisions.)

A review improves four outcomes — the right people **click**, **keep watching**, **share** the video, and take a
**useful next step** — and it protects **accuracy** and **learning**. These are editorial standards, not YouTube's
algorithm weights and not a formula for predicting virality. (YouTube groups performance into appeal, engagement and
satisfaction: https://support.google.com/youtube/answer/16559650)

The standard: *a video people choose because it interests them, finish because it rewards them, share because it
helps someone, and return to because they trust our judgment.*

## 1. The brief (`meta.brief` in lesson.json) — define success before reviewing
If a field is missing, state the assumption you are making, and write it into `meta.brief`.

| Field | What to specify |
|---|---|
| `target_viewer` | situation, knowledge level, main problem, language (default: curious Vietnamese adults 20–40, beginners in investing) |
| `format` | book analysis (this series), tutorial, essay, case study, Short… |
| `central_question` | the one question the video answers |
| `transformation` | "Before watching, they ___. After watching, they can ___." |
| `discovery_goal` | search demand, broader recommendations, or existing audience |
| `primary_conversion` | ONE: subscribe, watch another video, comment, email list… This channel's default (the owner's choice): **comment answering the end-card question about what to make next**. Everything else on the end card competes with it. |
| `share_recipient` | who a viewer would send this to, and why |
| `evidence` | sources, calculations, examples |
| `constraints` | length 4–5 min, 4:3, drawn icon metaphors (no footage, no faces of real people), one narrator voice |

## 2. Score these 12 categories
Rate each **0–5**, then points = `rating ÷ 5 × weight`.

| # | Category | Weight | Core question |
|---|---|---:|---|
| A | Audience relevance | 8 | Does the intended viewer immediately care? |
| B | Idea and potential reach | 12 | Is the central question compelling enough to choose? |
| C | Title and thumbnail | 12 | Do they create a clear, honest reason to click? |
| D | Opening | 8 | Does it quickly confirm the promise and begin delivering? |
| E | Structure and sustained interest | 10 | Does each section earn the next? |
| F | Teaching and understanding | 10 | Can viewers understand and use the ideas? |
| G | Evidence and trust | 10 | Are the claims justified and represented fairly? |
| H | Original contribution | 6 | Why watch our version? |
| I | Presentation and production | 6 | Do sound, visuals and delivery help the experience? |
| J | Payoff and application | 6 | Does the video deliver a worthwhile result? |
| K | Shareability | 6 | Is there a specific reason to send it to someone? |
| L | Conversion and channel fit | 6 | Is the next step relevant, clear and earned? |
| | **Total** | **100** | |

Anchors: **0** missing or seriously misleading · **1** major weakness, rebuild · **2** partly works, substantial gaps ·
**3** clear and competent · **4** strong, specific, well supported · **5** exceptionally effective, with concrete evidence.

**Every score needs evidence** — a quotation, beat id, timestamp, frame from `gate/scenes.jpg`, or thumbnail detail.
"Engaging script" is not evidence. Use **"not assessable"** when material is unavailable (actual retention, real
shares, CTR); report the assessed weight next to the total ("78/94 assessed").

**Ship standard (this channel):** no publication gate open, **total ≥ 75 of the assessed weight (scaled)**, and no
category rated ≤ 1. Otherwise REVISE.

## 3. Detailed criteria (validation in italics)

**A. Audience relevance (8)** — names a recognisable problem, desire or question; matches the viewer's knowledge;
explains why it matters through consequences; language and situations fit a Vietnamese viewer; serves the promise.
*Complete: "Someone in ___ situation would watch because ___."* Failure: "this is an important book".

**B. Idea and potential reach (12)** — one central question; real tension (misconception, uncertainty, hard choice,
surprising result); a concrete outcome; an entry point for people who never heard of the book; enough substance; a
distinctive angle; an enduring need or a stated timely hook. *Pitch it in one sentence.* Failure: a broad subject
("mental models") as the premise; better: "When does a useful mental model lead you to the wrong conclusion?"

**C. Title and thumbnail (12)** — one coherent promise together; understandable to a stranger; curiosity while
revealing the subject; matches what the video delivers; specific without unsupported certainty; legible at phone
size (`gate/thumb.jpg`, 320 px); one focal point; the image adds to the title, never repeats it; no misleading
wealth imagery or fabricated results. *Ask: "What would a reasonable viewer expect after clicking?" — then point to
the beat that delivers it.* Deliverable: **three genuinely different title–thumbnail pairs** with promise and tradeoff;
set the best one in `meta.youtube` (and the hook's frame 0, which is the thumbnail).

**D. Opening (8)** — confirms the promise promptly; starts with a concrete question, scene or demonstration; stakes
without exaggerated fear; an early piece of value; enough context; credibility where needed; no greetings, biography
or previews of every section. *Review the first 30 s separately (`gate/opening.txt`, `gate/hook.jpg`): mark every
sentence that gives neither value nor necessary setup.* Rewrite it in our voice and within factual limits; never
invent personal experiences.

**E. Structure and sustained interest (10)** — a sequence viewers can follow; each section has a job; questions are
answered along the way, not all withheld; new questions arise naturally; explanation alternates with evidence,
example or application; no repetition or detours; hard concepts get time; strong material placed where it helps;
everything raised is resolved. *For every section: "The viewer now understands ___, which makes the next question
___."* Do NOT require a cut or surprise every N seconds: judge pacing by whether attention supports understanding.
(The gate's frozen-screen and unread-line findings are evidence for this judgment, not verdicts.)

**F. Teaching and understanding (10)** — a specific learning outcome; terms explained; builds on what viewers know;
examples and counterexamples; reasoning shown between steps; similar concepts separated; misconceptions addressed;
diagrams where they explain better than speech; a chance to retrieve/apply; transfer to a new situation.
*Write one application question; can viewers answer it from what the video actually teaches?*

**G. Evidence and trust (10)** — for every substantial claim: fact, interpretation, opinion, prediction or
experience; does the source directly support it; quotations and numbers verified; correlation ≠ causation;
confidence matches evidence; disagreement and limits represented; a book's assertion not treated as established
fact; sources discoverable (end card + description). Investing content: date market data, state units and
currencies; explain assumptions; separate historical results, hypothetical illustrations and forecasts; show
downside and alternatives; fees, inflation, taxes, liquidity, leverage where material; no cherry-picked winners;
disclose holdings/commercial ties; say what evidence would weaken the thesis.
*Produce the claim ledger* (`gate/claims.md`): | Claim | Supporting source | What it actually supports | Required correction |.
A disclaimer does not repair a misleading claim.

**H. Original contribution (6)** — analysis beyond summary; original or Vietnamese-context examples; competing
explanations compared fairly; an application, calculation or decision process shown; where the advice works and
where it breaks; our identifiable voice. *"What does this add that the book or a generic summary does not?"*

**I. Presentation and production (6)** — speech intelligible and comfortable (gate: words heard, pace per line,
pauses); emphasis and pauses meaningful; visuals explain (the **mute test**: each picture alone says what is being
said — a tea cup under "what is your flywheel?" fails); charts have labels, units, dates, honest comparisons;
on-screen text readable on a phone; captions accurate; diacritics drawn by the fonts (gate `fonts`); music under the
voice; graphics never falsely imply evidence (illustrative curves labelled as such).

**J. Payoff and application (6)** — answers the central question; fulfils the title; a memorable explanation or tool;
how to apply it; boundaries stated; no needless repetition. *"The viewer can now ___, demonstrated by ___."*

**K. Shareability (6)** — a specific social use: help someone, explain a shared experience, start a useful discussion,
support a joint decision, share a surprising insight; easy to describe in a sentence; understandable without knowing
the channel; a memorable example or visual to retell; never outrage or inflated certainty; any share request names a
real recipient and reason. *Write the private message that would accompany the link.* If the only plausible message
is "great video", the sharing reason needs work.

**L. Conversion and channel fit (6)** — one primary next step (`meta.brief.primary_conversion`), a natural
continuation of the viewer's need, asked only after value is delivered, with its benefit explained, easy to do,
honestly described; a reason for new viewers to return; no competing calls to action (gate `end_card_ctas`).
*"Because the viewer now wants ___, the next useful step is ___."*

## 4. Publication gates — a high total never hides these
Mark **REVISE before publishing** (verdict cannot be "proceed") when the material contains:
- a central claim that is materially false or unsupported;
- a title or thumbnail promise the video does not fulfil;
- invented quotations, experiments, results or personal experiences;
- materially misleading investment calculations or charts;
- an explanation that fails to teach the stated core concept;
- an undisclosed relevant commercial conflict;
- a technical defect the gate reports as a hard fail (dropped words, numbers not read as written, glyphs the fonts
  cannot draw, broken layout).
At the idea stage an unanswered research question is a **research requirement**, not automatically a failure.

## 5. Feedback that can be implemented
Every important finding:

| Field | Content |
|---|---|
| Location | timestamp, beat id, quotation or asset detail |
| Observation | what is present in the material |
| Viewer consequence | why it may reduce understanding, interest, trust, sharing or conversion |
| Priority | must fix · high impact · optional |
| Proposed change | the exact replacement, cut, reorder, example or visual (as a lesson.json edit) |
| Validation | how to check the change solved it |
| Confidence | high · medium · low, with a reason |

Weak: "make this more engaging". Useful: "Section two names four biases before demonstrating any. Start with the
investment dilemma in section four, ask viewers to choose, then explain the bias behind that choice."
Give the **three highest-impact changes first**. Preserve strong material.

## 6. Stages
| Stage | Focus | Output |
|---|---|---|
| Idea | audience, premise, differentiation, feasibility | proceed / reframe / research / drop |
| Outline | promise, logic, evidence plan, payoff | revised section sequence |
| Script | opening, teaching, claims, pacing, sharing, CTA | located feedback, targeted rewrites |
| Rough cut (a draft render) | delivery, visuals, sound, actual pacing | timestamped edit list |
| Pre-publication (final render) | packaging alignment, final claims, destination | readiness decision, unresolved issues |
| Post-publication | observed audience response | evidence-based hypotheses and next tests |
After publishing, compare comparable videos and traffic sources; CTR varies with audience and placement; a retention
spike can mean interest **or confusion** (https://support.google.com/youtube/answer/7628154,
https://support.google.com/youtube/answer/9314415). Neither metric alone explains causation.

## 7. Review rules
- Support every important finding with a quotation, beat, timestamp, asset detail or supplied analytics.
- Separate observed problems from hypotheses. Never invent sources, experiences, results, analytics or reactions.
- Mark unavailable evidence "not assessable". Do not predict virality percentages or invent universal metric targets.
- Apply the anchors consistently and report assessment coverage. A high total never overrides a publication gate.
- Preserve the channel voice; say what should stay unchanged. Improve curiosity without exaggerating claims; improve
  pacing without sacrificing comprehension. Do not force drama, personal stories or CTAs where they do not fit.
- Verify consequential claims against sources when tools permit (WebSearch); otherwise mark them unverified.
- After revising, check the revision did not introduce factual errors, break the promise, remove nuance or create
  production demands the engine cannot meet. **Do not raise a score because you wrote the revision**: re-score from
  the rebuilt video's evidence.

## 8. Return (write to `gate/review.md`, and the scorecard to `gate/review.json`)
A. Verdict: proceed, revise, research, or rethink.
B. One sentence: audience, promise, viewer transformation.
C. Weighted scorecard with evidence and assessment coverage.
D. Publication blockers or research requirements.
E. Three highest-impact improvements, ranked.
F. Detailed feedback (location, consequence, exact fix, validation, confidence).
G. Targeted rewrites of the weakest material (applied to lesson.json when in fix mode).
H. Three title–thumbnail concepts grounded in the actual content.
I. A specific share recipient and the plausible message accompanying the link.
J. One primary CTA and why it follows naturally.
K. A stage-appropriate validation plan.
