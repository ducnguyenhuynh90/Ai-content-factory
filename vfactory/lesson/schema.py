"""lesson.json: the contract between the writer (Claude, via the lesson-video skill) and the renderer.

{
  "meta": {"series": "...", "title": "...", "subtitle": "...", "topic": "investing", "angle": "history|person|concept",
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
    "title": {"required": ["title"], "optional": ["kicker", "subtitle"]},
    "statement": {"required": ["text"], "optional": ["highlight", "kicker"]},
    "stat": {"required": ["value", "label"], "optional": ["from", "prefix", "suffix", "note"]},
    "chart": {"required": ["points"], "optional": ["title", "unit", "annotations", "y_label", "x_label"]},
    "timeline": {"required": ["events"], "optional": ["title"]},
    "quote": {"required": ["text", "by"], "optional": ["attribution", "year"]},
    "portrait": {"required": ["name"], "optional": ["years", "role", "initials"]},
    "principle": {"required": ["n", "name"], "optional": ["line"]},
    "compare": {"required": ["left", "right"], "optional": ["title"]},
    "list": {"required": ["items"], "optional": ["title", "check"]},
    "question": {"required": ["question"], "optional": ["choices", "answer", "think_seconds"]},
    "end": {"required": ["title"], "optional": ["cta", "next", "sources_line", "disclaimer"]},
}
WPM = 150.0  # documentary narration pace (Vox guide; Kokoro at speed 0.95 lands close)


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
        if not b.get("narration", "").strip():
            raise LessonError(f"{where}: empty narration")
        v = b.get("visual") or {}
        t = v.get("type")
        if t not in VISUALS:
            raise LessonError(f"{where}: visual.type must be one of {list(VISUALS)}")
        for r in VISUALS[t]["required"]:
            if r not in v:
                raise LessonError(f"{where}: visual '{t}' needs '{r}'")
        for s in b.get("sources", []):
            if s not in src_ids:
                raise LessonError(f"{where}: unknown source '{s}'")


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9'’£$€%-]+", text)


def est_seconds(text: str, speed: float = 1.0) -> float:
    return len(words(text)) / (WPM * speed) * 60


def lint(L: dict) -> dict:
    """Learning-science and craft checks. Returns {errors, warnings, stats}. Errors block rendering."""
    errors, warns = [], []
    meta = L["meta"]
    beats = L["beats"]
    speed = float(meta.get("speed", 1.0))
    total_words = sum(len(words(b["narration"])) for b in beats)
    est = sum(est_seconds(b["narration"], speed) for b in beats) + sum(
        float(b["visual"].get("think_seconds", 3.0)) for b in beats if b["visual"]["type"] == "question")
    lo, hi = meta.get("target_minutes", [3, 5])
    if est < lo * 60 * 0.9:
        warns.append(f"estimated {est / 60:.1f} min is under the {lo}-{hi} min target: add an example or a story beat")
    if est > hi * 60 * 1.05:
        errors.append(f"estimated {est / 60:.1f} min is over the {hi} min target: cut words, not scenes")
    acts = [b["act"] for b in beats]
    if acts[0] != "hook":
        errors.append("the first beat must be the hook (start inside the story, never 'today we will...')")
    if re.search(r"\b(today we|in this video|welcome|let'?s talk about|hi everyone)\b", beats[0]["narration"], re.I):
        errors.append("the hook opens with a preamble; start with a concrete fact, image or question")
    if len(words(beats[0]["narration"])) > 45:
        warns.append("hook is long: the first line should land in ~10 seconds")
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
        if n > 70:
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
        claims = re.search(r"\b(19|20|17|16)\d\d\b|£|\$|percent|million|billion|thousand|pounds", b["narration"] + screen, re.I)
        if claims and not b.get("sources") and b["act"] not in ("question", "recap", "close", "principle"):
            warns.append(f"{b['id']}: contains a number or date with no source id")
        if b.get("certainty") in ("disputed", "attributed") and not re.search(
                r"\b(reportedly|attributed|legend|lore|probably|may have|story goes|is said|disputed|estimate|about|roughly)\b",
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
