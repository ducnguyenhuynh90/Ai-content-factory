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

Write the complete lesson.json for the engine. Shape:
{
 "meta": {"series": "{{series}}", "title": "...", "subtitle": "...", "topic": "books", "angle": "concept", "lang": "vi",
          "style": "sticker", "aspect": "16:9", "target_minutes": [4, 6],
          "voice": "omnivoice:male, middle-aged, very low pitch", "voice_seed": 99, "speed": 0.88, "music": "chill",
          "captions": true, "look": {"primary_color": "#E8B06A", "secondary_color": "#12100E"},
          "disclaimer": "Nội dung giáo dục; nhân vật hư cấu, câu chuyện thật kể lại từ nguồn công khai.",
          "learning_goals": ["..."],
          "cast": [{"id": "linh", "name": "Linh", "role": "protagonist",
                    "look": {"skin": "#F1C9A5", "hair": "bob", "hair_color": "#2B2321", "shirt": "#E77A5F", "pants": "#3D4B63"}},
                   {"id": "musk", "name": "Elon Musk", "role": "real person", "real": true, "name_tag": "Elon Musk",
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
- Follow the beat sheet's order and ids; every beat has `spine`, `act`, `narration`, `visual`. Fiction beats use
  `stage` visuals with cast ids; the real story uses timeline/stat/quote/portrait/icon/shots/compare; the three moves
  share ONE `board` (board_id, focus; the first board beat has "start": "overview"; the recap uses overview: true);
  the worked example is ONE `scenario` (bars with before/after, labelled minh họa, no `delta` field).
- Concept A (the framework) colour "a", concept B (the default way) colour "b"; tag every element that draws a
  concept with `concept`; icons only from: {{icons}}.
- The silent title sting: {"id": "t0", "act": "context", "spine": "cho_den_mot_ngay", "narration": "",
  "visual": {"type": "title", "title": "...", "kicker": "{{series}}", "hold": 3.0}}.
- Retrieval question: {"type": "question", "question": "...", "choices": ["A. ...", "B. ...", "C. ..."],
  "answer": "B", "think_seconds": 5}.
- The LAST beat, exactly: {"id": "end", "act": "close", "spine": "va_gio", "narration": "{{end_narration}}",
  "visual": {"type": "end", "kicker": "{{series}}", "title": "<episode title>", "ask": "Bạn muốn tập sau về khung tư duy nào?",
  "ask_hint": "<three other frameworks, ' · ' separated>", "ask_cue": "còn bạn", "sources_line": "Nguồn: ... · xem mô tả",
  "sources_cue": "còn bạn", "disclaimer": "<meta.disclaimer>"}}. No `cta` field.
- Use only source ids from the research pack. Claims marked `cut` never appear; `hedge` claims are said hedged.
- Estimated length at ~240 Vietnamese syllables per minute: 4–6 minutes.

Reply with the lesson.json object only.
