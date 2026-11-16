"""Stickman actors for stage scenes, drawn in code (no downloads, no image model).

The look follows the "minimal line art" explainer style: a white round head with a bold black outline, black
stick limbs with round caps, an expressive face, and at most one colour accent (a tie) so each character stays
recognisable across a whole series. Stickmen mix freely with Fluent Emoji props on the same stage.

Name grammar (case-insensitive), usable anywhere an emoji asset name is accepted, including `swap`:

    "Stick <pose> [<face>] [<colour>] [cap] [glasses]"
    "Stick stand happy red"   "Stick slump sad red cap"   "Stick cheer joy blue glasses"

A real person is played by a generic stickman with a name label, never a likeness.
"""

from __future__ import annotations

import re

INK = "#1A1A1A"
COLOURS = {"red": "#D7263D", "blue": "#2B6CE0", "orange": "#F28C28", "green": "#2E9E5B", "purple": "#7A4FD6",
           "yellow": "#F2C230", "grey": "#8A8F98", "gray": "#8A8F98"}

# Joints in a 200 x 200 box, feet on the bottom edge. head = (cx, cy); arms/legs = (elbow|knee, hand|foot).
_BASE = {"head": (100, 40), "neck": (100, 72), "hip": (100, 132),
         "la": ((84, 106), (78, 134)), "ra": ((116, 106), (122, 134)),
         "ll": ((91, 163), (85, 196)), "rl": ((109, 163), (115, 196))}
POSES = {
    "stand": {},
    "wave": {"ra": ((130, 70), (140, 40))},
    "cheer": {"la": ((76, 60), (66, 30)), "ra": ((124, 60), (134, 30)), "ll": ((86, 163), (76, 196)),
              "rl": ((114, 163), (124, 196))},
    "point": {"ra": ((128, 82), (158, 74))},
    "think": {"ra": ((126, 104), (110, 72)), "la": ((84, 104), (112, 114))},
    "shrug": {"la": ((72, 96), (62, 76)), "ra": ((128, 96), (138, 76))},
    "shocked": {"la": ((72, 80), (54, 62)), "ra": ((128, 80), (146, 62)), "ll": ((86, 163), (76, 196)),
                "rl": ((114, 163), (124, 196))},
    "hold": {"la": ((88, 112), (116, 108)), "ra": ((118, 108), (142, 100))},
    "facepalm": {"ra": ((134, 86), (126, 46))},
    "slump": {"head": (106, 52), "neck": (103, 82), "hip": (98, 138), "la": ((96, 112), (100, 142)),
              "ra": ((112, 112), (116, 142)), "ll": ((92, 166), (86, 196)), "rl": ((106, 166), (112, 196))},
    "run": {"head": (110, 42), "neck": (106, 74), "hip": (96, 132), "la": ((82, 96), (70, 116)),
            "ra": ((124, 96), (138, 80)), "ll": ((120, 158), (110, 190)), "rl": ((82, 164), (62, 178))},
    "walk": {"la": ((92, 106), (98, 134)), "ra": ((110, 106), (104, 134)), "ll": ((98, 163), (82, 196)),
             "rl": ((106, 163), (122, 196))},
    "sit": {"hip": (100, 150), "la": ((86, 112), (104, 140)), "ra": ((114, 112), (128, 140)),
            "ll": ((126, 150), (128, 196)), "rl": ((120, 154), (122, 196)), "neck": (100, 86), "head": (100, 54)},
}
FACES = ("happy", "joy", "sad", "worried", "shocked", "neutral", "determined", "smirk", "tired")
EXTRAS = ("cap", "glasses")


class StickError(ValueError):
    pass


def is_stick(name: str) -> bool:
    return name.strip().lower().startswith("stick ")


def parse(name: str) -> dict:
    toks = name.strip().lower().split()[1:]
    if not toks or toks[0] not in POSES:
        raise StickError(f"{name!r}: pose must be one of {list(POSES)}")
    spec = {"pose": toks[0], "face": "happy", "colour": None, "extras": set()}
    for t in toks[1:]:
        if t in FACES:
            spec["face"] = t
        elif t in COLOURS:
            spec["colour"] = t
        elif t in EXTRAS:
            spec["extras"].add(t)
        else:
            raise StickError(f"{name!r}: unknown word {t!r}; faces {list(FACES)}, colours {list(COLOURS)}, extras {list(EXTRAS)}")
    return spec


def exists(name: str) -> bool:
    try:
        parse(name)
        return True
    except StickError:
        return False


