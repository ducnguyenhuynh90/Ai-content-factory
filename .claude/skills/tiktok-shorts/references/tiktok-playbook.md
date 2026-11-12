# TikTok short-form playbook

What the engine enforces is marked (lint). Everything else is editorial judgement — apply it, and let the channel's
own `learnings.md` overrule it once there is data.

## 0. What the feed rewards (as generally understood; TikTok doesn't publish weights)

1. **Watch time relative to length** — average % watched and full watches. Hook and pacing decide this.
2. **Shares and saves** — "I need to send this to someone" / "I'll need this later". The idea decides this.
3. **Comments** — a question, a choice, a mild disagreement. The ending decides this.
4. **Follows from the video** — a series, a promise of part 2. The channel decides this.

Views in the first hours are a test batch; a video that holds attention gets a bigger batch. So we optimise 1-4 and
read views last.

## 1. The first three seconds

- Frame 0 already shows the claim (lint: beat 1 is a `hook`). No logo, no title card, no black frame, no "xin chào".
- ≤ 12 words, ≤ ~3 s spoken (lint), one concrete anchor (name, number, year, a familiar object) and a turn.
- Spoken words, on-screen line and picture say the same thing at the same moment; line 2 + a hit land on the turn word.
- The hook must deliver what the cover and caption promise, or the viewer leaves at second 4.

### Hook types (tag `meta.hook_type`; analytics learns which work for this channel)

| type | shape | Vietnamese example |
|---|---|---|
| `contrarian` | the smart one lost / the obvious is wrong | "Thiên tài Newton từng mất một gia tài vì cổ phiếu." |
| `shock_stat` | a number that shouldn't be true | "Một củ tulip từng được rao giá bằng một căn nhà. Có thật không?" |
| `question` | a question the viewer can't answer yet | "Vì sao người Nhật xếp hàng không chen lấn?" |
| `story` | drop into the middle of the action | "Năm 1912, con tàu 'không thể chìm' có 20 xuồng cứu sinh cho 2.200 người." |
| `mistake` | the viewer is doing it too | "Bạn đang tiết kiệm sai cách — và lỗi này có từ năm 1720." |
| `secret` | the part nobody tells you | "Điều sách sử không kể về Vạn Lý Trường Thành." |
| `list` | a count + a payoff | "3 quyết định khiến đế chế giàu nhất thế giới phá sản." |
| `pov` | put the viewer inside | "Bạn là thương nhân ở London, năm 1720…" |
| `challenge` | test the viewer | "90 % người trả lời sai câu này." (only if you have the number's source) |

Write three, of different types, then pick. Never: clickbait the video doesn't pay off, fake urgency, fake numbers.

## 2. Structure for 25-60 s

| time | beat | job |
|---|---|---|
| 0-3 s | hook | scroll-stop: claim on screen, anchor, turn |
| 3-7 s | open loop | why stay: what the viewer gets / what it costs them |
| 7-35 s | escalation | a new picture every 2-4 s (lint warns > 6.5 s on one scene); each beat a little more surprising |
| ~middle | re-hook | the twist, the myth, "con số ai cũng nhắc là sai" |
| last 10 s | payoff | the lesson in ≤ 6 words, said once |
| optional | question | 3 choices + 3 s countdown → comments |
| last 3 s | end | loop line back to the hook or part-2 tease; ONE CTA (lint: follow-asks before the end are warned) |

Lengths: 21-34 s for a single surprising fact; 35-60 s for a story with a lesson. Longer only when the story holds;
split into parts instead (series → follows). If the goal is a monetisation programme that requires longer videos
(e.g. TikTok's Creator Rewards has required > 1 minute; check current terms and regional eligibility), make a
deliberate 61-90 s format with two re-hooks, not a padded short.

## 3. Pictures (sound-off test)

Most viewers scroll with sound off at least some of the time. Watch the video muted: the pictures + key phrases must
still tell the story.

- One idea = one familiar picture for the whole video (price = a balloon, value = a coin, the crowd = 3 star-struck
  faces). Act it out: the balloon grows, then falls on "vỡ".
- On-screen text = the key phrase or number (lint: ≤ 8 words per element), captions carry the sentence.
- Numbers count and land on the word that says them (`stat` with `cue`).
- Safe areas: nothing important right of 85 % width (like/comment/share rail) or below ~70 % height (caption, sound,
  nav). The renderer keeps to this; your own images should keep faces/subjects in the upper-middle.
- Your own footage, photos or images you generated and have the right to use go in `image`/`clip` beats. Never a
  generated photo-real image of a real person or a fake historical photo presented as real.

## 4. Voice

- Vietnamese: `vi-VN-NamMinhNeural` (male, warm, explainer) or `vi-VN-HoaiMyNeural` (female, bright); rate `+5%` to
  `+12%`. Read numbers as the TTS will say them; add `pronounce` for foreign names ("Odlyzko": "Ốt-lít-skô").
- The person's own voice usually outperforms TTS on trust and follows: record each beat on a phone
  (`"audio": "takes/b03.m4a"`), the engine times everything to it.
- Sentences short; a long one, then three words. It lands.

## 5. Sound

- The engine's score is original (no copyright claims). For reach, post `*_nomusic.mp4` and add a trending sound in the
  TikTok editor at 5-10 % volume under the voice — choose one from the Commercial Music Library if the account is a
  business account.
- ≤ ~12 designed effects per minute, each on a visible event (the engine budgets this).

## 6. Caption, hashtags, cover

- Caption: one line of context + one question ("Nếu là bạn, bạn có mua lại không? 👇"). Searchable keywords in the
  first line — TikTok is a search engine for under-30s.
- Hashtags 3-6 (lint): 1-2 broad (#lichsu, #kienthuc), 2-3 niche (#baihocdautu), 1 series tag. No #fyp spam.
- Cover: 3-5 words, inside the centre 3:4 (the profile grid crop). A consistent cover style makes the profile read as
  a series → follows.
- Pin a comment with the sources. Reply to early comments (video replies to good questions = free next video).

## 7. Cadence and series

- Consistency beats volume: 3-7 posts a week at the channel's slots, same series names, same look.
- Every 5-10 videos, read `insights.md`; double down on the top hook type and pillar, retire the weakest pillar.
- A winner gets a part 2 within 48 h and a remake with a different hook a few weeks later.

## 8. Honesty and policy

- Label AI-generated content (TikTok's AI-generated content label) when the voice or visuals are AI-made.
- No impersonation, no fake news formats, no invented testimonials or "I made $X" claims.
- TikTok restricts unoriginal / mass-produced duplicate content from For You: each short needs its own research,
  hook and pictures.
- Finance/health: education only, disclaimer in caption + end card (lint).
