"""Rigged sticker characters: generic, cute, everyday Vietnamese people drawn from SVG parts, moved by keyframes.

A character is a `look` (colours + a few choices) drawn as a puppet whose parts pivot where a body bends:

    mv (walk / jump, screen px) > pose (sit, squash) > legs L/R (hip) · breathe group > hair-back, torso, neck,
    head (neck: tilt, nod) > [ears, face, eyes (blink), brows, mouth (expression / talk)], arms L/R (shoulder) >
    forearm (elbow) > hand

Every pivoting part is wrapped in a `translate(pivot)` group and drawn around (0, 0), so each tween turns it about
`svgOrigin: "0 0"` (its joint). Motion is the same mechanism every other scene uses (scenes.py): one paused timeline,
`fromTo` tweens at absolute seconds, later ones `immediateRender: false`, finite repeats; every frame is a pure
function of time, so HyperFrames can seek any frame. No new runtime, nothing fetched.

Looks: skin, hair (HAIRS), hair_color, shirt, pants, shoes, outfit (OUTFITS), age (child|adult|older), glasses,
hat_color. Expressions (EXPRESSIONS) swap eyes, brows and mouth; actions (ACTIONS) move the rig:
idle (breathe + blink, always on), talk (mouth on every spoken word, a small head bob and an explaining hand),
wave, point, shrug, nod, facepalm, think (hand on chin), jump, sit / stand (a red plastic stool appears),
walk_in / walk_out / a cue with `x` (walk there).
Real people (meta.cast `real: true`) are never caricatured: they are this same generic figure with a name tag.
"""

from __future__ import annotations

import random
import re

from .scenes import _ft

INK = "#3B302C"
MOUTH = "#7A2E2A"
TONGUE = "#F08A8A"
BLUSH = "#F4A6A0"
RIG_H = 300.0  # an adult's height in rig units (feet at y = 0, head top at about -300)

EXPRESSIONS = ("neutral", "happy", "worried", "surprised", "thinking", "sad")
ACTIONS = ("idle", "talk", "wave", "point", "shrug", "walk_in", "walk_out", "jump", "sit", "stand", "nod", "facepalm", "think")
GESTURES = {"wave": 1.9, "point": 1.9, "shrug": 1.4, "jump": 0.8, "nod": 1.0, "facepalm": 1.9}  # momentary: seconds
HAIRS = ("short", "bob", "long", "bun", "ponytail", "cap", "spiky", "bald", "non_la")
OUTFITS = ("tee", "shirt", "dress", "ao_dai", "jacket")
AGES = ("child", "adult", "older")
DEFAULT_LOOK = {"skin": "#F1C9A5", "hair": "short", "hair_color": "#2B2321", "shirt": "#E77A5F", "pants": "#3D4B63",
                "shoes": "#3B302C", "outfit": "tee", "age": "adult", "glasses": False, "hat_color": "#5B8FD1"}
LOOK_KEYS = set(DEFAULT_LOOK)
HEX = re.compile(r"#[0-9A-Fa-f]{6}")
# colour keys must be #RRGGBB
COLOR_KEYS = ("skin", "hair_color", "shirt", "pants", "shoes", "hat_color")


def norm_look(look: dict | None) -> dict:
    lk = {**DEFAULT_LOOK, **{k: v for k, v in (look or {}).items() if v is not None}}
    if lk["age"] == "older" and not (look or {}).get("hair_color"):
        lk["hair_color"] = "#B9B4AE"
    if lk["outfit"] == "ao_dai" and not (look or {}).get("pants"):
        lk["pants"] = "#F7F2E8"
    return lk


def look_problems(look: dict) -> list[str]:
    """What is wrong with a look (unknown keys or values); empty when it draws."""
    out = []
    for k, v in (look or {}).items():
        if k not in LOOK_KEYS:
            out.append(f"unknown look key '{k}' (one of {sorted(LOOK_KEYS)})")
        elif k in COLOR_KEYS and not (isinstance(v, str) and HEX.fullmatch(v)):
            out.append(f"look '{k}' must be a #RRGGBB colour, not {v!r}")
    if (look or {}).get("hair") not in (None, *HAIRS):
        out.append(f"hair '{look['hair']}' is not one of {HAIRS}")
    if (look or {}).get("outfit") not in (None, *OUTFITS):
        out.append(f"outfit '{look['outfit']}' is not one of {OUTFITS}")
    if (look or {}).get("age") not in (None, *AGES):
        out.append(f"age '{look['age']}' is not one of {AGES}")
    return out


def _darker(h: str, k: float = 0.18) -> str:
    from .sticker import shade

    return shade(h, k)


def _sid(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s) or "c"


# ---------------------------------------------------------------- drawing (rig units)

def _st(w: float = 3.2) -> str:
    return f'stroke="{INK}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"'


