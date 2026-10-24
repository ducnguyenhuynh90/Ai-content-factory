"""The recipe: a single JSON document describing the whole edit.

It is the contract between the director (a human, Claude, or the heuristic
auto-director) and the renderer. Every field is optional except sources and
segments; the look fills the rest.
"""

from __future__ import annotations

import json
from pathlib import Path

ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "21:9": (2560, 1080)}
TRANSITIONS = {"cut", "dissolve", "dip", "flash", "whip", "zoom", "slide", "wipe"}

EXAMPLE = {
    "version": 1,
    "look": "prestige",
    "format": {"aspect": "16:9", "fps": 30},
    "sources": {"A": "footage/interview.mp4", "B": "footage/broll_city.mp4"},
    "title": {"text": "The Long Road Home", "kicker": "A Northlight Film", "subtitle": "", "mode": "auto"},
    "cold_open": [{"source": "B", "start": 12.0, "end": 15.2}],
    "segments": [
        {"source": "B", "start": 0.0, "end": 4.0, "transition": "cut", "beat": "ESTABLISH"},
        {"source": "A", "start": 3.1, "end": 9.8, "transition": "dissolve", "beat": "VOICE"},
    ],
    "lower_thirds": [{"segment": 1, "offset": 0.8, "name": "Mai Tran", "role": "Director"}],
    "chapters": [],
    "ending": {"title": "The Long Road Home", "tagline": "Now streaming", "cta": "Watch the film",
               "handle": "northlight.studio", "credits": [["Directed by", "Mai Tran"]]},
    "captions": {"words": None},
    "music": {"file": None},
    "sfx": True,
    "output": "final.mp4",
}


class RecipeError(ValueError):
    pass


def load(path_or_dict) -> dict:
    if isinstance(path_or_dict, dict):
        r, base = dict(path_or_dict), Path.cwd()
    else:
        p = Path(path_or_dict)
        r, base = json.loads(p.read_text()), p.parent.resolve()
    return normalize(r, base)


def normalize(r: dict, base: Path) -> dict:
    if not r.get("sources"):
        raise RecipeError("recipe needs 'sources'")
    if not r.get("segments"):
        raise RecipeError("recipe needs at least one segment")
    fmt = dict(r.get("format") or {})
    if "width" not in fmt:
        fmt["width"], fmt["height"] = ASPECTS.get(fmt.get("aspect", "16:9"), ASPECTS["16:9"])
    fmt.setdefault("fps", 30)
    r["format"] = fmt

    def absp(p):
        if not p:
            return p
        q = Path(p)
        return str(q if q.is_absolute() else (base / q).resolve())

    r["sources"] = {k: absp(v) for k, v in r["sources"].items()}
    for i, s in enumerate([*r.get("cold_open", []), *r["segments"]]):
        if s["source"] not in r["sources"]:
            raise RecipeError(f"segment {i} uses unknown source '{s['source']}'")
        if float(s["end"]) <= float(s["start"]):
            raise RecipeError(f"segment {i} has end <= start")
        t = s.get("transition", "cut")
        if t not in TRANSITIONS:
            raise RecipeError(f"segment {i}: unknown transition '{t}' (use one of {sorted(TRANSITIONS)})")
    for i, c in enumerate(r.get("cutaways") or []):
        if c["source"] not in r["sources"]:
            raise RecipeError(f"cutaway {i} uses unknown source '{c['source']}'")
    r.setdefault("cutaways", [])
    r.setdefault("look", "prestige")
    r.setdefault("cold_open", [])
    r.setdefault("lower_thirds", [])
    r.setdefault("chapters", [])
    r.setdefault("title", None)
    r.setdefault("ending", None)
    r.setdefault("sfx", True)
    r.setdefault("output", "final.mp4")
    music = r.get("music") or {}
    if music.get("file"):
        music["file"] = absp(music["file"])
    r["music"] = music
    cap = r.get("captions") or {}
    if isinstance(cap.get("words"), str):
        cap["words"] = absp(cap["words"])
    r["captions"] = cap
    if r.get("ending") and r["ending"].get("logo"):
        r["ending"]["logo"] = absp(r["ending"]["logo"])
    if not Path(r["output"]).is_absolute():
        r["output"] = str((base / r["output"]).resolve())
    return r


def dump(r: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(r, indent=2, ensure_ascii=False))
