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
    # state-change scenes (canvas.py): the picture changes while the voice explains
    "scenario": {"required": ["bars"], "optional": ["kicker", "heading", "cue", "before_label", "after_label", "takeaway", "takeaway_cue",
                                                    "prefix", "suffix", "decimals", "max"]},
    "board": {"required": [], "optional": ["regions", "board_id", "focus", "overview", "overview_cue", "line", "line_cue", "kicker",
                                           "start"]},
}
# fields any picture (a visual, a shot, an item, a region) may carry
COMMON = ["concept", "color", "action"]
TEXT_LED = ("statement", "stat", "quote", "list")  # pictures made of words (storyboard lint)
SHOT_MAX_S = 8.0  # one picture held longer than this, with no declared hold, reads as a slide
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
    ids, boards = set(), set()
    src_ids = {s["id"] for s in L.get("sources", [])}
    _validate_concepts(L["meta"].get("concepts"))
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
            if r not in v and not (r == "icon" and v.get("concept")):  # a concept brings its own picture
                raise LessonError(f"{where}: visual '{t}' needs '{r}'")
        for j, sh in enumerate(v.get("shots", []) if t == "shots" else []):
            st = sh.get("type")
            if st not in VISUALS or st in ("shots", "question", "hook"):
                raise LessonError(f"{where}: shot {j} type must be a picture type, not {st!r}")
            for r in VISUALS[st]["required"]:
                if r not in sh and not (r == "icon" and sh.get("concept")):
                    raise LessonError(f"{where}: shot {j} '{st}' needs '{r}'")
        if t == "scenario" and not (isinstance(v["bars"], list) and 1 <= len(v["bars"]) <= 3
                                    and all(isinstance(x, dict) and {"label", "before", "after"} <= set(x) for x in v["bars"])):
            raise LessonError(f"{where}: scenario 'bars' is 1-3 of {{label, before, after}}")
        if t == "board":
            if v.get("regions") is not None and not (isinstance(v["regions"], list) and 2 <= len(v["regions"]) <= 6
                                                     and all(isinstance(x, dict) and x.get("label") for x in v["regions"])):
                raise LessonError(f"{where}: board 'regions' is 2-6 of {{icon|concept, label}}")
            if not v.get("regions") and v.get("board_id") not in boards:
                raise LessonError(f"{where}: a board needs 'regions' (or a 'board_id' drawn by an earlier beat)")
            if v.get("board_id") and v.get("regions"):
                boards.add(v["board_id"])
        for s in b.get("sources", []):
            if s not in src_ids:
                raise LessonError(f"{where}: unknown source '{s}'")


def _validate_concepts(cs) -> None:
    if cs is None:
        return
    if not isinstance(cs, list):
        raise LessonError("meta.concepts is a list of {id, visual, color, shows, omits}")
    seen = set()
    for c in cs:
        if not isinstance(c, dict) or not c.get("id") or not c.get("visual"):
            raise LessonError(f"meta.concepts: every concept needs an 'id' and a 'visual' (an icon or a scene type): {c!r}")
        if c["id"] in seen:
            raise LessonError(f"meta.concepts: duplicate id '{c['id']}'")
        seen.add(c["id"])
        if c.get("color") not in (None, "a", "b"):
            raise LessonError(f"meta.concepts '{c['id']}': color is 'a' (gold) or 'b' (coral)")


def pictures(L: dict):
    """Every drawn thing in the lesson as (beat id, path, element): visuals, shots, and the items/regions/bars/sides
    inside them (anything that may carry an icon, a concept or a colour)."""
    def walk(bid, path, x):
        if isinstance(x, dict):
            if x.get("type") or x.get("icon") or x.get("concept") or x.get("color"):
                yield bid, path, x
            for k, y in x.items():
                if k not in ("type",) and not k.startswith("_"):
                    yield from walk(bid, f"{path}.{k}", y)
        elif isinstance(x, list):
            for i, y in enumerate(x):
                yield from walk(bid, f"{path}[{i}]", y)
    for b in L["beats"]:
        yield from walk(b["id"], "visual", b["visual"])


def concept_lint(L: dict) -> tuple[list[str], list[str]]:
    """One picture per idea for the whole film (meta.concepts): a beat that tags `concept` must draw it with the
    registered picture and colour; a concept says what the metaphor shows and where it stops (`shows`, `omits`)."""
    from .metaphors import ICONS

    errors, warns = [], []
    cs = {c["id"]: c for c in L["meta"].get("concepts") or []}
    if not cs:
        if any(el.get("concept") for _, _, el in pictures(L)):
            errors.append("a beat tags a 'concept' but meta.concepts is empty: register each idea once (id, visual, color, shows, omits)")
        return errors, warns
    by_visual: dict[str, list[str]] = {}
    for c in cs.values():
        if c["visual"] not in ICONS and c["visual"] not in VISUALS:
            errors.append(f"concept '{c['id']}': visual '{c['visual']}' is neither an icon nor a scene type")
        if not c.get("shows") or not c.get("omits"):
            warns.append(f"concept '{c['id']}': write what the picture shows and where the metaphor stops ('shows', 'omits'), "
                         "and say the limit on camera")
        by_visual.setdefault(c["visual"], []).append(c["id"])
    for vis, ids in by_visual.items():
        if len(ids) > 1:
            warns.append(f"concepts {ids} share the picture '{vis}': two ideas drawn alike blur into one")
    used = set()
    for bid, path, el in pictures(L):
        cid = el.get("concept")
        if not cid:
            continue
        if cid not in cs:
            errors.append(f"{bid}: {path} tags unknown concept '{cid}' (register it in meta.concepts)")
            continue
        used.add(cid)
        c = cs[cid]
        t = el.get("type")
        drawn = el.get("icon") or (t if t and t != "icon" else None)
        if drawn and drawn != c["visual"]:
            errors.append(f"{bid}: {path} draws concept '{cid}' as '{drawn}', but it is registered as '{c['visual']}' "
                          "(one picture per idea for the whole film)")
        if el.get("color") and c.get("color") and el["color"] != c["color"]:
            warns.append(f"{bid}: {path} colours concept '{cid}' '{el['color']}', registered '{c['color']}'")
    for cid in cs:
        if cid not in used:
            warns.append(f"concept '{cid}' is registered but never drawn: tag the beats that show it ('concept': '{cid}')")
    return errors, warns