def _hair_back(lk) -> str:
    """Hair behind the head (inside the head group, drawn before the face)."""
    c, h = lk["hair_color"], lk["hair"]
    if h == "bob":
        return f'<path d="M-74 -66 C-76 -132 76 -132 74 -66 L76 -14 Q76 -4 64 -4 L-64 -4 Q-76 -4 -76 -14 Z" fill="{c}" {_st()}/>'
    if h == "bun":
        return (f'<circle cx="0" cy="-130" r="24" fill="{c}" {_st()}/>'
                f'<path d="M-16 -112 Q0 -106 16 -112" fill="none" stroke="{_darker(c, .35)}" stroke-width="4"/>')
    if h == "ponytail":
        return f'<path d="M50 -96 C88 -96 96 -40 78 -6 C70 -30 62 -50 46 -66 Z" fill="{c}" {_st()}/>'
    return ""


def _hair_long(lk) -> str:
    """Long hair falling behind the shoulders: drawn behind the torso, turned with the head."""
    if lk["hair"] != "long":
        return ""
    return f'<path d="M-72 -70 C-74 -134 74 -134 72 -70 L78 52 Q78 64 66 64 L-66 64 Q-78 64 -78 52 Z" fill="{lk["hair_color"]}" {_st()}/>'


def _hair_front(lk) -> str:
    c, h = lk["hair_color"], lk["hair"]
    hi = _darker(c, -0.25)
    if h in ("bob", "long"):  # straight fringe, sides down past the ears
        return (f'<path d="M-68 -50 C-74 -128 74 -128 68 -50 L60 -50 C58 -70 52 -80 42 -84 L-42 -84 C-52 -80 -58 -70 -60 -50 Z" fill="{c}" {_st()}/>'
                f'<path d="M-36 -100 Q-24 -110 -10 -112" fill="none" stroke="{hi}" stroke-width="4.5" stroke-linecap="round" opacity="0.45"/>')
    if h in ("bun", "ponytail"):  # pulled back, middle part
        return (f'<path d="M-66 -58 C-70 -124 70 -124 66 -58 C60 -80 36 -100 0 -98 C-36 -100 -60 -80 -66 -58 Z" fill="{c}" {_st()}/>'
                f'<path d="M0 -118 L0 -100" stroke="{_darker(c, .35)}" stroke-width="3"/>')
    if h == "spiky":
        return (f'<path d="M-66 -56 C-72 -110 -40 -128 0 -128 C40 -128 72 -110 66 -56 L58 -76 L46 -66 L38 -86 L24 -74 L12 -92 L0 -78 '
                f'L-12 -92 L-24 -76 L-36 -88 L-46 -68 L-58 -78 Z" fill="{c}" {_st()}/>')
    if h == "bald":  # an older man's tufts over the ears and a shine on top
        return (f'<path d="M-66 -44 C-70 -70 -62 -86 -52 -92 C-54 -76 -56 -62 -54 -44 Z" fill="{c}" {_st()}/>'
                f'<path d="M66 -44 C70 -70 62 -86 52 -92 C54 -76 56 -62 54 -44 Z" fill="{c}" {_st()}/>'
                f'<path d="M-22 -108 Q-6 -116 10 -112" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round" opacity="0.6"/>')
    if h == "cap":
        hc = lk["hat_color"]
        return (f'<path d="M-66 -52 C-70 -80 -60 -90 -50 -92 L50 -92 C60 -90 70 -80 66 -52 L58 -66 L-58 -66 Z" fill="{c}" {_st()}/>'
                f'<path d="M-64 -76 C-66 -136 66 -136 64 -76 Z" fill="{hc}" {_st()}/>'
                f'<path d="M-70 -78 Q0 -66 70 -78 Q74 -70 70 -66 Q0 -54 -70 -66 Q-74 -70 -70 -78 Z" fill="{_darker(hc, .2)}" {_st()}/>'
                f'<circle cx="0" cy="-126" r="5" fill="{_darker(hc, .2)}" {_st(2.5)}/>')
    if h == "non_la":  # nón lá: a conical palm-leaf hat
        straw = "#F2D58A"
        rings = "".join(f'<path d="M{-112 + 16 * k} {-80 - 10 * k} Q0 {-70 - 10 * k} {112 - 16 * k} {-80 - 10 * k}" fill="none" '
                        f'stroke="{_darker(straw, .28)}" stroke-width="2.4"/>' for k in range(1, 5))
        return (f'<path d="M-66 -54 C-70 -84 -50 -96 -30 -96 L30 -96 C50 -96 70 -84 66 -54 C58 -70 40 -84 0 -84 C-40 -84 -58 -70 -66 -54 Z" fill="{c}" {_st()}/>'
                f'<path d="M-118 -80 L0 -158 L118 -80 Q0 -62 -118 -80 Z" fill="{straw}" {_st()}/>{rings}'
                f'<path d="M-50 -74 Q-58 -20 -30 -6 M50 -74 Q58 -20 30 -6" fill="none" stroke="#E5554F" stroke-width="2.5"/>')
    # short (default): side part, soft fringe
    return (f'<path d="M-66 -54 C-72 -112 -34 -130 0 -129 C36 -130 72 -112 66 -56 C60 -80 44 -94 22 -94 C8 -104 -16 -102 -30 -92 '
            f'C-46 -90 -60 -78 -66 -54 Z" fill="{c}" {_st()}/>'
            f'<path d="M14 -120 Q30 -112 40 -100" fill="none" stroke="{hi}" stroke-width="5" stroke-linecap="round" opacity="0.6"/>')


