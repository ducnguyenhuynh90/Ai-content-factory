"""`stage`: a small sticker set where rigged characters act out the everyday thread of a story.

    {"type": "stage", "set": "street|office|cafe|room|phone|plain",
     "characters": [{"id": "linh", "look": {...}, "x": 0.3, "expression": "worried", "action": "idle",
                     "cues": [{"cue": "nhưng", "expression": "surprised", "action": "jump"}]}],
     "props": [{"icon": "phone", "x": 0.7, "y": 0.6, "cue": "điện thoại"}],
     "bubble": {"who": "linh", "text": "Sao lại đắt thế?", "cue": "sao"},
     "caption": "…", "transition": "whip|zoom|circle|slide|cut"}

Optional fields beyond the contract (docs/plans/story-sticker-agent.md §3):
- characters[].cues[].x        walk to this x (0-1) on the cue
- characters[].tag             true/false or a text: the name tag under the feet (default: on the character's first
                               appearance in the film, always for a real person)
- props[].size (fraction of the short side, default 0.12), props[].color ("a"|"b"|#hex) / props[].concept
- bubbles: [bubble, …]         several lines in turn (each replaces the previous); a bubble may carry `until` (a cue
                               word: it closes there)
- bubble.style: "think"        a thought cloud instead of a speech bubble

Characters come from `meta.cast` ({id, name, look, role, tag?, real?}); a beat refers to them by id and may restate
the look (lint: it must match). The speaker's mouth moves while the bubble's words are spoken (word timings from the
voice; without them over the bubble's own length), and while the character's action is `talk`.
"""

from __future__ import annotations

import random
import re

from . import characters as C
from .metaphors import ICONS, _first_attrs, _st
from .scenes import GENERATORS, E, _ft
from .sticker import PALETTE, mix, shade, stickerize, svg_filter

SETS = ("street", "office", "cafe", "room", "phone", "plain")
LINE = PALETTE["line"]
PROP_COLORS = ["#D2643F", "#B7791F", "#3E8E7E", "#4A7DBA", "#8A5A9E"]


# ---------------------------------------------------------------- everyday props (added to the shared ICONS)