def shot_list(L: dict) -> list[dict]:
    """The pictures in screen order with an estimated hold: [{beat, i, v, seconds, act, hold}]. A `shots` visual splits
    its line at the shots' cue words; timing is estimated from the words (lint runs before any voice exists)."""
    meta = L["meta"]
    speed, lang = float(meta.get("speed", 1.0)), meta.get("lang", "en")
    out = []
    for b in L["beats"]:
        v = b["visual"]
        total = 0.45 + est_seconds(b["narration"], float(b.get("speed", speed)), lang) + 0.65 if b["narration"].strip() else float(v.get("hold", 3.0))
        items = v["shots"] if v["type"] == "shots" else [v]
        nw = [w.lower() for w in b["narration"].split()]
        starts = [0.0]
        for i, sh in enumerate(items[1:], 1):
            frac = i / len(items)
            if sh.get("cue"):
                cw = sh["cue"].lower().split()
                hit = next((j for j in range(len(nw)) if [re.sub(r"[^\w%$£-]", "", x) for x in nw[j:j + len(cw)]] ==
                            [re.sub(r"[^\w%$£-]", "", x) for x in cw]), None)
                if hit is not None:
                    frac = hit / max(1, len(nw))
            starts.append(max(starts[-1], 0.45 + frac * (total - 1.1)))
        ends = starts[1:] + [total]
        for i, (sh, t0, t1) in enumerate(zip(items, starts, ends)):
            out.append({"beat": b["id"], "i": i, "v": sh, "seconds": round(t1 - t0, 1), "act": b["act"],
                        "hold": bool(b.get("hold"))})
    return out


def text_led(v: dict) -> bool:
    return v.get("type") in TEXT_LED and not v.get("icon")


def storyboard_lint(L: dict) -> list[str]:
    """A slide show is a row of word cards. Warnings (huashu-art-motion's storyboard rules, measured on explainers):
    text-led pictures ≤ 30 %; the first and last content pictures are pictures, not words; no picture held > 8 s
    without a declared hold; if shots name their `action` (the verb the object does), every shot should, and the
    same action three times running reads as one shot repeated."""
    w = []
    shots = [s for s in shot_list(L) if s["v"].get("type") not in ("title", "end", "question")]
    if not shots:
        return w
    tl = [s for s in shots if text_led(s["v"])]
    share = len(tl) / len(shots)
    if share > 0.3:
        w.append(f"{len(tl)} of {len(shots)} pictures ({share:.0%}) are text-led (statement/stat/quote/list with no icon): "
                 "keep it ≤ 30 %, draw the idea instead")
    for which, s in (("first", shots[0]), ("last", shots[-1])):
        if text_led(s["v"]):
            w.append(f"{s['beat']}: the {which} content picture is text-led ({s['v']['type']}): open and close on an image")
    for s in shots:
        if s["seconds"] > SHOT_MAX_S and not s["hold"] and s["v"].get("type") not in ("board", "scenario", "chart", "timeline"):
            where = f"{s['beat']}" + (f" shot {s['i']}" if s["i"] else "")
            w.append(f"{where}: one picture held ~{s['seconds']:.1f}s (> {SHOT_MAX_S:.0f}s): add a shot on a cue word, or "
                     "declare 'hold' on the beat")
    acts = [s["v"].get("action") for s in shots]
    if any(acts):
        missing = [f"{s['beat']}#{s['i']}" for s in shots if not s["v"].get("action")]
        if missing:
            w.append(f"shots without an 'action' verb (what the object does): {missing[:8]}{' …' if len(missing) > 8 else ''}")
        for i in range(2, len(acts)):
            if acts[i] and acts[i] == acts[i - 1] == acts[i - 2]:
                w.append(f"{shots[i]['beat']}: the action '{acts[i]}' three shots running: vary the move")
    return w


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
    ce, cw = concept_lint(L)
    errors += ce
    warns += cw
    for b in beats:  # a strike that waits for a word the narrator never says lands at a guess
        for _, path, el in pictures({"beats": [b]}):
            for k in ("strike_cue",):
                if el.get(k) and not re.search(r"(?<!\w)" + re.escape(el[k].lower()), b["narration"].lower()):
                    warns.append(f"{b['id']}: {path}.{k} '{el[k]}' is not in the narration")
    return {"errors": errors, "warnings": warns, "storyboard": storyboard_lint(L),
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