def _eyes(expr: str, dx: float) -> str:
    """Two eyes for one expression, drawn about the eye line (y = 0 in the blink group)."""
    out = []
    for sx in (-1, 1):
        x = 21 * sx + dx
        if expr == "happy":
            out.append(f'<path d="M{x - 8} 3 Q{x} -8 {x + 8} 3" fill="none" stroke="{INK}" stroke-width="4.5" stroke-linecap="round"/>')
        elif expr == "sad":
            out.append(f'<path d="M{x - 7} -1 A7 7.5 0 0 0 {x + 7} -1 Z" fill="{INK}"/>'
                       f'<circle cx="{x + 2}" cy="2" r="1.6" fill="#fff"/>')
        elif expr == "surprised":
            out.append(f'<ellipse cx="{x}" cy="0" rx="7.5" ry="9.5" fill="{INK}"/><circle cx="{x + 2.5}" cy="-3.5" r="2.8" fill="#fff"/>')
        elif expr == "thinking":
            out.append(f'<ellipse cx="{x + 3}" cy="-3" rx="6" ry="7.8" fill="{INK}"/><circle cx="{x + 5.2}" cy="-6.2" r="2.2" fill="#fff"/>')
        elif expr == "worried":
            out.append(f'<ellipse cx="{x}" cy="1" rx="5.8" ry="7.4" fill="{INK}"/><circle cx="{x + 2}" cy="-1.8" r="2.2" fill="#fff"/>')
        else:  # neutral
            out.append(f'<ellipse cx="{x}" cy="0" rx="6.4" ry="8.4" fill="{INK}"/><circle cx="{x + 2.2}" cy="-3.2" r="2.4" fill="#fff"/>')
    return "".join(out)


def _brows(expr: str) -> str:
    s = f'fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"'
    d = {
        "neutral": "M-30 -78 Q-21 -82 -12 -78 M12 -78 Q21 -82 30 -78",
        "happy": "M-30 -82 Q-21 -88 -12 -82 M12 -82 Q21 -88 30 -82",
        "worried": "M-31 -77 L-13 -84 M13 -84 L31 -77",
        "surprised": "M-31 -88 Q-21 -96 -11 -88 M11 -88 Q21 -96 31 -88",
        "thinking": "M-30 -78 L-12 -78 M12 -86 Q21 -92 30 -88",
        "sad": "M-31 -74 L-13 -83 M13 -83 L31 -74",
    }[expr]
    extra = ""
    if expr == "worried":  # a sweat drop
        extra = '<path d="M54 -94 Q60 -82 56 -76 Q50 -76 50 -82 Q50 -88 54 -94 Z" fill="#9CCFF0" stroke="#3B302C" stroke-width="2"/>'
    return f'<path d="{d}" {s}/>{extra}'


def _mouth(expr: str) -> str:
    if expr == "happy":
        return (f'<path d="M-15 -37 Q0 -12 15 -37 Z" fill="{MOUTH}" {_st(3)}/>'
                f'<path d="M-7 -22 Q0 -28 7 -22 Q0 -16 -7 -22 Z" fill="{TONGUE}"/>')
    if expr == "worried":
        return f'<path d="M-12 -28 q6 -5 12 0 t12 0" fill="none" stroke="{INK}" stroke-width="3.6" stroke-linecap="round"/>'
    if expr == "surprised":
        return f'<ellipse cx="0" cy="-27" rx="6.5" ry="8.5" fill="{MOUTH}" {_st(3)}/>'
    if expr == "thinking":
        return f'<path d="M-4 -29 L10 -33" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
    if expr == "sad":
        return f'<path d="M-11 -24 Q0 -35 11 -24" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
    return f'<path d="M-9 -32 Q0 -24 9 -32" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'


def _torso(lk) -> str:
    sh, o = lk["shirt"], lk["outfit"]
    body = (f'<path d="M-34 -156 Q-42 -156 -43 -146 L-47 -82 Q-47 -70 -36 -70 L36 -70 Q47 -70 47 -82 L43 -146 Q42 -156 34 -156 Z" '
            f'fill="{sh}" {_st()}/>')
    neck = f'<path d="M-13 -156 Q0 -142 13 -156 Z" fill="{lk["skin"]}" {_st(2.6)}/>'
    dk = _darker(sh, 0.22)
    if o == "shirt":
        neck = (f'<path d="M-13 -156 Q0 -146 13 -156 Z" fill="{lk["skin"]}" {_st(2.6)}/>'
                f'<path d="M-16 -158 L0 -140 L-6 -158 Z M16 -158 L0 -140 L6 -158 Z" fill="#FFFFFF" {_st(2.4)}/>'
                + "".join(f'<circle cx="0" cy="{-128 + 16 * k}" r="2.6" fill="{dk}"/>' for k in range(4)))
    elif o == "jacket":
        body += (f'<path d="M-34 -156 Q-42 -156 -43 -146 L-47 -82 Q-47 -70 -36 -70 L-8 -70 L-10 -150 Z" fill="{dk}" {_st()}/>'
                 f'<path d="M34 -156 Q42 -156 43 -146 L47 -82 Q47 -70 36 -70 L8 -70 L10 -150 Z" fill="{dk}" {_st()}/>')
    elif o == "dress":
        body += (f'<path d="M-44 -96 L-60 -30 Q-60 -22 -50 -22 L50 -22 Q60 -22 60 -30 L44 -96 Z" fill="{sh}" {_st()}/>'
                 f'<path d="M-44 -96 L44 -96" stroke="{dk}" stroke-width="5"/>')
    elif o == "ao_dai":  # long tunic panels over light trousers, mandarin collar
        body += (f'<path d="M-30 -86 L-30 -8 Q-30 0 -22 0 L22 0 Q30 0 30 -8 L30 -86 Z" fill="{sh}" {_st()}/>'
                 f'<path d="M-34 -160 L34 -160 L32 -150 L-32 -150 Z" fill="{dk}" {_st(2.4)}/>')
        neck = ""
    return body + neck