def _icons_everyday() -> dict:
    return {
        "phone": lambda s, c: (f'<rect x="{s*.28}" y="{s*.06}" width="{s*.44}" height="{s*.88}" rx="{s*.08}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                               f'<rect x="{s*.34}" y="{s*.16}" width="{s*.32}" height="{s*.6}" rx="{s*.03}" fill="{c}" fill-opacity="0.3" {_st(s, c, .025)}/>'
                               f'<path d="M{s*.44} {s*.11} L{s*.56} {s*.11}" {_st(s, c, .03)}/><circle cx="{s*.5}" cy="{s*.85}" r="{s*.035}" fill="{c}"/>'),
        "coffee": lambda s, c: (f'<path d="M{s*.24} {s*.24} L{s*.76} {s*.24} L{s*.68} {s*.92} L{s*.32} {s*.92} Z" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                                f'<path d="M{s*.29} {s*.62} L{s*.71} {s*.62} L{s*.68} {s*.92} L{s*.32} {s*.92} Z" fill="{c}" fill-opacity="0.45" {_st(s, c, .025)}/>'
                                f'<rect x="{s*.36}" y="{s*.36}" width="{s*.12}" height="{s*.12}" rx="{s*.02}" fill="#FFFFFF" fill-opacity="0.4" {_st(s, c, .022)}/>'
                                f'<rect x="{s*.52}" y="{s*.44}" width="{s*.12}" height="{s*.12}" rx="{s*.02}" fill="#FFFFFF" fill-opacity="0.4" {_st(s, c, .022)}/>'
                                f'<path d="M{s*.6} {s*.04} L{s*.54} {s*.7}" {_st(s, c, .04)}/>'),
        "phin": lambda s, c: (f'<path d="M{s*.2} {s*.62} L{s*.8} {s*.62} L{s*.72} {s*.94} L{s*.28} {s*.94} Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                              f'<rect x="{s*.3}" y="{s*.3}" width="{s*.4}" height="{s*.26}" rx="{s*.03}" fill="{c}" fill-opacity="0.35" {_st(s, c)}/>'
                              f'<path d="M{s*.22} {s*.58} L{s*.78} {s*.58}" {_st(s, c)}/><rect x="{s*.34}" y="{s*.18}" width="{s*.32}" height="{s*.1}" rx="{s*.03}" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'
                              f'<path d="M{s*.5} {s*.18} L{s*.5} {s*.1}" {_st(s, c)}/>'),
        "scooter": lambda s, c: (f'<circle cx="{s*.2}" cy="{s*.74}" r="{s*.14}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                                 f'<circle cx="{s*.8}" cy="{s*.74}" r="{s*.14}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                                 f'<path d="M{s*.2} {s*.74} C{s*.28} {s*.5} {s*.5} {s*.52} {s*.56} {s*.62} L{s*.7} {s*.62} L{s*.74} {s*.3}" fill="none" {_st(s, c)}/>'
                                 f'<path d="M{s*.16} {s*.6} C{s*.2} {s*.44} {s*.46} {s*.44} {s*.54} {s*.6} L{s*.2} {s*.62} Z" fill="{c}" fill-opacity="0.4" {_st(s, c)}/>'
                                 f'<path d="M{s*.2} {s*.46} L{s*.46} {s*.46}" {_st(s, c, .05)}/>'
                                 f'<path d="M{s*.66} {s*.28} L{s*.84} {s*.24}" {_st(s, c)}/><circle cx="{s*.8}" cy="{s*.38}" r="{s*.05}" fill="{c}" fill-opacity="0.4" {_st(s, c, .025)}/>'),
        "laptop": lambda s, c: (f'<rect x="{s*.18}" y="{s*.2}" width="{s*.64}" height="{s*.44}" rx="{s*.04}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                                f'<rect x="{s*.25}" y="{s*.27}" width="{s*.5}" height="{s*.3}" fill="{c}" fill-opacity="0.3"/>'
                                f'<path d="M{s*.08} {s*.74} L{s*.92} {s*.74} L{s*.84} {s*.64} L{s*.16} {s*.64} Z" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'),
        "cash": lambda s, c: (f'<rect x="{s*.14}" y="{s*.22}" width="{s*.72}" height="{s*.4}" rx="{s*.04}" transform="rotate(-8 {s*.5} {s*.42})" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                              f'<rect x="{s*.1}" y="{s*.38}" width="{s*.76}" height="{s*.42}" rx="{s*.04}" fill="{c}" fill-opacity="0.22" {_st(s, c)}/>'
                              f'<circle cx="{s*.48}" cy="{s*.59}" r="{s*.1}" fill="{c}" fill-opacity="0.15" {_st(s, c, .03)}/>'),
        "receipt": lambda s, c: (f'<path d="M{s*.24} {s*.06} L{s*.76} {s*.06} L{s*.76} {s*.92} L{s*.67} {s*.86} L{s*.58} {s*.92} L{s*.5} {s*.86} '
                                 f'L{s*.42} {s*.92} L{s*.33} {s*.86} L{s*.24} {s*.92} Z" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                                 f'<path d="M{s*.34} {s*.24} L{s*.66} {s*.24} M{s*.34} {s*.38} L{s*.6} {s*.38} M{s*.34} {s*.52} L{s*.66} {s*.52} M{s*.46} {s*.7} L{s*.66} {s*.7}" {_st(s, c, .03)}/>'),
        "bag": lambda s, c: (f'<path d="M{s*.18} {s*.34} L{s*.82} {s*.34} L{s*.88} {s*.92} L{s*.12} {s*.92} Z" fill="{c}" fill-opacity="0.18" {_st(s, c)}/>'
                             f'<path d="M{s*.36} {s*.44} L{s*.36} {s*.24} C{s*.36} {s*.08} {s*.64} {s*.08} {s*.64} {s*.24} L{s*.64} {s*.44}" fill="none" {_st(s, c)}/>'),
        "heart": lambda s, c: (f'<path d="M{s*.5} {s*.86} C{s*.2} {s*.64} {s*.06} {s*.46} {s*.1} {s*.3} C{s*.14} {s*.12} {s*.42} {s*.08} {s*.5} {s*.3} '
                               f'C{s*.58} {s*.08} {s*.86} {s*.12} {s*.9} {s*.3} C{s*.94} {s*.46} {s*.8} {s*.64} {s*.5} {s*.86} Z" fill="{c}" fill-opacity="0.35" {_st(s, c)}/>'),
        "parcel": lambda s, c: (f'<path d="M{s*.5} {s*.1} L{s*.88} {s*.28} L{s*.88} {s*.72} L{s*.5} {s*.9} L{s*.12} {s*.72} L{s*.12} {s*.28} Z" fill="{c}" fill-opacity="0.18" {_st(s, c)}/>'
                                f'<path d="M{s*.12} {s*.28} L{s*.5} {s*.46} L{s*.88} {s*.28} M{s*.5} {s*.46} L{s*.5} {s*.9} M{s*.31} {s*.19} L{s*.69} {s*.37}" fill="none" {_st(s, c, .03)}/>'),
        "cart": lambda s, c: (f'<path d="M{s*.06} {s*.18} L{s*.2} {s*.18} L{s*.32} {s*.66} L{s*.8} {s*.66} L{s*.9} {s*.3} L{s*.24} {s*.3}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                              f'<circle cx="{s*.38}" cy="{s*.82}" r="{s*.07}" {_st(s, c)}/><circle cx="{s*.74}" cy="{s*.82}" r="{s*.07}" {_st(s, c)}/>'),
        "banhmi": lambda s, c: (f'<path d="M{s*.06} {s*.56} C{s*.06} {s*.3} {s*.94} {s*.3} {s*.94} {s*.56} C{s*.94} {s*.7} {s*.06} {s*.7} {s*.06} {s*.56} Z" fill="{c}" fill-opacity="0.25" {_st(s, c)}/>'
                                f'<path d="M{s*.26} {s*.46} L{s*.34} {s*.4} M{s*.44} {s*.44} L{s*.52} {s*.38} M{s*.62} {s*.44} L{s*.7} {s*.38}" {_st(s, c, .03)}/>'
                                f'<path d="M{s*.1} {s*.6} Q{s*.3} {s*.52} {s*.5} {s*.6} T{s*.9} {s*.6}" {_st(s, c, .03)}/>'),
        "chat": lambda s, c: (f'<path d="M{s*.1} {s*.2} L{s*.9} {s*.2} L{s*.9} {s*.68} L{s*.42} {s*.68} L{s*.24} {s*.86} L{s*.26} {s*.68} L{s*.1} {s*.68} Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                              + "".join(f'<circle cx="{s*x}" cy="{s*.44}" r="{s*.05}" fill="{c}"/>' for x in (.32, .5, .68))),
    }


for _k, _f in _icons_everyday().items():
    ICONS.setdefault(_k, (lambda f: (lambda s, c: _first_attrs(f(s, c))))(_f))


# ---------------------------------------------------------------- sets (flat pastel backgrounds, a few props, a little life)

def _r(x, y, w, h, fill, rx=0, stroke=None, sw=3, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" fill="{fill}"{st}{extra}/>'


def _icon_at(key: str, x: float, y: float, s: float, c: str, gid: str = "") -> str:
    """An icon drawn flat at (x, y) (top-left), size s, its fills turned into solid tints."""
    art = stickerize(ICONS[key](s, c))
    idattr = f' id="{gid}"' if gid else ""
    return f'<g transform="translate({x:.1f},{y:.1f})"><g{idattr}>{art}</g></g>'


def _sign(x, y, w, h, fill, text, fs, color="#FFFFFF", tid="", zones=None) -> str:
    """A shop sign (bảng hiệu). Its words are a text zone: they fade while a speech bubble covers them."""
    if zones is not None and tid:
        zones.append((tid, x, y, x + w, y + h))
    return (_r(x, y, w, h, fill, h * 0.18, LINE, 3) +
            f'<text id="{tid}" x="{x + w / 2:.1f}" y="{y + h / 2 + fs * 0.36:.1f}" text-anchor="middle" font-family="Inter" font-weight="800" '
            f'font-size="{fs}" fill="{color}" letter-spacing="2">{E(text)}</text>')


def _cloud(cx, cy, r) -> str:
    return "".join(f'<circle cx="{cx + dx * r:.1f}" cy="{cy + dy * r:.1f}" r="{r * k:.1f}" fill="#FFFFFF"/>'
                   for dx, dy, k in ((-1.0, 0.25, 0.7), (0, 0, 1.0), (1.05, 0.2, 0.75), (0.45, 0.35, 0.7), (-0.5, 0.4, 0.6)))


def _moto(scale: float, body: str) -> str:
    """A small xe máy with its rider (helmet), side view, origin at the ground under the middle."""
    k = scale
    return (f'<g transform="scale({k:.3f})">'
            f'<circle cx="-46" cy="-18" r="18" fill="#4A4A55" stroke="{LINE}" stroke-width="3"/><circle cx="-46" cy="-18" r="7" fill="#D8D8DE"/>'
            f'<circle cx="50" cy="-18" r="18" fill="#4A4A55" stroke="{LINE}" stroke-width="3"/><circle cx="50" cy="-18" r="7" fill="#D8D8DE"/>'
            f'<path d="M-66 -34 C-60 -64 -20 -66 -6 -44 L28 -44 L44 -86 L56 -86 L62 -34 Z" fill="{body}" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M-52 -66 L-4 -66 Q4 -66 2 -58 L-50 -56 Z" fill="#3B302C"/>'
            f'<path d="M-30 -66 L-24 -104 L0 -108 L10 -70 Z" fill="#5B8FD1" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/>'
            f'<circle cx="-12" cy="-124" r="17" fill="#FBE3A1" stroke="{LINE}" stroke-width="3"/>'
            f'<path d="M-30 -126 C-30 -150 6 -150 6 -126 Z" fill="#E5554F" stroke="{LINE}" stroke-width="3"/>'
            f'<path d="M0 -96 L40 -88" stroke="{LINE}" stroke-width="7" stroke-linecap="round"/>'
            f'<circle cx="62" cy="-74" r="6" fill="#FFF3B0" stroke="{LINE}" stroke-width="2.5"/></g>')


def _stool(x, y, k, color) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({k:.3f})">'
            f'<path d="M-36 -46 L36 -46 L42 -36 L-42 -36 Z" fill="{color}" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M-38 -36 L-46 0 L-32 0 L-26 -36 Z M38 -36 L46 0 L32 0 L26 -36 Z" fill="{shade(color, .2)}" stroke="{LINE}" stroke-width="3" stroke-linejoin="round"/></g>')


def set_street(sid, W, H, fy, dur, u):
    P = PALETTE
    m, tw = [_r(0, 0, W, H, "#D7ECF4")], []
    m.append(f'<g id="{sid}-cl"><g>{_cloud(W * 0.16, H * 0.1, u * 0.035)}</g><g>{_cloud(W * 0.62, H * 0.07, u * 0.03)}</g></g>')
    tw.append(_ft(f"#{sid}-cl", "x: 0", f"x: {W * 0.05:.0f}, duration: {dur:.2f}, ease: \"none\"", 0))
    base = fy - 0.075 * H
    cols = [P["peach"], P["mint"], P["butter"], P["pink"], P["lilac"], "#BFD5EA"]
    heights = [0.5, 0.4, 0.56, 0.44, 0.52, 0.42]
    hw = W / 5.2
    for i in range(6):
        x, h = -0.03 * W + i * hw, heights[i] * H
        c = cols[i]
        top = base - h
        m.append(_r(x, top, hw * 0.97, h, c, 0, LINE, 3))
        m.append(_r(x - 5, top - 0.02 * H, hw * 0.97 + 10, 0.024 * H, shade(c, 0.22), 4, LINE, 3))
        rows = max(1, int((h - 0.14 * H) / (0.12 * H)))
        for r in range(rows):
            wy = top + 0.05 * H + r * 0.12 * H
            for cx in (0.14, 0.56):
                m.append(_r(x + hw * cx, wy, hw * 0.27, 0.065 * H, "#FFF7E8", 4, shade(c, 0.35), 2.5))
            m.append(f'<path d="M{x + hw * 0.08:.0f} {wy + 0.075 * H:.0f} L{x + hw * 0.9:.0f} {wy + 0.075 * H:.0f}" stroke="{shade(c, .35)}" stroke-width="3"/>')
        m.append(_r(x + hw * 0.1, base - 0.085 * H, hw * 0.76, 0.085 * H, shade(c, 0.1), 3, shade(c, 0.35), 2.5))
        m.append("".join(f'<path d="M{x + hw * 0.1:.0f} {base - 0.085 * H + k * 0.017 * H:.0f} L{x + hw * 0.86:.0f} {base - 0.085 * H + k * 0.017 * H:.0f}" '
                         f'stroke="{shade(c, .3)}" stroke-width="2"/>' for k in range(1, 5)))
    fs = max(36, round(0.045 * u))
    zones: list = []
    m.append(_sign(-0.03 * W + 1.12 * hw, base - 0.27 * H, hw * 0.73, fs * 1.6, "#E5554F", "PHỞ", fs, tid=f"{sid}-z0", zones=zones))
    m.append(_sign(-0.03 * W + 3.06 * hw, base - 0.29 * H, hw * 0.88, fs * 1.6, "#3E8E7E", "CÀ PHÊ", fs, tid=f"{sid}-z1", zones=zones))
    # power lines
    m.append(f'<path d="M0 {0.2 * H:.0f} Q{W * 0.5:.0f} {0.3 * H:.0f} {W:.0f} {0.18 * H:.0f} M0 {0.24 * H:.0f} Q{W * 0.45:.0f} {0.34 * H:.0f} {W:.0f} {0.23 * H:.0f}" '
             f'fill="none" stroke="{LINE}" stroke-width="2.5" opacity="0.55"/>')
    # road with a passing xe máy, then the sidewalk the characters stand on
    m.append(_r(0, base, W, fy - base, "#CFC8BD"))
    m.append("".join(_r(x, base + (fy - base) * 0.45, W * 0.05, 5, "#FFFFFF", 2) for x in [W * k / 8 for k in range(9)]))
    k = u * 0.0018
    m.append(f'<g transform="translate(0,{base + (fy - base) * 0.75:.0f})"><g id="{sid}-moto">{_moto(k, "#E77A5F")}</g></g>')
    tw.append(_ft(f"#{sid}-moto", f"x: {-0.12 * W:.0f}", f'x: {1.15 * W:.0f}, duration: {max(3.5, min(7.0, dur * 0.8)):.2f}, ease: "none"', 0.3))
    m.append(_r(0, fy - 0.022 * H, W, H, "#EBDDC7"))
    m.append(_r(0, fy - 0.03 * H, W, 0.014 * H, "#D9C7AC", 0, LINE, 2))
    m.append("".join(f'<path d="M{x:.0f} {fy - 0.016 * H:.0f} L{x - 0.03 * W:.0f} {H:.0f}" stroke="#D9C7AC" stroke-width="3"/>' for x in [W * k / 7 for k in range(1, 8)]))
    # a tree at the edge
    tx = W * 0.965
    m.append(_r(tx - 0.012 * W, fy - 0.3 * H, 0.024 * W, 0.29 * H, "#A8744F", 6, LINE, 3))
    m.append("".join(f'<circle cx="{tx + dx * u:.0f}" cy="{fy - 0.36 * H + dy * u:.0f}" r="{r * u:.0f}" fill="#9FD3A8" stroke="{LINE}" stroke-width="3"/>'
                     for dx, dy, r in ((-0.06, 0.02, 0.06), (0.05, 0.03, 0.06), (0, -0.045, 0.07))))
    return "".join(m), tw, zones


def set_office(sid, W, H, fy, dur, u):
    P = PALETTE
    m, tw = [_r(0, 0, W, H, "#F6E9CF")], []
    # window onto the city
    wx, wy, ww, wh = W * 0.07, H * 0.1, W * 0.34, H * 0.42
    m.append(_r(wx, wy, ww, wh, "#D7ECF4", 8, LINE, 4))
    m.append("".join(_r(wx + ww * a, wy + wh * (1 - b), ww * 0.16, wh * b, c, 0) for a, b, c in
                     ((0.04, .5, "#BFD5EA"), (0.22, .72, "#C9DDF0"), (0.4, .42, "#B4CCE4"), (0.58, .62, "#C9DDF0"), (0.78, .5, "#BFD5EA"))))
    m.append(f'<path d="M{wx + ww / 2:.0f} {wy:.0f} L{wx + ww / 2:.0f} {wy + wh:.0f} M{wx:.0f} {wy + wh / 2:.0f} L{wx + ww:.0f} {wy + wh / 2:.0f}" stroke="#FFFFFF" stroke-width="8"/>')
    m.append(_r(wx, wy, ww, wh, "none", 8, LINE, 4))
    m.append(_r(wx - 10, wy + wh, ww + 20, 14, "#FFFFFF", 4, LINE, 3))
    # wall clock with a moving hand
    cx, cy, cr = W * 0.6, H * 0.2, u * 0.065
    m.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{cr:.0f}" fill="#FFFFFF" stroke="{LINE}" stroke-width="4"/>')
    m.append("".join(f'<circle cx="{cx + 0.78 * cr * __import__("math").cos(a * 0.5236):.0f}" cy="{cy + 0.78 * cr * __import__("math").sin(a * 0.5236):.0f}" r="3" fill="{LINE}"/>' for a in range(12)))
    m.append(f'<path d="M{cx:.0f} {cy:.0f} L{cx:.0f} {cy - cr * 0.45:.0f}" stroke="{LINE}" stroke-width="5" stroke-linecap="round"/>')
    m.append(f'<g transform="translate({cx:.0f},{cy:.0f})"><g id="{sid}-hand"><path d="M0 0 L0 {-cr * 0.7:.0f}" stroke="#D2643F" stroke-width="4" stroke-linecap="round"/></g></g>')
    tw.append(_ft(f"#{sid}-hand", 'rotation: 0, svgOrigin: "0 0"', f'rotation: {min(360, dur * 30):.0f}, svgOrigin: "0 0", duration: {dur:.2f}, ease: "none"', 0))
    # floor, desk with a laptop and a mug, a plant
    m.append(_r(0, fy - 0.02 * H, W, H, "#E3CDA8"))
    m.append("".join(f'<path d="M0 {fy + k * 0.05 * H:.0f} L{W:.0f} {fy + k * 0.05 * H:.0f}" stroke="#D2B98F" stroke-width="3"/>' for k in range(5)))
    dx0, dw, dy = W * 0.66, W * 0.32, fy - 0.24 * H
    m.append(_r(dx0, dy, dw, 0.03 * H, "#C99A6B", 6, LINE, 3))
    m.append(_r(dx0 + dw * 0.06, dy + 0.03 * H, 0.016 * W, 0.2 * H, "#A8744F", 4, LINE, 3) + _r(dx0 + dw * 0.9, dy + 0.03 * H, 0.016 * W, 0.2 * H, "#A8744F", 4, LINE, 3))
    s = u * 0.16
    m.append(_icon_at("laptop", dx0 + dw * 0.18, dy - s * 0.72, s, "#4A7DBA"))
    m.append(_icon_at("tea", dx0 + dw * 0.66, dy - s * 0.62, s * 0.6, "#D2643F"))
    m.append(_icon_at("sprout", W * 0.47, fy - u * 0.2, u * 0.16, "#3E8E7E"))
    m.append(_r(W * 0.47 + u * 0.035, fy - u * 0.07, u * 0.09, u * 0.07, "#E77A5F", 6, LINE, 3))
    return "".join(m), tw, []


def set_cafe(sid, W, H, fy, dur, u):
    P = PALETTE
    m, tw = [_r(0, 0, W, H, "#F7D9BF")], []
    # retro tiles on the lower wall
    ty = H * 0.48
    m.append(_r(0, ty, W, fy - ty, P["mint"]))
    step = u * 0.06
    m.append("".join(f'<path d="M{x:.0f} {ty:.0f} L{x:.0f} {fy:.0f}" stroke="#A9D6C0" stroke-width="2"/>' for x in [k * step for k in range(int(W / step) + 1)]))
    m.append("".join(f'<path d="M0 {y:.0f} L{W:.0f} {y:.0f}" stroke="#A9D6C0" stroke-width="2"/>' for y in [ty + k * step for k in range(int((fy - ty) / step) + 1)]))
    m.append(_r(0, ty - 8, W, 12, "#FFFFFF", 0, LINE, 2))
    # menu board
    fs = max(40, round(0.055 * u))
    fs2 = max(36, round(0.036 * u))
    bw, bh = max(W * 0.3, fs2 * 9.5), u * 0.21
    bx, by = min(W * 0.6, W * 0.97 - bw), H * 0.05
    m.append(_r(bx - 10, by - 10, bw + 20, bh + 20, "#A8744F", 10, LINE, 3) + _r(bx, by, bw, bh, "#2F5D50", 6))
    m.append(f'<g id="{sid}-z0"><text x="{bx + bw / 2:.0f}" y="{by + bh * 0.46:.0f}" text-anchor="middle" font-family="Inter" font-weight="800" font-size="{fs}" fill="#FFF7E8">CÀ PHÊ</text>'
             f'<text x="{bx + bw / 2:.0f}" y="{by + bh * 0.82:.0f}" text-anchor="middle" font-family="Inter" font-weight="600" font-size="{fs2}" fill="#FBE3A1">sữa đá · đen đá</text></g>')
    zones = [(f"{sid}-z0", bx, by, bx + bw, by + bh)]
    # two pendant lamps that sway a little
    for i, lx in enumerate((W * 0.22, W * 0.44)):
        m.append(f'<g transform="translate({lx:.0f},0)"><g id="{sid}-lp{i}"><path d="M0 0 L0 {H * 0.14:.0f}" stroke="{LINE}" stroke-width="3"/>'
                 f'<path d="M{-u * 0.05:.0f} {H * 0.14 + u * 0.05:.0f} Q0 {H * 0.14 - u * 0.03:.0f} {u * 0.05:.0f} {H * 0.14 + u * 0.05:.0f} Z" fill="#FBE3A1" stroke="{LINE}" stroke-width="3"/>'
                 f'<ellipse cx="0" cy="{H * 0.14 + u * 0.06:.0f}" rx="{u * 0.05:.0f}" ry="{u * 0.012:.0f}" fill="#FFF3B0"/></g></g>')
        period = 2.6 + 0.4 * i
        tw.append(f'tl.fromTo("#{sid}-lp{i}", {{ rotation: -2.5, svgOrigin: "0 0" }}, {{ rotation: 2.5, svgOrigin: "0 0", duration: {period:.2f}, '
                  f'ease: "sine.inOut", repeat: {max(0, int(dur / period))}, yoyo: true }}, 0);')
    # floor; low table with cà phê sữa đá under a dripping phin; a stack of plastic stools in the corner
    m.append(_r(0, fy - 0.02 * H, W, H, "#E8D3B0"))
    m.append("".join(f'<path d="M{x:.0f} {fy - 0.02 * H:.0f} L{x - 0.06 * W:.0f} {H:.0f}" stroke="#D8BE95" stroke-width="3"/>' for x in [W * k / 9 for k in range(1, 10)]))
    tx, tw_, th = W * 0.5, W * 0.13, fy - 0.12 * H
    m.append(_r(tx - tw_ / 2, th, tw_, 0.022 * H, "#C99A6B", 6, LINE, 3))
    m.append(f'<path d="M{tx - tw_ * 0.38:.0f} {th + 0.02 * H:.0f} L{tx - tw_ * 0.44:.0f} {fy - 0.01 * H:.0f} M{tx + tw_ * 0.38:.0f} {th + 0.02 * H:.0f} L{tx + tw_ * 0.44:.0f} {fy - 0.01 * H:.0f}" '
             f'stroke="#A8744F" stroke-width="8" stroke-linecap="round"/>')
    s = u * 0.13
    # cà phê phin: the filter sits on the glass and drips into it, a drop every ~0.8 s; an iced glass beside it
    m.append(_icon_at("phin", tx - s * 0.95, th - s * 0.95, s, "#8A5A2B"))
    m.append(_icon_at("coffee", tx + s * 0.02, th - s * 0.82, s * 0.85, "#8A5A2B"))
    for k in range(2):
        did = f"{sid}-dr{k}"
        m.append(f'<circle id="{did}" cx="{tx - s * 0.45:.0f}" cy="{th - s * 0.95 + s * 0.6:.0f}" r="{u * 0.005:.1f}" fill="#6B3E1E" opacity="0"/>')
        tw.append(f'tl.fromTo("#{did}", {{ y: 0, opacity: 0.9 }}, {{ y: {s * 0.18:.0f}, opacity: 0, duration: 0.8, ease: "power2.in", '
                  f'repeat: {max(0, int(dur / 1.6) - 1)}, repeatDelay: 0.8 }}, {0.4 + 0.8 * k:.2f});')
    for j in range(3):
        m.append(_stool(W * 0.93, fy - j * u * 0.022, u * 0.0022, "#E5554F" if j % 2 == 0 else "#4A7DBA"))
    m.append(_icon_at("sprout", W * 0.02, fy - u * 0.2, u * 0.14, "#3E8E7E"))
    return "".join(m), tw, zones


def set_room(sid, W, H, fy, dur, u):
    P = PALETTE
    m, tw = [_r(0, 0, W, H, "#ECE4F4")], []
    wx, wy, ww, wh = W * 0.1, H * 0.1, W * 0.24, H * 0.36
    m.append(_r(wx, wy, ww, wh, "#FFE7C2", 8, LINE, 4))
    m.append(f'<circle cx="{wx + ww * 0.7:.0f}" cy="{wy + wh * 0.35:.0f}" r="{u * 0.04:.0f}" fill="#FBE3A1"/>')
    m.append(_r(wx, wy, ww, wh, "none", 8, LINE, 4))
    m.append(f'<path d="M{wx - 20:.0f} {wy - 14:.0f} Q{wx + ww * 0.1:.0f} {wy + wh * 0.5:.0f} {wx - 6:.0f} {wy + wh + 16:.0f} L{wx - 36:.0f} {wy + wh + 16:.0f} L{wx - 36:.0f} {wy - 14:.0f} Z" fill="{P["pink"]}" stroke="{LINE}" stroke-width="3"/>')
    m.append(f'<path d="M{wx + ww + 20:.0f} {wy - 14:.0f} Q{wx + ww * 0.9:.0f} {wy + wh * 0.5:.0f} {wx + ww + 6:.0f} {wy + wh + 16:.0f} L{wx + ww + 36:.0f} {wy + wh + 16:.0f} L{wx + ww + 36:.0f} {wy - 14:.0f} Z" fill="{P["pink"]}" stroke="{LINE}" stroke-width="3"/>')
    m.append(_r(wx - 50, wy - 20, ww + 100, 10, "#A8744F", 4))
    # shelf with books and a small plant
    sx, sy = W * 0.62, H * 0.24
    m.append(_r(sx, sy, W * 0.24, 12, "#C99A6B", 4, LINE, 3))
    m.append("".join(_r(sx + W * 0.02 + k * W * 0.022, sy - h * H, W * 0.018, h * H, c, 3, LINE, 2.5) for k, (h, c) in
                     enumerate(((.08, "#E77A5F"), (.1, "#5B8FD1"), (.07, "#FBE3A1"), (.09, "#7DB892")))))
    m.append(_icon_at("sprout", sx + W * 0.15, sy - u * 0.1, u * 0.1, "#3E8E7E"))
    # floor, mattress with pillow and blanket, a standing fan that turns
    m.append(_r(0, fy - 0.02 * H, W, H, "#D9C3A5"))
    m.append(f'<ellipse cx="{W * 0.45:.0f}" cy="{fy + 0.06 * H:.0f}" rx="{W * 0.22:.0f}" ry="{0.05 * H:.0f}" fill="{P["peach"]}" stroke="{LINE}" stroke-width="3"/>')
    bx, bw = W * 0.66, W * 0.32
    m.append(_r(bx, fy - 0.1 * H, bw, 0.09 * H, "#FFFFFF", 14, LINE, 3))
    m.append(_r(bx + bw * 0.06, fy - 0.15 * H, bw * 0.24, 0.06 * H, P["butter"], 14, LINE, 3))
    m.append(_r(bx + bw * 0.38, fy - 0.12 * H, bw * 0.6, 0.1 * H, P["mint"], 14, LINE, 3))
    fx, fy0 = W * 0.06, fy - 0.36 * H
    m.append(f'<path d="M{fx:.0f} {fy0:.0f} L{fx:.0f} {fy - 0.01 * H:.0f}" stroke="{LINE}" stroke-width="6"/>'
             f'<ellipse cx="{fx:.0f}" cy="{fy - 0.01 * H:.0f}" rx="{u * 0.05:.0f}" ry="{u * 0.012:.0f}" fill="#8FA3B8" stroke="{LINE}" stroke-width="3"/>')
    fr = u * 0.075
    m.append(f'<circle cx="{fx:.0f}" cy="{fy0:.0f}" r="{fr:.0f}" fill="#DFF1FA" stroke="{LINE}" stroke-width="4"/>')
    blades = "".join(f'<ellipse cx="0" cy="{-fr * 0.42:.0f}" rx="{fr * 0.2:.0f}" ry="{fr * 0.42:.0f}" fill="#8FC1E3" stroke="{LINE}" stroke-width="2.5" transform="rotate({a})"/>'
                     for a in (0, 120, 240))
    m.append(f'<g transform="translate({fx:.0f},{fy0:.0f})"><g id="{sid}-fan">{blades}<circle r="{fr * 0.14:.0f}" fill="#FFFFFF" stroke="{LINE}" stroke-width="3"/></g></g>')
    tw.append(_ft(f"#{sid}-fan", 'rotation: 0, svgOrigin: "0 0"', f'rotation: {dur * 400:.0f}, svgOrigin: "0 0", duration: {dur:.2f}, ease: "none"', 0))
    return "".join(m), tw, []


def set_phone(sid, W, H, fy, dur, u):
    P = PALETTE
    m, tw = [_r(0, 0, W, H, "#DCEFE6")], []
    m.append("".join(f'<circle cx="{W * x:.0f}" cy="{H * y:.0f}" r="{u * r:.0f}" fill="#CBE7DA"/>' for x, y, r in
                     ((0.1, 0.18, 0.12), (0.38, 0.86, 0.16), (0.95, 0.1, 0.1), (0.5, 0.2, 0.05))))
    m.append(_r(0, fy, W, H, "#CFE6DA"))
    ph = min(H * 0.8, W * 0.84)
    pw = ph * 0.5
    px, py = W * 0.72 - pw / 2, fy - ph - 0.01 * H
    m.append(_r(px, py, pw, ph, "#2E2A35", pw * 0.12, LINE, 4))
    sx, sy, sw, sh = px + pw * 0.06, py + ph * 0.05, pw * 0.88, ph * 0.9
    m.append(_r(sx, sy, sw, sh, "#FFFDF8", pw * 0.07))
    m.append(_r(px + pw * 0.38, py + ph * 0.015, pw * 0.24, ph * 0.018, "#4A4655", 6))
    m.append(_r(sx, sy, sw, sh * 0.1, "#D2643F", pw * 0.07))
    m.append(_r(sx, sy + sh * 0.06, sw, sh * 0.04, "#D2643F"))
    for k, (yy, ww, c, right) in enumerate(((0.16, 0.6, P["sky"], False), (0.3, 0.5, P["butter"], True), (0.44, 0.66, P["sky"], False),
                                            (0.6, 0.44, P["butter"], True))):
        bx = sx + sw * (0.94 - ww) if right else sx + sw * 0.06
        m.append(_r(bx, sy + sh * yy, sw * ww, sh * 0.1, c, sh * 0.03, LINE, 2.5))
    # a heart that pulses on the screen (someone liked it)
    hs = u * 0.07
    hx, hy = sx + sw * 0.8, sy + sh * 0.8
    m.append(f'<g transform="translate({hx:.0f},{hy:.0f})"><g id="{sid}-hrt">{_icon_at("heart", -hs / 2, -hs / 2, hs, "#E5554F")}</g></g>')
    tw.append(f'tl.fromTo("#{sid}-hrt", {{ scale: 0.85, svgOrigin: "0 0" }}, {{ scale: 1.15, svgOrigin: "0 0", duration: 0.6, ease: "sine.inOut", '
              f'repeat: {max(0, int(dur / 0.6))}, yoyo: true }}, 0);')
    return "".join(m), tw, []


def set_plain(sid, W, H, fy, dur, u):
    P = PALETTE
    m, tw = [_r(0, 0, W, H, P["bg"])], []
    m.append(f'<ellipse cx="{W * 0.5:.0f}" cy="{H * 0.48:.0f}" rx="{W * 0.36:.0f}" ry="{H * 0.36:.0f}" fill="{P["butter"]}" opacity="0.55"/>')
    m.append(f'<ellipse cx="{W * 0.5:.0f}" cy="{fy + 0.01 * H:.0f}" rx="{W * 0.4:.0f}" ry="{0.035 * H:.0f}" fill="#EADCC3"/>')
    rng = random.Random(4)
    for k in range(8):
        cid = f"{sid}-cf{k}"
        x, y = rng.uniform(0.06, 0.94) * W, rng.uniform(0.08, 0.6) * H
        c = P[["mint", "pink", "sky", "lilac", "peach"][k % 5]]
        m.append(f'<circle id="{cid}" cx="{x:.0f}" cy="{y:.0f}" r="{u * rng.uniform(0.008, 0.016):.1f}" fill="{c}"/>')
        tw.append(f'tl.fromTo("#{cid}", {{ y: 0 }}, {{ y: {-u * 0.03:.0f}, duration: {2 + k % 3 * 0.5:.2f}, ease: "sine.inOut", repeat: {max(0, int(dur / 2))}, yoyo: true }}, {0.2 * k:.2f});')
    return "".join(m), tw, []


SET_FN = {"street": set_street, "office": set_office, "cafe": set_cafe, "room": set_room, "phone": set_phone, "plain": set_plain}


# ---------------------------------------------------------------- the stage scene

def floor_y(L) -> float:
    return L.h * (0.7 if L.h > L.w else 0.78)


def char_scale(L, look: dict) -> float:
    k = 0.74 if C.norm_look(look)["age"] == "child" else 1.0
    return (0.5 if L.w > L.h else 0.46) * L.u / C.RIG_H * k


def default_xs(n: int) -> list[float]:
    return {1: [0.42], 2: [0.28, 0.66], 3: [0.18, 0.47, 0.76]}.get(n, [0.5])


def _norm_words(s: str) -> list[str]:
    return [w for w in (re.sub(r"[^\w]", "", x.lower()) for x in s.split()) if w]


def speech_span(text: str, words: list[dict], t_from: float) -> tuple[float, float]:
    """When a bubble's words are spoken: the first run of narration words (at or after its appearance) that starts
    with the bubble's first words; otherwise the bubble's own length from its appearance."""
    bw = _norm_words(text)
    nw = [re.sub(r"[^\w]", "", w["word"].lower()) for w in words]
    k = min(2, len(bw))
    for i in range(len(words)):
        if words[i]["start"] < t_from - 0.6:
            continue
        if bw and nw[i:i + k] == bw[:k]:
            j = min(len(words) - 1, i + len(bw) - 1)
            return words[i]["start"], words[j]["end"]
    return t_from + 0.1, t_from + 0.1 + 0.27 * max(2, len(bw))


def text_width(text: str, fs: float) -> float:
    """Inter 800 at size fs, roughly: wide letters, narrow letters, spaces (good to ~10 %, enough to size a bubble)."""
    w = 0.0
    for ch in text:
        w += 0.3 if ch == " " else (0.36 if ch in "il.,'!:;|" else (0.84 if ch in "MWmwĐ" else 0.6))
    return w * fs


def bubbles_of(v: dict) -> list[dict]:
    bs = list(v.get("bubbles") or [])
    if v.get("bubble"):
        bs = [v["bubble"]] + bs
    return [b for b in bs if isinstance(b, dict) and b.get("text")]


def stage(L, sid, v, dur, cue):
    W, H, u = L.w, L.h, L.u
    fy = floor_y(L)
    cast = getattr(L, "cast", {}) or {}
    chars = [c for c in (v.get("characters") or []) if isinstance(c, dict) and c.get("id")][:3]
    words = v.get("_words") or []
    speech_end = words[-1]["end"] if words else max(0.8, dur - 0.7)
    xs = default_xs(len(chars))
    tw, html_parts = [], []
    set_name = v.get("set", "plain") if v.get("set") in SETS else "plain"
    set_svg, set_tw, zones = SET_FN[set_name](sid, W, H, fy, dur, u)
    tw += set_tw
    tw.append(_ft(f"#{sid}-set", f'scale: 1, svgOrigin: "{W / 2:.0f} {fy:.0f}"', f'scale: 1.03, svgOrigin: "{W / 2:.0f} {fy:.0f}", duration: {dur:.2f}, ease: "none"', 0))

    # bubbles: when each opens and closes, and whose mouth moves while it is spoken
    bubs = []
    t_prev = 0.0
    for i, b in enumerate(bubbles_of(v)):
        t = cue(b["cue"], 0.6 + 2.2 * i) if b.get("cue") else 0.6 + 2.2 * i
        t = max(t, t_prev + 0.8 if i else 0.2)
        bubs.append({**b, "t": round(t, 3), "span": speech_span(b["text"], words, t)})
        t_prev = t
    for i, b in enumerate(bubs):
        end = bubs[i + 1]["t"] - 0.05 if i + 1 < len(bubs) else dur - 0.25
        if b.get("until"):
            end = min(end, max(b["t"] + 1.2, cue(b["until"], end)))
        b["end"] = end

    defs = [svg_filter(f"{sid}-stk", r=max(4.0, u * 0.0055), drop=u * 0.008)]
    shadows, bodies, xs_px = [], [], {}
    first = set(v.get("_tags") or [])
    tag_html = []
    rigs = {}
    for i, ch in enumerate(chars):
        reg = cast.get(ch["id"], {})
        look = {**(reg.get("look") or {}), **(ch.get("look") or {})}
        lk = C.norm_look(look)
        cid = f"{sid}-{C._sid(ch['id'])}"
        x = float(ch.get("x", xs[i]))
        X = x * W
        xs_px[ch["id"]] = X
        others = [float(o.get("x", xs[j])) for j, o in enumerate(chars) if o is not ch]
        side = 1 if (sum(others) / len(others) if others else 0.5) >= x else -1
        sc = char_scale(L, look)
        rigs[ch["id"]] = {"cid": cid, "X": X, "scale": sc, "look": lk, "side": side}
        shadows.append(f'<g transform="translate({X:.1f},{fy + 2:.1f})"><g id="{cid}-sh"><ellipse cx="0" cy="0" rx="{48 * sc:.1f}" ry="{9 * sc:.1f}" '
                       f'fill="#3B302C" opacity="0.16"/></g></g>')
        bodies.append(f'<g filter="url(#{sid}-stk)"><g transform="translate({X:.1f},{fy:.1f})"><g id="{cid}-mv"><g transform="scale({sc:.4f})">'
                      f'{C.rig_svg(cid, look, side, ch.get("expression") or "neutral")}</g></g></g></g>')
        tag = ch.get("tag", None)
        if tag is None:
            tag = bool(reg.get("real")) or ch["id"] in first
        if tag:
            text = tag if isinstance(tag, str) else (reg.get("tag") or reg.get("name") or ch["id"])
            rigs[ch["id"]]["tag"] = f"#{cid}-tag"
            fs = L.fs(L.READ)
            tag_html.append(f'<div style="position:absolute;left:{X - L.w * 0.2:.0f}px;width:{L.w * 0.4:.0f}px;top:{fy + L.px(0.016):.0f}px;text-align:center;">'
                            f'<div id="{cid}-tag" class="stk-tag" style="display:inline-block;padding:{L.px(0.006)}px {L.px(0.02)}px;border-radius:999px;'
                            f'background:#FFFFFF;border:3px solid {C.INK};color:{PALETTE["ink"]};font-weight:800;font-size:{fs}px;line-height:1.15;white-space:nowrap;">'
                            f'<span style="display:inline-block;width:{L.px(0.016)}px;height:{L.px(0.016)}px;border-radius:50%;background:{lk["shirt"]};'
                            f'border:2px solid {C.INK};margin-right:{L.px(0.01)}px;vertical-align:middle;"></span>{E(text)}</div></div>')

    for i, ch in enumerate(chars):
        r = rigs[ch["id"]]
        events = [{"t": 0.0, "expression": ch.get("expression"), "action": ch.get("action") or "idle"}]
        for c in ch.get("cues") or []:
            if not isinstance(c, dict):
                continue
            t = cue(c["cue"], dur * 0.5) if c.get("cue") else float(c.get("at", dur * 0.5))
            e = {"t": max(0.05, t), "expression": c.get("expression"), "action": c.get("action")}
            if c.get("x") is not None:
                e["x"] = float(c["x"]) * W
            if c.get("toward") is not None:
                e["toward"] = float(c["toward"]) * W
            events.append(e)
        if (ch.get("action") == "walk_in") and ch.get("x") is not None:
            events[0]["x"] = r["X"]
        spans = [b["span"] for b in bubs if b.get("who") == ch["id"] and b.get("style") != "think"]
        ch2 = {**ch, "_long_hair": r["look"]["hair"] == "long"}
        pxs = [float(p.get("x", 0.5)) for p in v.get("props") or [] if isinstance(p, dict)]
        point_side = (1 if sum(pxs) / len(pxs) * W >= r["X"] else -1) if pxs else None  # point at the props, else the partner
        ctw, K, xtrack = C.choreograph(r["cid"], ch2, x_px=r["X"], scale=r["scale"], W=W, dur=dur, events=events, words=words,
                                       talk_spans=spans, speech_end=speech_end, seed=7 + 13 * i, partner_side=r["side"],
                                       extra_x=[r["tag"]] if r.get("tag") else None, point_side=point_side)
        r["K"] = K
        tw += ctw
        if r.get("tag"):
            tw.append(_ft(r["tag"], "opacity: 0, scale: 0.6", 'opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)"', 0.5))

    # props: sticker badges that pop in on their word, then float
    ZK = C.Keys()
    prop_hidden: set[str] = set()
    props_svg = []
    for i, p in enumerate(v.get("props") or []):
        key = L.icon_of(p)
        if key not in ICONS:
            continue
        s = L.px(float(p.get("size", 0.12)))
        px_, py_ = float(p.get("x", 0.5)) * W, float(p.get("y", 0.5)) * H
        col = L.color(p, PROP_COLORS[i % len(PROP_COLORS)]) if (p.get("color") or p.get("concept")) else PROP_COLORS[i % len(PROP_COLORS)]
        disc = mix(col, "#FFFFFF", 0.82)
        art = stickerize(ICONS[key](s * 0.78, col))
        pid = f"{sid}-p{i}"
        props_svg.append(f'<g transform="translate({px_:.1f},{py_:.1f})"><g id="{pid}" filter="url(#{sid}-stk)" opacity="0"><g id="{pid}f">'
                         f'<circle cx="0" cy="0" r="{s * 0.56:.1f}" fill="{disc}" stroke="{C.INK}" stroke-width="3"/>'
                         f'<g transform="translate({-s * 0.39:.1f},{-s * 0.39:.1f})">{art}</g></g></g></g>')
        t = cue(p["cue"], 0.4 + 0.3 * i) if p.get("cue") else 0.4 + 0.3 * i
        for zid, zx0, zy0, zx1, zy1 in zones:  # a prop that lands on set lettering hides it
            if zx0 < px_ + s * 0.62 and zx1 > px_ - s * 0.62 and zy0 < py_ + s * 0.62 and zy1 > py_ - s * 0.62:
                ZK.add(f"#{zid}", "opacity", t, 0, 0.2, "power2.out")
                prop_hidden.add(zid)
        tw.append(_ft(f"#{pid}", 'opacity: 0, scale: 0.2, rotation: -14, svgOrigin: "0 0"',
                      'opacity: 1, scale: 1, rotation: 0, svgOrigin: "0 0", duration: 0.5, ease: "back.out(2.2)"', t))
        reps = max(0, int((dur - t) / 1.4) - 1)
        tw.append(f'tl.fromTo("#{pid}f", {{ y: 0 }}, {{ y: {-L.px(0.012)}, duration: 1.4, ease: "sine.inOut", repeat: {reps}, yoyo: true }}, {t + 0.5:.2f});')
        if p.get("out_cue"):
            tw.append(_ft(f"#{pid}", "opacity: 1", 'opacity: 0, duration: 0.25, ease: "power2.in"', cue(p["out_cue"], dur - 1), later=True))

    svg = (f'<svg id="{sid}-sv" class="raw" width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="position:absolute;left:0;top:0;overflow:hidden">'
           f'<defs>{"".join(defs)}</defs><g id="{sid}-set">{set_svg}</g>{"".join(shadows)}{"".join(bodies)}{"".join(props_svg)}</svg>')

    # speech bubbles above the speaker's head
    bub_html = []
    fsb = L.fs(0.044)
    maxw = min(W * 0.44, L.px(0.8)) if W > H else W * 0.8
    for i, b in enumerate(bubs):
        r = rigs.get(b.get("who"))
        if not r:
            continue
        K = r["K"]
        bx = r["X"] + K.value_at(f"#{r['cid']}-mv", "x", b["t"] + 0.01)
        sit = K.value_at(f"#{r['cid']}-pose", "y", b["t"] + 0.6) * r["scale"]
        head_top = fy - (C.RIG_H * 0.97) * r["scale"] + sit
        if r["look"]["hair"] == "non_la":
            head_top -= 18 * r["scale"]
        bottom = head_top - L.px(0.03)
        pad = L.px(0.032)
        est = text_width(b["text"], fsb)
        lines = max(1, -(-est // (maxw - 2 * pad)))
        bw_ = min(maxw, est / lines * 1.08 + 2 * pad + 8)
        left = min(max(L.px(0.03), bx - bw_ / 2), W - L.px(0.03) - bw_)
        tail = min(max(bx - left, L.px(0.05)), bw_ - L.px(0.05))
        bid = f"{sid}-b{i}"
        think = b.get("style") == "think"
        radius = L.px(0.06) if think else L.px(0.035)
        tail_html = ((f'<div style="position:absolute;left:{tail - L.px(0.03):.0f}px;bottom:{-L.px(0.035):.0f}px;width:{L.px(0.026)}px;height:{L.px(0.026)}px;'
                      f'border-radius:50%;background:#fff;border:3.5px solid {C.INK};"></div>'
                      f'<div style="position:absolute;left:{tail - L.px(0.012):.0f}px;bottom:{-L.px(0.06):.0f}px;width:{L.px(0.014)}px;height:{L.px(0.014)}px;'
                      f'border-radius:50%;background:#fff;border:3px solid {C.INK};"></div>') if think else
                     (f'<div style="position:absolute;left:{tail - L.px(0.018):.0f}px;bottom:{-L.px(0.016):.0f}px;width:{L.px(0.034)}px;height:{L.px(0.034)}px;'
                      f'background:#fff;border-right:3.5px solid {C.INK};border-bottom:3.5px solid {C.INK};transform:rotate(45deg);"></div>'))
        bub_html.append(
            f'<div id="{bid}" style="position:absolute;left:{left:.0f}px;width:{bw_:.0f}px;bottom:{H - bottom:.0f}px;transform-origin:{tail:.0f}px 100%;">'
            f'<div style="position:relative;padding:{L.px(0.018)}px {pad}px;background:#fff;border:3.5px solid {C.INK};border-radius:{radius}px;'
            f'box-shadow:0 0 0 {L.px(0.006)}px #fff, 0 {L.px(0.012)}px {L.px(0.024)}px rgba(84,62,38,0.25);text-align:center;'
            f'font-size:{fsb}px;line-height:1.22;font-weight:800;color:{PALETTE["ink"]};text-shadow:none;text-wrap:balance;">{E(b["text"])}</div>'
            f'{tail_html}</div>')
        tw.append(_ft(f"#{bid}", "opacity: 0, scale: 0.4, y: 20", 'opacity: 1, scale: 1, y: 0, duration: 0.42, ease: "back.out(2)"', b["t"]))
        bh_ = lines * fsb * 1.22 + 2 * L.px(0.018) + 8
        for zid, zx0, zy0, zx1, zy1 in zones:  # set lettering under the bubble steps back: never words over words
            if zid in prop_hidden:
                continue
            if zx0 < left + bw_ + 10 and zx1 > left - 10 and zy0 < bottom + 10 and zy1 > bottom - bh_ - 10:
                ZK.add(f"#{zid}", "opacity", b["t"], 0, 0.2, "power2.out")
                ZK.add(f"#{zid}", "opacity", b["end"], 1, 0.3, "power2.in")
        tw.append(_ft(f"#{bid}", "opacity: 1, scale: 1", 'opacity: 0, scale: 0.85, duration: 0.2, ease: "power2.in"', b["end"] - 0.2, later=True))

    tw += ZK.tweens()
    cap_html = ""
    if v.get("caption"):
        speaker_left = any(rigs.get(b.get("who"), {}).get("X", W) < W * 0.5 for b in bubs)
        side = f"right:{L.px(0.05)}px;" if speaker_left else f"left:{L.px(0.05)}px;"
        cap_html = (f'<div id="{sid}-cap" style="position:absolute;{side}top:{L.px(0.1)}px;max-width:{W * 0.42:.0f}px;padding:{L.px(0.01)}px {L.px(0.024)}px;'
                    f'background:{PALETTE["butter"]};border:3px solid {C.INK};border-radius:{L.px(0.014)}px;font-weight:800;font-size:{L.fs(L.READ)}px;'
                    f'line-height:1.2;color:{PALETTE["ink"]};text-shadow:none;box-shadow:0 0 0 {L.px(0.006)}px #fff, 0 {L.px(0.01)}px {L.px(0.02)}px rgba(84,62,38,0.22);">'
                    f'{E(v["caption"])}</div>')
        t = cue(v["caption_cue"], 0.3) if v.get("caption_cue") else 0.3
        tw.append(_ft(f"#{sid}-cap", "opacity: 0, x: -30, rotation: -4", 'opacity: 1, x: 0, rotation: -1.5, duration: 0.45, ease: "back.out(1.8)"', t))

    m = f'<div id="{sid}-c" style="position:absolute;inset:0;overflow:hidden;">{svg}{"".join(tag_html)}{"".join(bub_html)}{cap_html}</div>'
    css = f"#{sid}-wrap .stk-tag {{ text-shadow: none; box-shadow: 0 0 0 {L.px(0.005)}px #fff, 0 {L.px(0.008)}px {L.px(0.016)}px rgba(84,62,38,0.22); }}"
    return m, css, tw


GENERATORS["stage"] = stage


# ---------------------------------------------------------------- film-level helpers

def stage_visuals(v: dict):
    """The stage pictures inside one visual (itself, or the stage shots of a `shots`)."""
    if v.get("type") == "stage":
        yield v
    elif v.get("type") == "shots":
        for sh in v.get("shots") or []:
            if isinstance(sh, dict) and sh.get("type") == "stage":
                yield sh


def prepare(visuals: list[dict], cast: list[dict] | None) -> list[dict]:
    """Mark where each character first appears (it gets its name tag there). Returns copies."""
    import copy

    out = [copy.deepcopy(v) for v in visuals]
    seen: set[str] = set()
    for v in out:
        for st in stage_visuals(v):
            ids = [c.get("id") for c in st.get("characters") or [] if isinstance(c, dict)]
            st["_tags"] = [i for i in ids if i not in seen]
            seen |= set(ids)
    return out


def has_stage(v: dict) -> bool:
    return any(True for _ in stage_visuals(v))
