[stage:critique]
# Task: self-critique as the channel's editor

Research pack:
{{research}}

lesson.json:
{{lesson}}

Deterministic checks and lint notes on it (fix anything still open):
{{notes}}

Read the lesson as a Vietnamese viewer would hear and see it. Check, beat by beat:
1. Pixar: want + flaw; stakes felt; coincidence only into trouble; the ending earned by the protagonist's choice.
2. Hook in the first 10 s; no preview, filler or early CTA; the open loop is a story loop, not a list.
3. Facts: every number/date/quote traceable to a research claim; hedged claims hedged out loud; the 2 threads never
   blur (the fiction never "proves" the real story); myths corrected accurately; no likeness of real people.
4. Teaching: misconception named then corrected; one metaphor carried through; its limit said on camera; three moves
   with a worked example; question → recap in the same words → close back to the hook.
5. Speech: numbers in words, long numbers rounded, no tongue-twisters or phrases that blur when spoken.
6. Screen: a picture that MEANS each line; something changes every 2–3 s; cues are words in the beat's narration;
   short on-screen text.
Report `issues` (severity must|should) and the `ops` that fix them: JSON-patch-style edits on lesson.json
({"op": "replace"|"add"|"remove", "path": "/beats/@b07/narration", "value_json": "<the new value as a JSON string>",
"why": "..."}). Paths may select beats by id with "@id". Change only what improves the episode; keep ids stable. Do not
add facts that are not in the research pack. `verdict`: pass if nothing must change.

Reply with JSON matching this schema:
{{schema}}