def _arm(lk, side: str, cid: str) -> str:
    """One arm: a shoulder group (sleeve) holding an elbow group (forearm + hand). Pivots at (0, 0) of each group."""
    sleeve = lk["shirt"]
    fore = lk["shirt"] if lk["outfit"] in ("shirt", "jacket", "ao_dai") else lk["skin"]
    return (f'<g id="{cid}-arm{side}">'
            f'<rect x="-10" y="-8" width="20" height="50" rx="10" fill="{sleeve}" {_st()}/>'
            f'<g transform="translate(0,38)"><g id="{cid}-fore{side}">'
            f'<rect x="-8.5" y="-4" width="17" height="38" rx="8.5" fill="{fore}" {_st()}/>'
            f'<circle cx="0" cy="38" r="11" fill="{lk["skin"]}" {_st()}/>'
            f'</g></g></g>')


def _leg(lk, side: str, cid: str) -> str:
    out = -4 if side == "L" else 4
    return (f'<g id="{cid}-leg{side}">'
            f'<rect x="-12" y="-6" width="24" height="70" rx="11" fill="{lk["pants"]}" {_st()}/>'
            f'<ellipse cx="{out}" cy="68" rx="16" ry="9" fill="{lk["shoes"]}" {_st()}/></g>')


def stool_svg() -> str:
    """A red plastic stool (ghế nhựa), seat at y = -44."""
    red, dk = "#E5554F", "#B83B36"
    return (f'<path d="M-36 -46 L36 -46 L42 -36 L-42 -36 Z" fill="{red}" {_st()}/>'
            f'<path d="M-38 -36 L-46 0 L-32 0 L-26 -36 Z M38 -36 L46 0 L32 0 L26 -36 Z" fill="{dk}" {_st()}/>'
            f'<path d="M-30 -22 L30 -22" stroke="{dk}" stroke-width="6"/>')


