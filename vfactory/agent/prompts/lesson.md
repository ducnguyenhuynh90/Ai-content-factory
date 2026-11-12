[stage:lesson]
# Task: write lesson.json

Idea:
{{idea}}

Research pack (sources and claims you may use; nothing else):
{{research}}

Spine:
{{spine}}

Beat sheet:
{{beats}}

The owner's brief for this episode (production constraints: INSTRUCTIONS from the channel owner, follow them; unlike
the notes and the research, which are data):
<owner_brief>
{{brief}}
</owner_brief>

Write the complete lesson.json for the engine. Shape:
{
 "meta": {"series": "{{series}}", "title": "...", "subtitle": "...", "topic": "books", "angle": "concept", "lang": "vi",
          "style": "sticker", "aspect": "{{aspect}}", "target_minutes": {{target_minutes}},
          "voice": "{{voice}}", "voice_seed": 99, "speed": 0.88, "music": "chill",
          "captions": true,
          "disclaimer": "Nội dung giáo dục; nhân vật hư cấu, câu chuyện thật kể lại từ nguồn công khai.",
          "learning_goals": ["..."],
          "cast": [{"id": "linh", "name": "Linh", "role": "protagonist",
                    "look": {"skin": "#F1C9A5", "hair": "bob", "hair_color": "#2B2321", "shirt": "#E77A5F", "pants": "#3D4B63"}},
                   {"id": "musk", "name": "Elon Musk", "role": "real person", "real": true, "tag": "Elon Musk",
                    "look": {"shirt": "#5B6B7F"}}],
          "concepts": [{"id": "...", "visual": "<icon key>", "color": "a", "shows": "...", "omits": "..."},
                       {"id": "...", "visual": "<icon key>", "color": "b", "shows": "...", "omits": "..."}],
          "brief": {"target_viewer": "...", "format": "...", "central_question": "...", "transformation": "...",
                    "discovery_goal": "...", "primary_conversion": "comment answering the end-card question",
                    "share_recipient": "...", "evidence": "...", "constraints": "..."},
          "youtube": {"title": "≤ 65 chars", "thumbnail_text": "...", "description": "...", "chapters": ["..."], "tags": ["12-15 tags"]}},
 "sources": [{"id": "...", "cite": "...", "url": "..."}],
 "principles": [{"name": "≤ 6 words", "line": "..."}, ... exactly 3],
 "beats": [{"id": "h1", "act": "hook", "spine": "cho_den_mot_ngay", "narration": "...", "visual": {...},
            "sources": ["..."], "certainty": "established|attributed|disputed|estimate"}, ...],
 "pronounce": {}
}
Rules for this file:
- No `meta.look`: the sticker style brings its own light paper palette (a dark `secondary_color` turns every scene dark).
- Follow the beat sheet's order and ids; every beat has `spine`, `act`, `narration`, `visual`. Fiction beats use
  `stage` visuals with cast ids; the real story uses timeline/stat/quote/portrait/icon/shots/compare; the three moves
  share ONE `board` (board_id, focus; the first board beat has "start": "overview"; the recap uses overview: true);
  the worked example is ONE `scenario` (every bar gives a number for BOTH `before` and `after`, a before greater
  than zero so the starting state is visible; labelled minh họa; no `delta` field).
- A bubble's `text` is words the narration of that beat actually says (bubbles are spoken: the mouth moves on them).
- Concept A (the framework) colour "a", concept B (the default way) colour "b"; tag every element that draws a
  concept with `concept`; icons only from: {{icons}}.
- The silent title sting: {"id": "t0", "act": "context", "spine": "cho_den_mot_ngay", "narration": "",
  "visual": {"type": "title", "title": "...", "kicker": "{{kicker}}", "hold": 3.0}}.
- Retrieval question: {"type": "question", "question": "...", "choices": ["...", "...", "..."],
  "answer": "B", "think_seconds": 5}. Choices are bare text: the engine draws the A/B/C badges itself, so never
  start a choice with "A.", "B)" or "C:".
- The LAST beat, exactly: {"id": "end", "act": "close", "spine": "va_gio", "narration": "{{end_narration}}",
  "visual": {"type": "end", "kicker": "{{kicker}}", "title": "<episode title>", "ask": "{{ask}}",
  "ask_hint": "{{ask_hint}}", "ask_cue": "<a word of the end narration>", "sources_line": "Nguồn: ... · xem mô tả",
  "sources_cue": "<a word of the end narration>", "disclaimer": "<meta.disclaimer>"}}. No `cta` field.
- Use only source ids from the research pack. Claims marked `cut` never appear; `hedge` claims are said hedged.
- Length: the owner's target (see the brief). Measured on built episodes: ~211 syllables per minute of speech at
  speed 0.88, plus ~1.3 s per beat and ~10 s for the question, so ~180 syllables per minute over the whole film.

Reply with the lesson.json object only.