def search(word: str) -> list[str]:
    w = word.lower()
    return [f"Stick {p} happy" for p in POSES if w in p] + [f"Stick stand {f}" for f in FACES if w in f]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _face(cx, cy, face) -> str:
    dot = lambda x, y, r=3.6: f'<circle cx="{x}" cy="{y}" r="{r}" fill="{INK}"/>'
    s = f'stroke="{INK}" stroke-width="3.2" stroke-linecap="round" fill="none"'
    ex, ey = 8.5, cy - 4
    eyes = dot(cx - ex, ey) + dot(cx + ex, ey)
    m = cy + 9
    if face == "happy":
        return eyes + f'<path d="M{cx - 8} {m - 2} Q{cx} {m + 7} {cx + 8} {m - 2}" {s}/>'
    if face == "joy":
        return (f'<path d="M{cx - 12} {ey + 1} Q{cx - ex} {ey - 6} {cx - 5} {ey + 1}" {s}/>'
                f'<path d="M{cx + 5} {ey + 1} Q{cx + ex} {ey - 6} {cx + 12} {ey + 1}" {s}/>'
                f'<path d="M{cx - 10} {m - 3} Q{cx} {m + 12} {cx + 10} {m - 3} Z" fill="{INK}"/>')
    if face == "sad":
        return (eyes + f'<path d="M{cx - 13} {ey - 6} L{cx - 5} {ey - 9}" {s}/><path d="M{cx + 13} {ey - 6} L{cx + 5} {ey - 9}" {s}/>'
                f'<path d="M{cx - 8} {m + 4} Q{cx} {m - 4} {cx + 8} {m + 4}" {s}/>')
    if face == "worried":
        return (eyes + f'<path d="M{cx - 13} {ey - 7} L{cx - 5} {ey - 10}" {s}/><path d="M{cx + 13} {ey - 7} L{cx + 5} {ey - 10}" {s}/>'
                f'<path d="M{cx - 9} {m + 1} q 4.5 -4 9 0 t 9 0" {s}/>')
    if face == "shocked":
        return (f'<circle cx="{cx - ex}" cy="{ey}" r="6" fill="#FFF" stroke="{INK}" stroke-width="2.6"/>{dot(cx - ex, ey, 2.6)}'
                f'<circle cx="{cx + ex}" cy="{ey}" r="6" fill="#FFF" stroke="{INK}" stroke-width="2.6"/>{dot(cx + ex, ey, 2.6)}'
                f'<ellipse cx="{cx}" cy="{m + 2}" rx="4.5" ry="6" fill="{INK}"/>')
    if face == "determined":
        return (eyes + f'<path d="M{cx - 14} {ey - 10} L{cx - 4} {ey - 6}" {s}/><path d="M{cx + 14} {ey - 10} L{cx + 4} {ey - 6}" {s}/>'
                f'<path d="M{cx - 7} {m + 1} L{cx + 7} {m + 1}" {s}/>')
    if face == "smirk":
        return eyes + f'<path d="M{cx - 7} {m + 1} Q{cx + 3} {m + 3} {cx + 9} {m - 4}" {s}/>'
    if face == "tired":
        return (f'<path d="M{cx - 13} {ey} L{cx - 4} {ey}" {s}/><path d="M{cx + 4} {ey} L{cx + 13} {ey}" {s}/>'
                f'<path d="M{cx - 6} {m + 2} L{cx + 6} {m + 1}" {s}/>')
    return eyes + f'<path d="M{cx - 7} {m + 1} L{cx + 7} {m + 1}" {s}/>'  # neutral


def svg(name: str) -> str:
    spec = parse(name)
    p = {**_BASE, **POSES[spec["pose"]]}
    (hx, hy), (nx, ny), (px, py) = p["head"], p["neck"], p["hip"]
    sx, sy = nx + (px - nx) * 0.15, ny + (py - ny) * 0.15  # shoulders
    limb = lambda a, b, c: f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]} L{c[0]} {c[1]}"/>'
    body = (f'<g stroke="{INK}" stroke-width="7.5" stroke-linecap="round" stroke-linejoin="round" fill="none">'
            f'<path d="M{nx} {ny} Q{(nx + px) / 2 + 2} {(ny + py) / 2} {px} {py}"/>'
            + limb((sx, sy), *p["la"]) + limb((sx, sy), *p["ra"]) + limb((px, py), *p["ll"]) + limb((px, py), *p["rl"]) + "</g>")
    tie = ""
    if spec["colour"]:
        c = COLOURS[spec["colour"]]
        tie = (f'<path d="M{nx - 5} {ny + 2} L{nx + 5} {ny + 2} L{nx + 3} {ny + 8} L{nx + 6} {ny + 30} L{nx} {ny + 37} '
               f'L{nx - 6} {ny + 30} L{nx - 3} {ny + 8} Z" fill="{c}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>')
    r = 30
    head = f'<circle cx="{hx}" cy="{hy}" r="{r}" fill="#FFFFFF" stroke="{INK}" stroke-width="5.5"/>' + _face(hx, hy, spec["face"])
    extra = ""
    if "glasses" in spec["extras"]:
        extra += (f'<g stroke="{INK}" stroke-width="2.6" fill="none"><circle cx="{hx - 8.5}" cy="{hy - 4}" r="7.5"/>'
                  f'<circle cx="{hx + 8.5}" cy="{hy - 4}" r="7.5"/><path d="M{hx - 1} {hy - 4} L{hx + 1} {hy - 4}"/></g>')
    if "cap" in spec["extras"]:
        c = COLOURS.get(spec["colour"] or "", INK)
        extra += (f'<path d="M{hx - r + 1} {hy - 8} A{r - 1} {r - 1} 0 0 1 {hx + r - 1} {hy - 8} Z" fill="{c}" stroke="{INK}" stroke-width="4"/>'
                  f'<path d="M{hx + r - 4} {hy - 9} L{hx + r + 14} {hy - 7}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="400" height="400">'
            f'{body}{tie}{head}{extra}</svg>')