def rig_svg(cid: str, look: dict, facing: int = 1, expression: str = "neutral") -> str:
    """The whole puppet in rig units (feet at the origin). Every animated part has an id `{cid}-...`."""
    lk = norm_look(look)
    dx = 2.5 * facing  # the pupils look toward the other side of the stage
    child = lk["age"] == "child"
    head_scale = 1.1 if child else 1.0
    expr_eyes = "".join(f'<g id="{cid}-ey-{e}" opacity="{1 if e == expression else 0}">{_eyes(e, dx)}</g>' for e in EXPRESSIONS)
    expr_brows = "".join(f'<g id="{cid}-bw-{e}" opacity="{1 if e == expression else 0}">{_brows(e)}</g>' for e in EXPRESSIONS)
    expr_mouth = "".join(f'<g id="{cid}-mo-{e}" opacity="{1 if e == expression else 0}">{_mouth(e)}</g>' for e in EXPRESSIONS)
    wrinkles = ""
    if lk["age"] == "older":
        wrinkles = (f'<path d="M-40 -60 l-6 -3 M-40 -54 l-7 0 M40 -60 l6 -3 M40 -54 l7 0 M-14 -96 Q0 -100 14 -96" '
                    f'fill="none" stroke="{_darker(lk["skin"], .3)}" stroke-width="2.2" stroke-linecap="round"/>')
    glasses = ""
    if lk.get("glasses"):
        glasses = (f'<g fill="none" stroke="{INK}" stroke-width="3.2"><circle cx="{-21 + dx}" cy="-58" r="15"/>'
                   f'<circle cx="{21 + dx}" cy="-58" r="15"/></g><path d="M{-6 + dx} -60 Q{dx} -64 {6 + dx} -60" fill="none" stroke="{INK}" stroke-width="3"/>')
    face = (f'{_hair_back(lk)}'
            f'<circle cx="-60" cy="-56" r="12" fill="{lk["skin"]}" {_st()}/><circle cx="60" cy="-56" r="12" fill="{lk["skin"]}" {_st()}/>'
            f'<ellipse cx="0" cy="-62" rx="62" ry="58" fill="{lk["skin"]}" {_st()}/>'
            f'<ellipse cx="-38" cy="-36" rx="9.5" ry="5.8" fill="{BLUSH}" opacity="0.65"/>'
            f'<ellipse cx="38" cy="-36" rx="9.5" ry="5.8" fill="{BLUSH}" opacity="0.65"/>{wrinkles}'
            f'<g transform="translate(0,-58)"><g id="{cid}-ey">{expr_eyes}</g></g>'
            f'{expr_brows}'
            f'<g id="{cid}-mx">{expr_mouth}</g>'
            f'<g transform="translate(0,-36)"><g id="{cid}-mt" opacity="0">'
            f'<ellipse cx="0" cy="8" rx="10" ry="9" fill="{MOUTH}" {_st(3)}/><ellipse cx="0" cy="13" rx="6" ry="3.4" fill="{TONGUE}"/></g></g>'
            f'{glasses}{_hair_front(lk)}')
    head = (f'<g transform="translate(0,-160)"><g id="{cid}-head"><g id="{cid}-hb"><g transform="scale({head_scale})">{face}</g></g></g></g>')
    long_hair = _hair_long(lk)
    hair_back = (f'<g transform="translate(0,-160)"><g id="{cid}-hl"><g transform="scale({head_scale})">{long_hair}</g></g></g>'
                 if long_hair else "")
    neck = f'<rect x="-9" y="-170" width="18" height="18" fill="{lk["skin"]}" {_st(2.6)}/>'
    upper = (f'{hair_back}{_torso(lk)}{neck}{head}'
             f'<g transform="translate(-37,-148)">{_arm(lk, "L", cid)}</g>'
             f'<g transform="translate(37,-148)">{_arm(lk, "R", cid)}</g>')
    legs = (f'<g transform="translate(-16,-74)">{_leg(lk, "L", cid)}</g>'
            f'<g transform="translate(16,-74)">{_leg(lk, "R", cid)}</g>')
    return (f'<g id="{cid}-pose"><g id="{cid}-stool" opacity="0">{stool_svg()}</g>{legs}'
            f'<g transform="translate(0,-74)"><g id="{cid}-br"><g transform="translate(0,74)">{upper}</g></g></g></g>')


# ---------------------------------------------------------------- keyframes

PIVOTED = {"rotation", "scaleX", "scaleY", "scale"}


class Keys:
    """Keyframes per (target, property), turned into back-to-back fromTo tweens (never two at once on one property:
    a key that would start before the previous one ends waits for it)."""

    def __init__(self):
        self.tracks: dict[tuple[str, str], list] = {}
        self.init: dict[tuple[str, str], float] = {}
        self.origin: dict[str, str] = {}
        self._n = 0

    def start(self, sel: str, prop: str, val: float):
        self.init[(sel, prop)] = val

    def add(self, sel: str, prop: str, t: float, val: float, dur: float = 0.3, ease: str = "power2.inOut"):
        self._n += 1
        self.tracks.setdefault((sel, prop), []).append((max(0.0, t), self._n, float(val), dur, ease))

    def value_at(self, sel: str, prop: str, t: float) -> float:
        v = self.init.get((sel, prop), 1.0 if prop.startswith(("scale", "opacity")) else 0.0)
        for kt, _, val, d, _e in sorted(self.tracks.get((sel, prop), [])):
            if kt <= t:
                v = val
        return v

    def tweens(self) -> list[str]:
        out = []
        for (sel, prop), ks in self.tracks.items():
            ks = sorted(ks)
            prev = self.init.get((sel, prop), 1.0 if prop.startswith(("scale", "opacity")) else 0.0)
            free = 0.0
            first = True
            for i, (t, _, val, d, ease) in enumerate(ks):
                t = max(t, free)
                nxt = ks[i + 1][0] if i + 1 < len(ks) else None
                if nxt is not None and nxt > t:
                    d = min(d, nxt - t)
                d = max(0.02, d)
                if abs(val - prev) < 1e-6:
                    continue
                o = f', svgOrigin: "{self.origin[sel]}"' if sel in self.origin and prop in PIVOTED else ""
                out.append(_ft(sel, f"{prop}: {prev:.3f}{o}", f'{prop}: {val:.3f}{o}, duration: {d:.3f}, ease: "{ease}"', t, later=not first))
                first = False
                prev, free = val, t + d
        return out


# ---------------------------------------------------------------- choreography

REST = {"L": 9.0, "R": -9.0}
FORE_REST = {"L": 5.0, "R": -5.0}


def _arms(K: Keys, cid: str, t: float, pose: dict, dur: float = 0.35, ease: str = "back.out(1.4)"):
    for part, val in pose.items():
        K.add(f"#{cid}-{part}", "rotation", t, val, dur, ease)


def rest_pose() -> dict:
    return {"armL": REST["L"], "armR": REST["R"], "foreL": FORE_REST["L"], "foreR": FORE_REST["R"]}


def think_pose(side: str = "R") -> dict:
    p = rest_pose()
    if side == "R":
        p.update(armR=80, foreR=115)
    else:
        p.update(armL=-80, foreL=-115)
    return p


