# Plan: "Chuyện đời thường" sticker-style story videos + a local, model-agnostic agent

Owner's request (12/11): redo the thinking-framework videos as gripping stories set in everyday Vietnam 2026, with
relatable real-life parallels; sticker-style visuals with moving characters and smooth transitions; a Pixar-like story
structure; and build it as an agent that runs locally and accepts any model.

## 1. Story format (what every episode is)
- **Two threads, braided.** A fictional but true-to-life Vietnamese protagonist in 2026 (e.g. Linh, 27, kế toán ở
  Q.7, chạy thêm đơn TikTok Shop; anh Tùng chạy Grab; cô Mai mở quán cà phê ở Đà Lạt) lives a small dilemma. A real,
  verified story (SpaceX, Hà Nội 1902, Wald…) is the "flashback" that cracks it open. The real story stays factual;
  the fictional thread is labelled as such once ("nhân vật hư cấu, chuyện có thật").
- **Pixar story spine** (Emma Coats' rule #4), 4–6 minutes:
  1. Ngày xưa / Mỗi ngày… (the protagonist's normal, with a want)
  2. Cho đến một ngày… (inciting incident; the hook lands in the first 10 s)
  3. Vì vậy… vì vậy… (escalation; the default way of thinking makes it worse — the misconception)
  4. Cho đến khi… (the real story as the turning point; the framework is named and shown as ONE metaphor)
  5. Từ đó… (protagonist applies 3 moves; a worked example on screen)
  6. Và giờ… (new normal; where the metaphor stops; a question for the viewer; one CTA)
- Plus Pixar's rules the writer checks: a want and a flaw, stakes the viewer feels, coincidence only to get into
  trouble never out, an ending earned by the character's choice.

## 2. Visual style: "sticker"
- Light, warm paper background (cream/pastel), flat sets (street, văn phòng, quán cà phê, phòng trọ, màn hình điện
  thoại), everything drawn as stickers: bold shapes, thick white outline, soft drop shadow, slight paper texture.
- Rigged characters built from SVG parts (head, hair, face, torso, arms, legs) with expressions (vui, lo, ngạc nhiên,
  suy nghĩ, buồn) and actions (đứng thở, chớp mắt, nói, vẫy, chỉ, nhún vai, đi vào/ra, nhảy, ngồi). Real people
  (Musk, Buffett…) are never caricatured: a generic sticker figure plus a name tag.
- Smooth transitions between beats: whip-pan, zoom-through an object (match cut), circle wipe, page slide.
- Fonts that draw every Vietnamese glyph (Inter / Be Vietnam Pro, weights 600/800 only; never 700).
- Same rules as before: text ≥ 36 px at 1080p, something moves every 2–3 s, one picture per concept, captions.
- Aspect: 16:9 by default (YouTube main), 9:16 variant for Shorts.

## 3. Engine contract (new visual types, JSON)
```json
{"type": "stage",
 "set": "street|office|cafe|room|phone|plain",
 "characters": [{"id": "linh", "look": {"skin": "#F1C9A5", "hair": "bob", "hair_color": "#2B2321",
                  "shirt": "#E77A5F", "pants": "#3D4B63"},
                 "x": 0.3, "expression": "worried", "action": "idle",
                 "cues": [{"cue": "nhưng", "expression": "surprised", "action": "jump"}]}],
 "props": [{"icon": "phone", "x": 0.7, "y": 0.6, "cue": "điện thoại"}],
 "bubble": {"who": "linh", "text": "Sao lại đắt thế?", "cue": "sao"},
 "caption": "…", "transition": "whip|zoom|circle|slide|cut"}
```
`meta.cast` registers characters once ({id, name, look, role}); beats refer to them by id. `meta.style = "sticker"`
switches the whole film to the sticker look (existing visual types render as stickers too).

## 4. The agent (`python -m vfactory.agent`)
Stages, each a prompt file + JSON output validated before the next stage, all state in a run directory (resumable):
`idea → research (facts with sources; human can drop notes/URLs) → spine → beat sheet → lesson.json (repair loop on
lint errors) → self-critique → build → gate (deterministic checks + LLM review of frames if the model sees images) →
fix loop (max N rounds) → package (title, thumbnail text, description)`.

Providers, chosen by flag/config/env, no hard dependency:
- `anthropic` — official SDK (optional install), default model `claude-opus-5-5`.
- `openai` — any OpenAI-compatible Chat Completions endpoint via stdlib HTTP: OpenAI, OpenRouter, Gemini
  (OpenAI-compatible endpoint), Ollama (`http://localhost:11434/v1`), LM Studio, vLLM, llama.cpp server.
- `fake` — scripted responses for tests.
Weaker local models get: smaller per-stage prompts, strict JSON with schema + repair retries, and lint feedback loops.

## 5. Order of work
1. Engine: sticker look + `stage` + characters + transitions (+ tests, a 30 s check render).
2. Agent package + providers + prompts + tests with the fake provider.
3. Pilot: redo "Tư duy từ gốc" in the new format, run end-to-end through the agent, owner reviews.
4. Only after approval: redo the other framework episodes / new topics. Publishing is unchanged until then.
