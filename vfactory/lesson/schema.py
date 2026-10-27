"""lesson.json: the contract between the writer (Claude, via the lesson-video skill) and the renderer.

{
  "meta": {"series": "...", "title": "...", "subtitle": "...", "topic": "investing", "angle": "history|person|concept", "lang": "en|vi",
           "audience": "...", "aspect": "4:3", "target_minutes": [3, 5], "voice": "bm_george", "speed": 0.95,
           "disclaimer": "Educational content, not financial advice.", "learning_goals": ["..."]},
  "sources": [{"id": "odlyzko2019", "cite": "Odlyzko, Notes and Records 73(1), 2019", "url": "..."}],
  "principles": [{"name": "Price is not value", "line": "..."}],
  "beats": [{"id": "b01", "act": "hook", "narration": "spoken words, numbers as words",
             "visual": {"type": "title", ...}, "sources": ["odlyzko2019"], "certainty": "established|estimate|disputed|attributed"}],
  "pronounce": {"Odlyzko": "oh-DLIZ-ko"}
}

Visual types and their fields: see VISUALS below.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ACTS = ("hook", "context", "story", "misconception", "complication", "turn", "principle", "example", "question",
        "recap", "close")
VISUALS = {
    "hook": {"required": ["lines"], "optional": ["points", "crash_cue", "peak_label", "end_label", "kicker"]},
    "title": {"required": ["title"], "optional": ["kicker", "subtitle"]},
    "statement": {"required": ["text"], "optional": ["highlight", "kicker", "strike", "replace", "strike_cue"]},
    "stat": {"required": ["value", "label"], "optional": ["from", "prefix", "suffix", "note", "decimals", "cue"]},
    "chart": {"required": ["points"], "optional": ["title", "unit", "annotations", "y_label", "x_label"]},
    "timeline": {"required": ["events"], "optional": ["title"]},
    "quote": {"required": ["text", "by"], "optional": ["attribution", "year"]},
    "portrait": {"required": ["name"], "optional": ["years", "role", "initials"]},
    "principle": {"required": ["n", "name"], "optional": ["line"]},
    "compare": {"required": ["left", "right"], "optional": ["title"]},
    "list": {"required": ["items"], "optional": ["title", "check"]},
    "question": {"required": ["question"], "optional": ["choices", "answer", "think_seconds"]},
    "end": {"required": ["title"], "optional": ["cta", "next", "sources_line", "disclaimer", "next_cue", "cta_cue", "sources_cue",
                                               "ask", "ask_cue", "ask_hint"]},
    # metaphor scenes (metaphors.py): the object on screen is the explanation
    "funnel": {"required": ["total"], "optional": ["keep", "label", "keep_label", "keep_cue", "cue", "start_full", "stat", "cols", "seed"]},
    "ladder": {"required": ["levels"], "optional": ["kicker", "heading", "top_cue", "tags"]},
    "venn": {"required": ["circles"], "optional": ["kicker", "heading", "center_label", "center_cue"]},
    "flywheel": {"required": [], "optional": ["kicker", "heading", "name", "line", "line_cue", "marks", "push_cues", "fast_cue",
                                             "from_angle", "to_angle", "ease", "spokes", "enter"]},
    "halo": {"required": ["items"], "optional": ["kicker", "heading", "label", "label_cue"]},
    "swap": {"required": ["from", "to"], "optional": ["kicker", "heading", "cue", "strike_cue", "line", "line_cue"]},
    "shots": {"required": ["shots"], "optional": []},
    "trio": {"required": ["items"], "optional": ["kicker", "heading", "cross", "line", "line_cue"]},
    "icon": {"required": ["icon"], "optional": ["kicker", "heading", "line", "line_cue", "steam", "motion", "motion_cue", "turns", "period"]},
    "climb": {"required": ["peak", "rest"], "optional": ["kicker", "heading", "stop_cue", "line", "line_cue"]},
    "book": {"required": ["title"], "optional": ["kicker", "heading", "author", "year", "facts"]},
    "company": {"required": ["name"], "optional": ["kicker", "heading", "art", "facts", "card"]},
    "rise": {"required": ["value"], "optional": ["kicker", "heading", "value_text", "value_label", "base_label", "cue", "stamp", "ranking",
                                               "pass_cue", "products", "why", "why_kicker", "why_cue"]},
}
WPM = 150.0  # documentary narration pace (Vox guide; Kokoro at speed 0.95 lands close)
# words (Vietnamese: syllables) per minute at speed 1.0; Piper vi_VN-vais1000 measured ~270, so speed 0.82 ≈ 220
WPM_BY_LANG = {"en": WPM, "vi": 270.0}


class LessonError(ValueError):
    pass


def load(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text())
    validate(data)
    return data


def validate(L: dict) -> None:
    for k in ("meta", "beats"):
        if k not in L:
            raise LessonError(f"lesson needs '{k}'")
    ids = set()
    src_ids = {s["id"] for s in L.get("sources", [])}
    for i, b in enumerate(L["beats"]):
        where = f"beat {i} ({b.get('id')})"
        if not b.get("id") or b["id"] in ids:
            raise LessonError(f"{where}: missing or duplicate id")
        ids.add(b["id"])
        if b.get("act") not in ACTS:
            raise LessonError(f"{where}: act must be one of {ACTS}")
        v = b.get("visual") or {}
        t = v.get("type")
        if not b.get("narration", "").strip() and not (t in ("title", "end") and v.get("hold")):
            raise LessonError(f"{where}: empty narration (only a title/end card with 'hold' seconds may be silent)")
        if t not in VISUALS:
            raise LessonError(f"{where}: visual.type must be one of {list(VISUALS)}")
        for r in VISUALS[t]["required"]:
            if r not in v:
                raise LessonError(f"{where}: visual '{t}' needs '{r}'")
        for j, sh in enumerate(v.get("shots", []) if t == "shots" else []):
            st = sh.get("type")
            if st not in VISUALS or st in ("shots", "question", "hook"):
                raise LessonError(f"{where}: shot {j} type must be a picture type, not {st!r}")
            for r in VISUALS[st]["required"]:
                if r not in sh:
                    raise LessonError(f"{where}: shot {j} '{st}' needs '{r}'")
        for s in b.get("sources", []):
            if s not in src_ids:
                raise LessonError(f"{where}: unknown source '{s}'")


def words(text: str) -> list[str]:
    return re.findall(r"[\w'’£$€%-]+", text)


def est_seconds(text: str, speed: float = 1.0, lang: str = "en") -> float:
    return len(words(text)) / (WPM_BY_LANG.get(lang, WPM) * speed) * 60


def lint(L: dict) -> dict:
    """Learning-science and craft checks. Returns {errors, warnings, stats}. Errors block rendering."""
    errors, warns = [], []
    meta = L["meta"]
    beats = L["beats"]
    speed = float(meta.get("speed", 1.0))
    lang = meta.get("lang", "en")
    total_words = sum(len(words(b["narration"])) for b in beats)
    est = sum(est_seconds(b["narration"], speed, lang) for b in beats) + sum(
        float(b["visual"].get("think_seconds", 3.0)) for b in beats if b["visual"]["type"] == "question")
    lo, hi = meta.get("target_minutes", [3, 5])
    if est < lo * 60 * 0.9:
        warns.append(f"estimated {est / 60:.1f} min is under the {lo}-{hi} min target: add an example or a story beat")
    if est > hi * 60 * 1.05:
        errors.append(f"estimated {est / 60:.1f} min is over the {hi} min target: cut words, not scenes")
    acts = [b["act"] for b in beats]
    errors += hook_errors(beats, lang)
    warns += hook_warnings(beats)
    if "misconception" not in acts and not any("misconception" in b.get("tags", []) for b in beats):
        warns.append("no misconception beat: name the wrong idea the viewer probably holds, then correct it "
                     "(Muller: confronting misconceptions roughly doubled learning vs. clear exposition alone)")
    if "question" not in acts:
        warns.append("no retrieval question: ask the viewer to recall or apply a principle before the recap (testing effect)")
    if "recap" not in acts:
        warns.append("no recap beat: restate the principles in one place")
    principles = L.get("principles", [])
    if not 2 <= len(principles) <= 4:
        warns.append(f"{len(principles)} principles: aim for 2-4 (cognitive load); one big idea per lesson, its principles as steps")
    for b in beats:
        n = len(words(b["narration"]))
        if n > 70 * WPM_BY_LANG.get(lang, WPM) / WPM:
            warns.append(f"{b['id']}: {n} words in one beat; split it (one idea per scene)")
        if re.search(r"\d", b["narration"]) and not b.get("allow_digits"):
            warns.append(f"{b['id']}: digits in narration; write numbers as they are spoken ('seventeen twenty', 'a thousand pounds')")
        screen = _screen_text(b["visual"])
        if screen and len(words(screen)) > 18 and b["visual"]["type"] not in ("quote", "list", "end", "timeline", "compare"):
            warns.append(f"{b['id']}: {len(words(screen))} words on screen; keep on-screen text to key phrases (redundancy principle)")
        if screen and b["visual"]["type"] in ("statement",):
            ov = _overlap(screen, b["narration"])
            if ov > 0.85 and len(words(screen)) > 8:
                warns.append(f"{b['id']}: on-screen text repeats the narration word for word; show the key phrase instead")
        claims = re.search(r"\b(19|20|17|16)\d\d\b|£|\$|percent|million|billion|thousand|pounds|phần trăm|triệu|tỷ|nghìn",
                           b["narration"] + screen, re.I)
        if claims and not b.get("sources") and b["act"] not in ("question", "recap", "close", "principle"):
            warns.append(f"{b['id']}: contains a number or date with no source id")
        if b.get("certainty") in ("disputed", "attributed") and not re.search(
                r"\b(reportedly|attributed|legend|lore|probably|may have|story goes|is said|disputed|estimate|about|roughly|"
                r"khoảng|ước tính|được cho là|tương truyền|có lẽ|người ta kể|gây tranh cãi|chưa kiểm chứng)\b",
                b["narration"], re.I):
            errors.append(f"{b['id']}: marked {b['certainty']} but the narration states it as fact; say so out loud")
    if meta.get("topic", "").lower() in ("investing", "investment", "finance", "money") and not meta.get("disclaimer"):
        errors.append("finance lesson without a disclaimer (educational, not financial advice)")
    for b in beats:
        if re.search(r"\b(guaranteed|can'?t lose|risk-free|always goes up|get rich quick)\b", b["narration"], re.I):
            errors.append(f"{b['id']}: promissory language ('guaranteed', 'can't lose'...) has no place in an investing lesson")
    if not L.get("sources"):
        errors.append("no sources: every lesson lists the sources its facts come from")
    return {"errors": errors, "warnings": warns,
            "stats": {"beats": len(beats), "words": total_words, "est_minutes": round(est / 60, 2),
                      "principles": len(principles), "acts": acts}}


# English, then Vietnamese
TENSION = re.compile(r"\b(but|then|yet|until|lost|lose|never|wrong|failed|crash\w*|ruin\w*|gone|instead|except|why|how|"
                     r"nhưng|vậy mà|thế mà|rồi|chỉ|mất|không bao giờ|sai|thất bại|sụp đổ|phá sản|kẻ thù|tại sao|vì sao)\b|\?", re.I)
SPECIFIC = re.compile(r"\b([A-Z][a-z]+|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion|"
                      r"seventeen|eighteen|nineteen|twenty|percent|"
                      r"một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|mươi|trăm|nghìn|ngàn|triệu|tỷ|phần trăm)\b")
PROMISE = re.compile(r"\b(you'?ll|you will|by the end|in the next|here'?s (how|why|what)|three|two|four|rules?|lessons?|"
                     r"principles?|the reason|stop it|avoid|"
                     r"bạn sẽ|đến cuối|trong vài phút|ba|bốn|bài học|nguyên tắc|lý do|cách)\b", re.I)
PREAMBLE = re.compile(r"\b(today we|in this video|welcome|let'?s talk about|hi everyone|hey guys|"
                      r"hôm nay chúng ta|trong video này|xin chào|chào mừng|chào các bạn)\b", re.I)


def hook_errors(beats: list[dict], lang: str = "en") -> list[str]:
    """The first five seconds decide whether anyone sees the rest (hook-writing skill; HyperFrames vertical guide)."""
    e = []
    if beats[0]["act"] != "hook":
        e.append("the first beat must be the hook (start inside the story, never 'today we will...')")
        return e
    h = beats[0]
    if PREAMBLE.search(h["narration"]):
        e.append("the hook opens with a preamble; start mid-story with a concrete fact, image or question")
    hs = est_seconds(h["narration"], float(h.get("speed", 1.0)), lang)
    if hs > 7.5:
        e.append(f"the hook takes ~{hs:.0f}s to say; the paradox must land inside ~5s (≤ 16 words)")
    if h["visual"]["type"] in ("title", "end"):
        e.append("frame 0 is a title card: open on the hook image/claim (visual type 'hook' or 'statement'); the title comes after")
    return e


def hook_warnings(beats: list[dict]) -> list[str]:
    w = []
    if beats[0]["act"] != "hook":
        return w
    h = beats[0]["narration"]
    if not TENSION.search(h):
        w.append("hook has no tension: add the turn (but/then/lost/never/why...) that makes it a paradox, not a fact")
    if not SPECIFIC.search(h):
        w.append("hook has no concrete anchor: name the person, the year or the number")
    if len(beats) > 1 and not PROMISE.search(beats[1]["narration"]):
        w.append("beat 2 should open a loop: promise the payoff for staying ('by the end you'll see... and three rules...')")
    for i, b in enumerate(beats[2:], 2):
        if b["visual"]["type"] == "title" and i > 3:
            w.append("the title card comes late; keep it within the first ~20 seconds, right after the hook")
    return w


def _screen_text(v: dict) -> str:
    parts = []
    for k in ("title", "text", "label", "subtitle", "name", "line", "question"):
        if isinstance(v.get(k), str):
            parts.append(v[k])
    for k in ("items",):
        if isinstance(v.get(k), list):
            parts += [x if isinstance(x, str) else x.get("text", "") for x in v[k]]
    return " ".join(parts)


def _overlap(a: str, b: str) -> float:
    wa = [w.lower() for w in words(a)]
    wb = {w.lower() for w in words(b)}
    return sum(1 for w in wa if w in wb) / max(1, len(wa))