def mouth_flaps(K: Keys, cid: str, spans: list[tuple[float, float]], words: list[dict], seed: int):
    """The open mouth replaces the expression's mouth while the character speaks; it opens on every word (a syllable in
    Vietnamese) and closes between them. Without word timings it flaps at a speaking rhythm."""
    rng = random.Random(seed)
    for t0, t1 in spans:
        if t1 - t0 < 0.15:
            continue
        K.add(f"#{cid}-mx", "opacity", t0, 0, 0.06, "none")
        K.add(f"#{cid}-mt", "opacity", t0, 1, 0.06, "none")
        ws = [w for w in words if w["start"] >= t0 - 0.05 and w["end"] <= t1 + 0.05]
        if ws:
            for i, w in enumerate(ws):
                open_ = 0.55 + 0.45 * min(1.0, len(w["word"]) / 6) * rng.uniform(0.75, 1.0)
                K.add(f"#{cid}-mt", "scaleY", w["start"], open_, min(0.09, max(0.04, (w["end"] - w["start"]) * 0.4)), "power2.out")
                nxt = ws[i + 1]["start"] if i + 1 < len(ws) else t1
                close_at = max(w["start"] + 0.08, min(w["end"] - 0.03, nxt - 0.06))
                K.add(f"#{cid}-mt", "scaleY", close_at, 0.18, 0.07, "power2.in")
        else:
            t, k = t0, 0
            while t < t1 - 0.1:
                K.add(f"#{cid}-mt", "scaleY", t, (0.9 if k % 3 else 0.6) * rng.uniform(0.8, 1.0), 0.07, "power2.out")
                K.add(f"#{cid}-mt", "scaleY", t + 0.1, 0.2, 0.06, "power2.in")
                t += 0.19 + rng.uniform(-0.03, 0.04)
                k += 1
        K.add(f"#{cid}-mt", "opacity", t1, 0, 0.08, "none")
        K.add(f"#{cid}-mx", "opacity", t1, 1, 0.08, "none")
        # a small head bob while speaking
        t, k = t0 + 0.1, 0
        while t < t1 - 0.3:
            K.add(f"#{cid}-hb", "rotation", t, (2.6 if k % 2 else -2.2), 0.45, "sine.inOut")
            t += 0.55
            k += 1
        K.add(f"#{cid}-hb", "rotation", max(t0, t1 - 0.2), 0, 0.3, "sine.inOut")


