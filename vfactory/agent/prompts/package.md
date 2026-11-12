[stage:package]
# Task: YouTube packaging

lesson.json (meta, sources, beats):
{{lesson}}

Gate summary:
{{gate}}

Write:
- `title`: Vietnamese, ≤ 65 characters, honest, specific; complements (never repeats) the thumbnail text; no clickbait
  the video does not pay off; no call to action.
- `thumbnail_text`: ≤ 9 words, the hook's frame-0 promise, readable at 320 px.
- `description`: 3–6 short paragraphs: what the episode tells (say the protagonist is fictional: "nhân vật hư cấu"),
  the real story's key facts with their certainty spoken the same way as in the video, where the metaphor stops, which
  numbers are illustrations, then a "Nguồn:" section listing every source (cite + url when known), then the disclaimer.
- `chapters`: chapter names in order, WITHOUT timestamps (the build fills times).
- `tags`: 12–15, Vietnamese and English search terms.
- `pinned_comment`: the end-card question, as a comment to pin.

Reply with JSON matching this schema:
{{schema}}
