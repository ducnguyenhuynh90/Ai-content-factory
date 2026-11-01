# Plan: "Khung tư duy" series + what we borrow from 8 open-source video skills

## 1. What the 8 repos teach us (ideas only; nothing copied, no new dependencies)

| Repo | Licence | Fit | What we take |
|---|---|---|---|
| chuspeeism/dashi-animationstyle | MIT | High | Measured rules for explainers: legibility at phone size, "something visibly changes every 2–3 s", concept → picture tables |
| alchaincyf/huashu-art-motion | MIT | High | Storyboard lint before render (object + verb per shot, text-led shots ≤ 30 %), 3b1b-style "transform continuity" |
| lemomo-ai/lemo-opuscar | MIT (films CC BY) | Med-high | Whiteboard grammar: one board per chapter, camera travels, recap = whole board; reading-time check; "differ from last episode on 4 of 6 axes" |
| Kianzzz/xilo-opus-video | MIT | Med | Offer 3 deliberately different plans before building; "one metaphor carries the whole film" |
| WaterDJiang/Wattter_openSkills | CC BY-NC-SA | Ideas only | Write the explanation model first: parts, rules, what changes, **where the metaphor stops** |
| solplum/anything2video | MIT | Med | Mechanism scenes ("show the process change state"), 480-px readability probe |
| Vincentwei1021/mg-styles-15 | MIT | Low-med | Calibrated jury scale (7 = professional, 8 = high-end) |
| Vincentwei1021/video-shotcraft | Apache-2.0 | Low | Before/after slider, title that shrinks into the section label |

Avoid: Remotion (commercial licence), three.js/Blender stacks, glitch/neon/flash styles, cartoon characters,
the same slow push-in on every shot.

## 2. Engine upgrades (in order)

| # | Change | Why (owner complaints / weak gate category) | Effort |
|---|---|---|---|
| 1 | Readable-text floor ≈ 36 px (from ≈ 29 px) + gate renders 480-px check frames | small unreadable labels | S |
| 2 | Frozen-screen metric (pixel change every 2.5 s, caption band excluded); dead-stretch limit 3 s → 2 s unless a hold is declared | frozen screens | S |
| 3 | `meta.concepts`: each core idea gets ONE picture for the whole film + `shows`/`omits` (where the metaphor stops); lint fails if a concept is drawn two ways | wrong / drifting metaphors | S–M |
| 4 | Two concept colours (gold = idea A, coral = idea B) used in pictures, numbers and caption highlights | faster comprehension | S |
| 5 | Storyboard lint: every shot has an `action` verb; text-led shots ≤ 30 %; no 3 identical camera moves in a row | slide-show feel | M |
| 6 | `scenario` scene: one worked example that changes state on screen (before → after, slider) | teaching depth (gate F, H) | M |
| 7 | `board` scene: one continuous canvas per chapter, camera glides between regions, recap pulls back to the whole board | "one picture carries the film" | L |

Upgrades 1–4 go in first (a day), pilot 5–7 on the first framework episode.

## 3. The series: 10 thinking frameworks, each = one true story + one metaphor that carries the film

| # | Framework | True story (the spine) | Carrying metaphor | Where the metaphor stops (said on camera) |
|---|---|---|---|---|
| 1 | Tư duy từ gốc (First principles) | 2002: Elon Musk is quoted tens of millions for a rocket, prices the raw materials instead; SpaceX | Cook vs. chef: following a recipe vs. knowing why each ingredient is there | Not every field lets you rebuild from atoms; it costs time |
| 2 | Tư duy bậc hai (Second-order) | 1995: wolves return to Yellowstone; elk, rivers, willows change (and the scientific debate about how much) | Ripples from one stone in a pond | Real systems have many stones at once |
| 3 | Khi thước đo thành mục tiêu (Goodhart / incentives) | Hà Nội 1902: the rat-tail bounty and rat farms (Michael Vann's research) | A thermometer held over a candle | Measurement is still needed, just not as the only target |
| 4 | Vòng tròn năng lực | 1983: Buffett buys Nebraska Furniture Mart from Rose Blumkin on a handshake, no audit; skips the dot-com boom | A lantern's circle of light at night | The circle can grow, slowly, with study |
| 5 | Bản đồ không phải lãnh thổ | ~1620–1747: European maps draw California as an island for over a century | Map vs. the real coastline | A wrong map is still better than none if you keep checking it |
| 6 | Biên an toàn | 1883–84: Roebling designs the Brooklyn Bridge several times stronger than needed; P. T. Barnum walks 21 elephants across | A bridge rated for far more than the sign says | Too much margin also has a cost |
| 7 | Chi phí cơ hội | 1976: Ronald Wayne sells his 10 % of Apple for $800 (and says he does not regret it) | A fork in the road: choosing one path is giving up the other | Hindsight is not foresight; he had real reasons |
| 8 | Thiên kiến kẻ sống sót | WWII: Abraham Wald and the bullet holes on returning bombers (with the myth correction: the famous red-dot diagram is a later illustration) | Holes on the planes that came home | Some survivors really are better; check, don't assume |
| 9 | Tối thiểu hóa hối tiếc | 1994: Jeff Bezos leaves D. E. Shaw to sell books online, imagining himself at 80 | Looking back from your 80-year-old self | Not every risk is worth taking; it works for regret-of-not-trying decisions |
| 10 | Quan trọng vs. khẩn cấp | Eisenhower's 1954 remark on important vs. urgent; the jar of big rocks (clearly labelled a parable) | Big rocks, pebbles, sand in a jar | Some urgent things really are important |

Each episode keeps the series contract: hook ≤ 20 syllables with a real anchor, misconception first, one story told
step by step, three principles drawn as ONE recurring picture, the limits of the framework, a retrieval question about a
Vietnamese everyday situation, recap, one end-card CTA, and the gatekeeper's PASS before delivery.

Facts in this table are leads to verify, not final claims: each writer checks every date, number and quote against two
sources, and anything contested (Yellowstone's trophic cascade, Wald's diagram, quotes attributed to Eisenhower) is said
on camera as contested.

## 4. Schedule

- Now: finish building and gating book episodes 30, 23–26 (already written).
- Then: engine upgrades 1–4 (+ tests), rebuild nothing old.
- Pilot: framework episode 1 with upgrades 5–7; review with the owner before writing the other nine.
- Publishing continues daily at 19:00 after episode 32 (1 Dec), so the framework series would start 2 Dec.