def merge_spans(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1] + 0.12:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def choreograph(cid: str, ch: dict, *, x_px: float, scale: float, W: float, dur: float, events: list[dict],
                words: list[dict], talk_spans: list[tuple[float, float]], speech_end: float, seed: int = 1,
                partner_side: int = 1, extra_x: list[str] | None = None, point_side: int | None = None) -> tuple[list[str], "Keys", list]:
    """Turn a character's timeline of events ({t, expression?, action?, x?}) into tweens. Returns (tweens, keys,
    x track) where the x track is [(t, offset px, duration)] for anything that follows the character (its name tag).
    `partner_side` is +1 when the rest of the stage lies to the right (point and explaining hands go that way)."""
    K = Keys()
    for part in ("armL", "armR", "foreL", "foreR", "legL", "legR", "head", "hb", "hl", "ey", "mt", "pose", "br"):
        K.origin[f"#{cid}-{part}"] = "0 0"
    K.origin[f"#{cid}-sh"] = "0 0"
    side_arm = "R" if partner_side > 0 else "L"
    sgn = 1 if side_arm == "R" else -1  # the rotation sign that lifts the arm toward the partner
    for part, val in rest_pose().items():
        K.start(f"#{cid}-{part}", "rotation", val)
    for p in ("legL", "legR"):
        K.start(f"#{cid}-{p}", "scaleY", 1)
    K.start(f"#{cid}-mt", "scaleY", 0.2)
    expr0 = ch.get("expression") or "neutral"
    for e in EXPRESSIONS:
        for part in ("ey", "bw", "mo"):
            K.start(f"#{cid}-{part}-{e}", "opacity", 1.0 if e == expr0 else 0.0)
    K.start(f"#{cid}-mx", "opacity", 1)
    K.start(f"#{cid}-mt", "opacity", 0)
    K.start(f"#{cid}-stool", "opacity", 0)
    speed = 0.36 * W  # px per second
    off_left, off_right = -x_px - 0.16 * W, W * 1.16 - x_px
    exit_side = off_left if x_px < W / 2 else off_right
    head_targets = [f"#{cid}-head"] + ([f"#{cid}-hl"] if ch.get("_long_hair") else [])
    xtrack: list[tuple[float, float, float, str]] = []
    state = {"x": 0.0, "posture": "stand", "activity": "idle", "busy": 0.0}

    def set_x(t, val, d, ease):
        for sel in [f"#{cid}-mv", f"#{cid}-sh"] + (extra_x or []):
            K.add(sel, "x", t, val, d, ease)
        xtrack.append((t, val, d, ease))

    def base_arms(t, d=0.35):
        _arms(K, cid, t, think_pose(side_arm) if state["activity"] == "think" else rest_pose(), d)

    def stand_up(t) -> float:
        if state["posture"] != "sit":
            return t
        K.add(f"#{cid}-pose", "y", t, 0, 0.35, "power2.out")
        for p in ("legL", "legR"):
            K.add(f"#{cid}-{p}", "scaleY", t, 1, 0.35, "power2.out")
        K.add(f"#{cid}-stool", "opacity", t + 0.3, 0, 0.2, "none")
        state["posture"] = "stand"
        return t + 0.4

    def walk(t0, x1):
        t0 = stand_up(t0)
        x0 = state["x"]
        d = max(0.7, abs(x1 - x0) / speed)
        set_x(t0, x1, d, "power1.inOut")
        n = max(2, round(d / 0.3))
        step = d / n
        for k in range(n):
            tk, s = t0 + k * step, (1 if k % 2 == 0 else -1)
            K.add(f"#{cid}-legL", "rotation", tk, 19 * s, step * 0.95, "sine.inOut")
            K.add(f"#{cid}-legR", "rotation", tk, -19 * s, step * 0.95, "sine.inOut")
            K.add(f"#{cid}-armL", "rotation", tk, REST["L"] - 16 * s, step * 0.95, "sine.inOut")
            K.add(f"#{cid}-armR", "rotation", tk, REST["R"] - 16 * s, step * 0.95, "sine.inOut")
            K.add(f"#{cid}-pose", "y", tk, -6, step / 2, "sine.out")
            K.add(f"#{cid}-pose", "y", tk + step / 2, 0, step / 2, "sine.in")
        for p in ("legL", "legR"):
            K.add(f"#{cid}-{p}", "rotation", t0 + d, 0, 0.2, "sine.out")
        state["x"] = x1
        state["busy"] = t0 + d + 0.2
        base_arms(t0 + d, 0.25)
        return t0 + d

    def gesture(t, act, toward=None):
        g = GESTURES[act]
        t = max(t, state["busy"])
        end = t + g
        if act == "wave":
            arm, fore = ("armR", "foreR") if side_arm == "R" else ("armL", "foreL")
            s = -1 if side_arm == "R" else 1
            K.add(f"#{cid}-{arm}", "rotation", t, 148 * s, 0.35, "back.out(1.6)")
            k, tt = 0, t + 0.3
            while tt < end - 0.4:
                K.add(f"#{cid}-{fore}", "rotation", tt, (-28 if k % 2 == 0 else 18) * -s, 0.22, "sine.inOut")
                tt += 0.24
                k += 1
            K.add(f"#{cid}-{fore}", "rotation", end - 0.4, FORE_REST[side_arm], 0.25, "sine.inOut")
        elif act == "point":
            ps = point_side or partner_side
            if toward is not None:
                ps = 1 if toward >= x_px + state["x"] else -1
            if ps > 0:
                _arms(K, cid, t, {"armR": -96, "foreR": -6}, 0.35, "back.out(1.8)")
            else:
                _arms(K, cid, t, {"armL": 96, "foreL": 6}, 0.35, "back.out(1.8)")
            for sel in head_targets:
                K.add(sel, "rotation", t, 5 * ps, 0.35)
                K.add(sel, "rotation", end - 0.3, 0, 0.35)
        elif act == "shrug":
            _arms(K, cid, t, {"armL": 42, "foreL": 80, "armR": -42, "foreR": -80}, 0.3, "back.out(1.6)")
            for sel in head_targets:
                K.add(sel, "rotation", t, -8 * partner_side, 0.3)
                K.add(sel, "y", t, -3, 0.3)
                K.add(sel, "rotation", end - 0.3, 0, 0.3)
                K.add(sel, "y", end - 0.3, 0, 0.3)
        elif act == "facepalm":
            _arms(K, cid, t, {"armR": 150, "foreR": 22}, 0.4, "power3.out")
            for sel in head_targets:
                K.add(sel, "rotation", t + 0.15, -7, 0.35)
                K.add(sel, "y", t + 0.15, 5, 0.35)
                K.add(sel, "rotation", end - 0.3, 0, 0.35)
                K.add(sel, "y", end - 0.3, 0, 0.35)
        elif act == "nod":
            for sel in head_targets:
                for k in range(2):
                    K.add(sel, "y", t + 0.42 * k, 6, 0.2, "sine.inOut")
                    K.add(sel, "rotation", t + 0.42 * k, 2.5, 0.2, "sine.inOut")
                    K.add(sel, "y", t + 0.42 * k + 0.21, 0, 0.2, "sine.inOut")
                    K.add(sel, "rotation", t + 0.42 * k + 0.21, 0, 0.2, "sine.inOut")
        elif act == "jump":
            t = stand_up(t)
            end = t + g
            K.add(f"#{cid}-pose", "scaleY", t, 0.9, 0.1, "power2.out")
            K.add(f"#{cid}-pose", "scaleY", t + 0.1, 1.05, 0.2, "power2.out")
            K.add(f"#{cid}-mv", "y", t + 0.1, -0.12 * RIG_H * scale, 0.28, "power2.out")
            K.add(f"#{cid}-mv", "y", t + 0.38, 0, 0.26, "power2.in")
            K.add(f"#{cid}-pose", "scaleY", t + 0.62, 0.93, 0.08, "power2.out")
            K.add(f"#{cid}-pose", "scaleY", t + 0.7, 1, 0.2, "back.out(2)")
            K.add(f"#{cid}-sh", "scaleX", t + 0.1, 0.65, 0.28, "power2.out")
            K.add(f"#{cid}-sh", "scaleX", t + 0.38, 1, 0.26, "power2.in")
            _arms(K, cid, t + 0.05, {"armL": 150, "foreL": 10, "armR": -150, "foreR": -10}, 0.3, "power2.out")
        state["busy"] = end
        if act in ("wave", "point", "shrug", "facepalm", "jump"):
            base_arms(end - 0.25, 0.35)

    talk_from = None
    talk_list = list(talk_spans)
    evs = sorted(events, key=lambda e: e["t"])
    for e in evs:
        t = e["t"]
        if e.get("expression") in EXPRESSIONS:
            for ex in EXPRESSIONS:
                for part in ("ey", "bw", "mo"):
                    K.add(f"#{cid}-{part}-{ex}", "opacity", t, 1.0 if ex == e["expression"] else 0.0, 0.12, "power1.inOut")
        a = e.get("action")
        if e.get("x") is not None and a not in ("walk_in", "walk_out"):
            walk(t, float(e["x"]) - x_px)
        if a in ("idle", "think", "talk", "walk_out") and talk_from is not None:
            talk_list.append((talk_from, t))
            talk_from = None
        if a == "talk":
            talk_from = t
            state["activity"] = "talk"
            # the explaining hand, toward the partner, then back
            tg = max(t, state["busy"]) + 0.1
            if side_arm == "R":
                _arms(K, cid, tg, {"armR": -32, "foreR": -62}, 0.4)
            else:
                _arms(K, cid, tg, {"armL": 32, "foreL": 62}, 0.4)
            base_arms(tg + 1.3, 0.45)
            state["busy"] = tg + 1.75
        elif a == "idle":
            state["activity"] = "idle"
            base_arms(max(t, state["busy"]))
        elif a == "think":
            state["activity"] = "think"
            base_arms(max(t, state["busy"]), 0.45)
            for sel in head_targets:
                K.add(sel, "rotation", t, 6 * partner_side, 0.5)
        elif a == "sit":
            if state["posture"] != "sit":
                K.add(f"#{cid}-stool", "opacity", t, 1, 0.15, "none")
                K.add(f"#{cid}-pose", "y", t + 0.1, 30, 0.4, "power2.inOut")
                for p in ("legL", "legR"):
                    K.add(f"#{cid}-{p}", "scaleY", t + 0.1, 0.52, 0.4, "power2.inOut")
                state["posture"] = "sit"
        elif a == "stand":
            stand_up(t)
        elif a == "walk_in":
            if t <= 0.05:  # starts off screen and walks in at once
                for sel in [f"#{cid}-mv", f"#{cid}-sh"] + (extra_x or []):
                    K.start(sel, "x", exit_side)
                state["x"] = exit_side
                walk(0.15, float(e["x"]) - x_px if e.get("x") is not None else 0.0)
            else:
                for sel in [f"#{cid}-mv", f"#{cid}-sh"] + (extra_x or []):
                    K.start(sel, "x", exit_side)
                state["x"] = exit_side
                walk(t, float(e["x"]) - x_px if e.get("x") is not None else 0.0)
        elif a == "walk_out":
            walk(t, exit_side)
        elif a in GESTURES:
            gesture(t, a, float(e["toward"]) if e.get("toward") is not None else None)
        if a in ("idle", "think") and state["activity"] != "talk":
            pass
    if talk_from is not None:
        talk_list.append((talk_from, max(talk_from + 0.3, speech_end)))
    mouth_flaps(K, cid, merge_spans(talk_list), words, seed)
    # blinks: seeded, every 2.4-4.4 s, never while the eyes are closed in a smile
    rng = random.Random(seed * 7 + 3)
    t = rng.uniform(0.7, 1.8)
    while t < dur - 0.3:
        K.add(f"#{cid}-ey", "scaleY", t, 0.1, 0.07, "power2.in")
        K.add(f"#{cid}-ey", "scaleY", t + 0.08, 1, 0.1, "power2.out")
        t += rng.uniform(2.4, 4.4)
    tw = K.tweens()
    # breathing: the upper body rises and falls about the hips (one finite yoyo tween)
    period = 1.7 + 0.2 * (seed % 3)
    reps = max(0, int(dur / period))
    tw.insert(0, f'tl.fromTo("#{cid}-br", {{ scaleY: 1, svgOrigin: "0 0" }}, {{ scaleY: 1.022, svgOrigin: "0 0", duration: {period:.2f}, '
                 f'ease: "sine.inOut", repeat: {reps}, yoyo: true }}, {0.05 + 0.3 * (seed % 4):.2f});')
    return tw, K, xtrack
