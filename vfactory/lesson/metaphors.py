"""Metaphor scenes: the object on screen IS the explanation (HyperFrames explainer guidance).

Each one is a small machine whose working is the idea, built up one part per spoken cue:
- funnel   "one chosen out of many": a field of dots counts in, then all but a few dim and the survivors gather in a row
- ladder   a hierarchy that builds step by step; the top step lights and two qualities fuse onto it
- venn     three circles arrive on their words; their intersection fills and is named
- flywheel a heavy wheel pushed turn by turn, accelerating until speed lines appear and it runs on its own
- halo     cards wearing a halo; on the cue the halo fails and the verdict stamps over the card
- swap     one thing is let go (struck and dropped) so another can take its place
- company  who the company is, as a picture: its world drawn (a paper mill), facts on their words, a news clipping
- rise     why it won: the doubters' stamp, the climb against a flat market, rivals passed, products on the shelf

Same contract as scenes.py: ids prefixed with the beat id, fromTo tweens only, everything a function of timeline time,
deterministic (seeded) layouts.
"""

from __future__ import annotations

import math
import random
import re

from .scenes import GENERATORS, E, _fade, _fmt_num, _ft, _rise


def _blur_in(sel: str, at: float, dur: float = 0.35, px: int = 8) -> str:
    return _ft(sel, f'opacity: 0, filter: "blur({px}px)"', f'opacity: 1, filter: "blur(0px)", duration: {dur}, ease: "power2.out"', at)


def _head(L, sid, v, top: float = 0.13) -> tuple[str, list[str]]:
    """Kicker + optional heading in the top band."""
    m, tw = "", []
    if v.get("kicker"):
        m += f'<div id="{sid}-k" class="kicker" style="position:absolute;left:{L.px(0.1)}px;top:{L.h * top:.0f}px;">{E(v["kicker"])}</div>'
        tw.append(_fade(f"#{sid}-k", 0.05))
    if v.get("heading"):
        m += (f'<div id="{sid}-hd" class="serif" style="position:absolute;left:{L.px(0.1)}px;right:{L.px(0.1)}px;'
              f'top:{L.h * top + L.px(0.045):.0f}px;font-size:{L.fs(0.06)}px;line-height:1.15;">{E(v["heading"])}</div>')
        tw.append(_blur_in(f"#{sid}-hd", 0.2, 0.5))
    return m, tw


# ---------------------------------------------------------------- funnel: one chosen out of many

def funnel(L, sid, v, dur, cue):
    total, keep = int(v["total"]), int(v.get("keep", 0))
    rng = random.Random(int(v.get("seed", 7)))
    cols = int(v.get("cols", 55))
    rows = math.ceil(total / cols)
    gx0, gx1, gy0 = L.w * 0.08, L.w * 0.92, L.h * 0.40
    step = (gx1 - gx0) / (cols - 1)
    r = max(2.0, step * 0.28)
    pts = [(gx0 + (i % cols) * step, gy0 + (i // cols) * step) for i in range(total)]
    chosen = sorted(rng.sample(range(total), keep)) if keep else []
    full = bool(v.get("start_full"))
    # rows are groups so the field can sweep in with a handful of tweens instead of a thousand
    groups = []
    for row in range(rows):
        dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>' for x, y in pts[row * cols:(row + 1) * cols])
        groups.append(f'<g id="{sid}-r{row}">{dots}</g>')
    # survivors: drawn on top, then gathered into a centred row
    gap = min(L.px(0.075), (L.w * 0.8) / max(1, keep))
    row_y = gy0 + rows * step * 0.45
    surv, tw = [], []
    t_keep = cue(v.get("keep_cue", ""), dur * 0.35) if keep else 0
    for j, idx in enumerate(chosen):
        x, y = pts[idx]
        tx = L.w / 2 + (j - (keep - 1) / 2) * gap
        surv.append(f'<circle id="{sid}-s{j}" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{L.accent}" opacity="0"/>')
        tw.append(_ft(f"#{sid}-s{j}", f"opacity: 0, attr: {{r: {r:.1f}}}", f'opacity: 1, attr: {{r: {r * 2.2:.1f}}}, duration: 0.35, ease: "back.out(2)"',
                      t_keep + 0.05 * j))
        tw.append(_ft(f"#{sid}-s{j}", f"attr: {{cx: {x:.1f}, cy: {y:.1f}, r: {r * 2.2:.1f}}}",
                      f'attr: {{cx: {tx:.1f}, cy: {row_y:.1f}, r: {L.px(0.016):.1f}}}, duration: 1.1, ease: "power3.inOut"',
                      t_keep + 0.9 + 0.03 * j, later=True))
    counter_to = float(v.get("count_to", total))
    label = v.get("label", "")
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">
      <div style="position:absolute;left:0;right:0;top:{L.h * 0.12:.0f}px;text-align:center;">
        <div id="{sid}-l" class="kicker">{E(label)}</div>
        <div id="{sid}-n" class="serif" style="font-size:{L.fs(0.15)}px;line-height:1.05;margin-top:{L.px(0.012)}px;font-variant-numeric:tabular-nums;">
          <span id="{sid}-v">{_fmt_num(total if full else 0, 0, L.t['locale'])}</span></div>
        <div id="{sid}-kl" class="acc" style="font-size:{L.fs(0.034)}px;font-weight:700;opacity:0;">{E(v.get('keep_label', ''))}</div>
      </div>
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <g id="{sid}-field" fill="{L.ink}" opacity="0.55">{''.join(groups)}</g>
        {''.join(surv)}
      </svg>
      {f'<div id="{sid}-st" style="position:absolute;left:0;right:0;top:{row_y + L.px(0.06):.0f}px;text-align:center;opacity:0;"><span class="serif acc" style="font-size:{L.fs(0.12)}px;line-height:1;">{E(v["stat"]["text"])}</span><div class="muted" style="font-size:{L.fs(0.03)}px;margin-top:{L.px(0.01)}px;">{E(v["stat"].get("label", ""))}</div></div>' if v.get('stat') else ''}
    </div>"""
    tw = [_fade(f"#{sid}-l", 0.05)] + tw
    if not full:
        sweep = min(4.0, max(1.2, dur * 0.35))  # the field fills while the voice sets the scene
        t0 = cue(v.get("cue", ""), 0.4) if v.get("cue") else 0.4
        for row in range(rows):
            tw.append(_ft(f"#{sid}-r{row}", "opacity: 0", 'opacity: 1, duration: 0.35, ease: "power2.out"', t0 + sweep * row / rows))
        loc = L.t["locale"]
        tw += [f"const {sid}P = {{ v: 0 }};",
               f'tl.fromTo({sid}P, {{ v: 0 }}, {{ v: {counter_to}, duration: {sweep + 0.3:.2f}, ease: "power1.out", onUpdate: () => '
               f'{{ document.getElementById("{sid}-v").textContent = Math.round({sid}P.v).toLocaleString("{loc}"); }} }}, {t0:.3f});']
    if keep:
        tw.append(_ft(f"#{sid}-field", "opacity: 0.55", 'opacity: 0.08, duration: 0.8, ease: "power2.inOut"', t_keep, later=True))
        tw.append(_ft(f"#{sid}-n", "opacity: 1", 'opacity: 0, duration: 0.2, ease: "power2.in"', t_keep + 0.6, later=True))
        tw.append(_rise(f"#{sid}-kl", t_keep + 0.8, 0.5, 10))
        if v.get("stat"):
            tw.append(_blur_in(f"#{sid}-st", max(t_keep + 2.2, cue(v["stat"].get("cue", ""), t_keep + 2.4)), 0.4))
    return m, "", tw


# ---------------------------------------------------------------- ladder: a hierarchy with a lit top step

def ladder(L, sid, v, dur, cue):
    levels = v["levels"]  # bottom -> top
    n = len(levels)
    x0, base = L.w * 0.12, L.h * 0.86
    sh = L.px(0.085)
    wmin, wmax = L.w * 0.34, L.w * 0.62
    steps, tw = [], []
    head, htw = _head(L, sid, v)
    tw += htw
    build = min(2.4, dur * 0.3)
    for i, lab in enumerate(levels):
        w = wmax - (wmax - wmin) * i / max(1, n - 1)
        y = base - (i + 1) * (sh + L.px(0.012))
        top = i == n - 1
        steps.append(f'<div id="{sid}-s{i}" style="position:absolute;left:{x0:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{sh}px;'
                     f'border-radius:{L.px(0.012)}px;background:{"rgba(255,255,255,0.06)"};border:2px solid {L.muted}55;display:flex;align-items:center;'
                     f'padding-left:{L.px(0.025)}px;gap:{L.px(0.02)}px;transform-origin:0 50%;">'
                     f'<span class="serif" style="font-size:{L.fs(0.045)}px;color:{L.accent if top else L.muted};">{i + 1}</span>'
                     f'<span style="font-size:{L.fs(0.03)}px;color:{L.ink if top else L.muted};">{E(lab)}</span></div>')
        tw.append(_ft(f"#{sid}-s{i}", "opacity: 0, scaleX: 0.6", 'opacity: 1, scaleX: 1, duration: 0.45, ease: "expo.out"', 0.5 + build * i / n))
    t_top = cue(v.get("top_cue", ""), 0.6 + build)
    tw.append(_ft(f"#{sid}-s{n - 1}", "backgroundColor: \"rgba(255,255,255,0.06)\", borderColor: \"rgba(154,147,136,0.33)\"",
                  f'backgroundColor: "{L.accent}22", borderColor: "{L.accent}", duration: 0.5, ease: "power2.out"', t_top, later=True))
    tags = v.get("tags") or []
    ty = base - n * (sh + L.px(0.012)) + sh / 2
    tx = x0 + wmin + L.px(0.04)
    tag_m = ""
    for j, tg in enumerate(tags):
        tag_m += (f'<div id="{sid}-t{j}" style="position:absolute;left:{tx:.0f}px;top:{ty - L.px(0.03) + j * L.px(0.06) - (len(tags) - 1) * L.px(0.03):.0f}px;'
                  f'font-size:{L.fs(0.034)}px;font-weight:700;color:{L.accent};white-space:nowrap;">'
                  f'{"+ " if j else "← "}{E(tg["text"])}</div>')
        tw.append(_ft(f"#{sid}-t{j}", "opacity: 0, x: 40", 'opacity: 1, x: 0, duration: 0.5, ease: "power3.out"',
                      max(t_top + 0.3, cue(tg.get("cue", ""), t_top + 0.4 + 0.6 * j))))
    m = f'<div id="{sid}-c" style="position:absolute;inset:0;">{head}{"".join(steps)}{tag_m}</div>'
    return m, "", tw


# ---------------------------------------------------------------- venn: the intersection is the idea

def venn(L, sid, v, dur, cue):
    circles = v["circles"][:3]
    R = L.px(0.19)
    cx, cy = L.w * 0.5, L.h * 0.52
    d = R * 0.62
    centers = [(cx, cy - d), (cx - d * 0.95, cy + d * 0.55), (cx + d * 0.95, cy + d * 0.55)]
    lab_pos = [(cx, cy - d - R - L.px(0.035), "middle"), (cx - d * 0.95 - R * 0.55, cy + d * 0.55 + R + L.px(0.05), "middle"),
               (cx + d * 0.95 + R * 0.55, cy + d * 0.55 + R + L.px(0.05), "middle")]
    head, tw = _head(L, sid, v, 0.1)
    clips = "".join(f'<clipPath id="{sid}-cp{i}"><circle cx="{x:.1f}" cy="{y:.1f}" r="{R}"/></clipPath>' for i, (x, y) in enumerate(centers))
    rings = "".join(f'<circle id="{sid}-o{i}" cx="{x:.1f}" cy="{y:.1f}" r="{R}" fill="{L.ink}" fill-opacity="0.04" stroke="{L.ink}" '
                    f'stroke-opacity="0.75" stroke-width="3" opacity="0"/>' for i, (x, y) in enumerate(centers))
    labels = "".join(f'<text id="{sid}-lb{i}" x="{x:.1f}" y="{y:.1f}" text-anchor="{a}" fill="{L.ink}" font-family="Inter" font-weight="700" '
                     f'font-size="{L.fs(0.03)}" opacity="0">{E(c["label"])}</text>' for i, ((x, y, a), c) in enumerate(zip(lab_pos, circles)))
    x2, y2 = centers[2]
    core = (f'<g clip-path="url(#{sid}-cp0)"><g clip-path="url(#{sid}-cp1)"><circle id="{sid}-core" cx="{x2:.1f}" cy="{y2:.1f}" r="{R}" '
            f'fill="{L.accent}" opacity="0"/></g></g>')
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible"><defs>{clips}</defs>
        {rings}{core}{labels}
        <line id="{sid}-ll" x1="{cx:.1f}" y1="{cy + d * 0.2:.1f}" x2="{cx:.1f}" y2="{cy + d * 0.55 + R + L.px(0.07):.1f}" stroke="{L.accent}"
          stroke-width="2" stroke-dasharray="{R:.0f}" stroke-dashoffset="{R:.0f}"/>
        <text id="{sid}-cl" x="{cx:.1f}" y="{cy + d * 0.55 + R + L.px(0.12):.1f}" text-anchor="middle" fill="{L.accent}" font-family="EB Garamond"
          font-weight="600" font-size="{L.fs(0.055)}" opacity="0">{E(v.get('center_label', ''))}</text>
      </svg></div>"""
    for i, c in enumerate(circles):
        at = max(0.4 + 0.3 * i, cue(c.get("cue", ""), 0.8 + 1.2 * i))
        x, y = centers[i]
        tw.append(_ft(f"#{sid}-o{i}", f"opacity: 0, attr: {{r: {R * 0.7:.0f}}}", f'opacity: 1, attr: {{r: {R}}}, duration: 0.7, ease: "expo.out"', at))
        tw.append(_fade(f"#{sid}-lb{i}", at + 0.2, 0.4))
    t_core = cue(v.get("center_cue", ""), dur * 0.7)
    tw.append(_ft(f"#{sid}-core", "opacity: 0", 'opacity: 0.95, duration: 0.6, ease: "power2.out"', t_core))
    tw.append(_ft(f"#{sid}-ll", f"strokeDashoffset: {R:.0f}", 'strokeDashoffset: 0, duration: 0.4, ease: "power2.out"', t_core + 0.3))
    tw.append(_blur_in(f"#{sid}-cl", t_core + 0.55, 0.4))
    return m, "", tw


# ---------------------------------------------------------------- flywheel: turn by turn until it runs itself

def flywheel(L, sid, v, dur, cue):
    R = L.px(0.24)
    cx, cy = L.w * 0.34, L.h * 0.56
    spokes = int(v.get("spokes", 8))
    a0, a1 = float(v.get("from_angle", 0)), float(v.get("to_angle", 360))
    ease = v.get("ease", "power2.in")
    head, tw = _head(L, sid, v, 0.1)
    sp = "".join(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + R * 0.86 * math.cos(2 * math.pi * k / spokes):.1f}" '
                 f'y2="{cy + R * 0.86 * math.sin(2 * math.pi * k / spokes):.1f}" stroke="{L.ink}" stroke-opacity="0.55" stroke-width="{L.px(0.012)}" stroke-linecap="round"/>'
                 for k in range(spokes))
    bolts = "".join(f'<circle cx="{cx + R * 0.93 * math.cos(2 * math.pi * (k + 0.5) / spokes):.1f}" cy="{cy + R * 0.93 * math.sin(2 * math.pi * (k + 0.5) / spokes):.1f}" '
                    f'r="{L.px(0.008)}" fill="{L.accent}"/>' for k in range(spokes))
    # speed lines: arcs just outside the rim, fading in as the wheel finds its momentum
    arcs = []
    for k in range(3):
        rr = R + L.px(0.04) + k * L.px(0.025)
        s, e = math.radians(200 + k * 25), math.radians(290 + k * 25)
        arcs.append(f'<path d="M {cx + rr * math.cos(s):.1f} {cy + rr * math.sin(s):.1f} A {rr:.1f} {rr:.1f} 0 0 1 '
                    f'{cx + rr * math.cos(e):.1f} {cy + rr * math.sin(e):.1f}" fill="none" stroke="{L.accent}" stroke-width="{max(3, L.px(0.005))}" '
                    f'stroke-linecap="round" stroke-opacity="{0.8 - 0.2 * k:.2f}"/>')
    tx = L.w * 0.62
    right = ""
    if v.get("name"):
        right += (f'<div id="{sid}-nm" class="serif" style="font-size:{L.fs(0.07)}px;line-height:1.08;">{E(v["name"])}</div>')
    if v.get("line"):
        right += f'<div id="{sid}-ln" class="muted" style="font-size:{L.fs(0.032)}px;line-height:1.4;margin-top:{L.px(0.02)}px;">{E(v["line"])}</div>'
    marks = v.get("marks") or []  # [{"text": "vòng 1", "cue": "..."}]
    mk = "".join(f'<div id="{sid}-m{i}" style="font-size:{L.fs(0.034)}px;font-weight:700;margin-top:{L.px(0.018)}px;color:{L.accent if i == len(marks) - 1 else L.ink};">{E(x["text"])}</div>'
                 for i, x in enumerate(marks))
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R * 1.02:.1f}" fill="{L.accent}" fill-opacity="0.05"/>
        <g id="{sid}-sp" opacity="0">{''.join(arcs)}</g>
        <g id="{sid}-wh">
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" fill="none" stroke="{L.ink}" stroke-width="{L.px(0.03)}"/>
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R * 0.9:.1f}" fill="none" stroke="{L.ink}" stroke-opacity="0.3" stroke-width="2"/>
          {sp}{bolts}
          <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{L.px(0.05)}" fill="{L.bg}" stroke="{L.accent}" stroke-width="{L.px(0.008)}"/>
          <circle cx="{cx:.1f}" cy="{cy - R:.1f}" r="{L.px(0.014)}" fill="{L.accent}"/>
        </g>
        <path id="{sid}-ar" d="M {cx + R * 0.15:.1f} {cy - R - L.px(0.07):.1f} l {L.px(0.11)} 0 m -{L.px(0.03)} -{L.px(0.022)} l {L.px(0.03)} {L.px(0.022)} l -{L.px(0.03)} {L.px(0.022)}"
          fill="none" stroke="{L.accent}" stroke-width="{max(4, L.px(0.007))}" stroke-linecap="round" stroke-linejoin="round" opacity="0"/>
      </svg>
      <div style="position:absolute;left:{tx:.0f}px;right:{L.px(0.08)}px;top:{L.h * 0.38:.0f}px;">{right}<div style="margin-top:{L.px(0.03)}px">{mk}</div></div>
    </div>"""
    tw += [_ft(f"#{sid}-wh", f'rotation: {a0}, svgOrigin: "{cx:.1f} {cy:.1f}"',
               f'rotation: {a1}, svgOrigin: "{cx:.1f} {cy:.1f}", duration: {dur - 0.1:.2f}, ease: "{ease}"', 0)]
    if v.get("enter", True):
        tw.insert(0, _ft(f"#{sid}-wh", "opacity: 0", 'opacity: 1, duration: 0.6, ease: "power2.out"', 0.1))
    for i, pc in enumerate(v.get("push_cues", [])):  # a push: the arrow strikes along the rim's tangent
        at = cue(pc, 0.6 + 1.2 * i)
        tw.append(_ft(f"#{sid}-ar", "opacity: 0, x: -30", 'opacity: 1, x: 0, duration: 0.25, ease: "power3.out"', at, later=i > 0))
        tw.append(_ft(f"#{sid}-ar", "opacity: 1, x: 0", 'opacity: 0, x: 24, duration: 0.3, ease: "power2.in"', at + 0.45, later=True))
    if v.get("fast_cue") is not None:
        tf = cue(v["fast_cue"], dur * 0.6)
        tw.append(_ft(f"#{sid}-sp", "opacity: 0", 'opacity: 1, duration: 0.8, ease: "power2.out"', tf))
    if v.get("name"):
        tw.append(_blur_in(f"#{sid}-nm", 0.4, 0.45))
    if v.get("line"):
        tw.append(_blur_in(f"#{sid}-ln", max(0.9, cue(v.get("line_cue", ""), 1.0)), 0.4))
    for i, x in enumerate(marks):
        tw.append(_rise(f"#{sid}-m{i}", max(0.6, cue(x.get("cue", ""), 1.0 + i)), 0.45, 12))
    return m, "", tw


# ---------------------------------------------------------------- halo: the glow that was in the eye of the beholder

def halo(L, sid, v, dur, cue):
    items = v["items"][:3]
    n = len(items)
    cw, chh = L.w * 0.3, L.px(0.2)
    gapx = L.w * 0.06
    x0 = (L.w - (n * cw + (n - 1) * gapx)) / 2
    y = L.h * 0.42
    head, tw = _head(L, sid, v, 0.1)
    cards = ""
    for i, it in enumerate(items):
        x = x0 + i * (cw + gapx)
        cards += f"""<div id="{sid}-cd{i}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{cw:.0f}px;height:{chh}px;">
          <svg width="{cw:.0f}" height="{L.px(0.1)}" style="position:absolute;left:0;top:-{L.px(0.09)}px;overflow:visible">
            <ellipse id="{sid}-hl{i}" cx="{cw / 2:.0f}" cy="{L.px(0.05)}" rx="{cw * 0.32:.0f}" ry="{L.px(0.022)}" fill="none" stroke="{L.accent}"
              stroke-width="{max(4, L.px(0.007))}" style="filter: drop-shadow(0 0 {L.px(0.012)}px {L.accent});"/></svg>
          <div id="{sid}-bx{i}" style="position:absolute;inset:0;border:2px solid {L.muted}66;border-radius:{L.px(0.016)}px;background:rgba(255,255,255,0.04);
            display:flex;flex-direction:column;align-items:center;justify-content:center;gap:{L.px(0.012)}px;">
            <div class="serif" style="font-size:{L.fs(0.05)}px;">{E(it['name'])}</div>
            <div id="{sid}-bf{i}" class="acc" style="font-size:{L.fs(0.028)}px;font-weight:700;">{E(it.get('before', ''))}</div></div>
          <div id="{sid}-sm{i}" style="position:absolute;left:50%;top:{chh + L.px(0.03)}px;transform-origin:50% 50%;white-space:nowrap;opacity:0;
            padding:{L.px(0.008)}px {L.px(0.02)}px;border:3px solid #D8664B;color:#E77A5F;font-weight:800;letter-spacing:0.08em;font-size:{L.fs(0.028)}px;">{E(it.get('after', ''))}</div>
        </div>"""
        tw.append(_ft(f"#{sid}-cd{i}", "opacity: 0, y: 30", 'opacity: 1, y: 0, duration: 0.6, ease: "expo.out"', 0.4 + 0.25 * i))
        tw.append(_ft(f"#{sid}-hl{i}", "opacity: 0", 'opacity: 1, duration: 0.6, ease: "power2.out"', 0.8 + 0.25 * i))
        at = max(1.6, cue(it.get("cue", ""), dur * 0.35 + i))
        # the halo flickers and dies, the card sinks a little, the verdict stamps over it
        tw.append(_ft(f"#{sid}-hl{i}", "opacity: 1", 'opacity: 0.2, duration: 0.06, ease: "none"', at, later=True))
        tw.append(_ft(f"#{sid}-hl{i}", "opacity: 0.2", 'opacity: 0.8, duration: 0.06, ease: "none"', at + 0.09, later=True))
        tw.append(_ft(f"#{sid}-hl{i}", "opacity: 0.8, y: 0", 'opacity: 0, y: 26, duration: 0.45, ease: "power3.in"', at + 0.18, later=True))
        tw.append(_ft(f"#{sid}-bx{i}", "opacity: 1, y: 0", 'opacity: 0.55, y: 14, duration: 0.5, ease: "power2.inOut"', at + 0.3, later=True))
        tw.append(_ft(f"#{sid}-bf{i}", "opacity: 1", 'opacity: 0.25, duration: 0.3, ease: "power2.out"', at + 0.3, later=True))
        tw.append(_ft(f"#{sid}-sm{i}", 'opacity: 0, scale: 1.6, rotation: -8, xPercent: -50',
                      'opacity: 1, scale: 1, rotation: -5, xPercent: -50, duration: 0.3, ease: "expo.out"', at + 0.55))
    lab = ""
    if v.get("label"):
        lab = (f'<div id="{sid}-lab" style="position:absolute;left:0;right:0;top:{L.h * 0.8:.0f}px;text-align:center;">'
               f'<span class="serif" style="font-size:{L.fs(0.06)}px;">{E(v["label"])}</span></div>')
        tw.append(_blur_in(f"#{sid}-lab", max(2.5, cue(v.get("label_cue", ""), dur * 0.7)), 0.45))
    m = f'<div id="{sid}-c" style="position:absolute;inset:0;">{head}{cards}{lab}</div>'
    return m, "", tw


# ---------------------------------------------------------------- swap: let one thing go so another can take its place

ICONS = {
    "factory": lambda s, c: (f'<path d="M0 {s} L0 {s * .45} L{s * .25} {s * .62} L{s * .25} {s * .45} L{s * .5} {s * .62} L{s * .5} {s * .45} '
                             f'L{s * .75} {s * .62} L{s * .75} {s * .1} L{s * .9} {s * .1} L{s * .9} {s} Z" fill="none" stroke="{c}" stroke-width="{s * .04:.1f}" '
                             f'stroke-linejoin="round"/><rect x="{s * .1}" y="{s * .75}" width="{s * .12}" height="{s * .12}" fill="{c}"/>'
                             f'<rect x="{s * .35}" y="{s * .75}" width="{s * .12}" height="{s * .12}" fill="{c}"/>'
                             f'<rect x="{s * .6}" y="{s * .75}" width="{s * .12}" height="{s * .12}" fill="{c}"/>'),
    "tissue": lambda s, c: (f'<path d="M{s * .3} {s * .5} L{s * .24} {s * .2} Q{s * .37} {s * .1} {s * .5} {s * .2} Q{s * .63} {s * .3} {s * .76} {s * .18} '
                            f'L{s * .7} {s * .5} Z" fill="{c}" fill-opacity="0.18" stroke="{c}" stroke-width="{s * .03:.1f}" stroke-linejoin="round"/>'
                            f'<path d="M{s * .02} {s * .5} L{s * .98} {s * .5} L{s * .9} {s * .95} L{s * .1} {s * .95} Z" fill="none" stroke="{c}" '
                            f'stroke-width="{s * .04:.1f}" stroke-linejoin="round"/>'
                            f'<rect x="{s * .3}" y="{s * .47}" width="{s * .4}" height="{s * .07}" rx="{s * .035}" fill="{c}"/>'),
}


def swap(L, sid, v, dur, cue):
    s = L.px(0.24)
    y = L.h * 0.36
    xa, xb = L.w * 0.18, L.w * 0.82 - s
    a, b = v["from"], v["to"]
    head, tw = _head(L, sid, v, 0.12)
    ia = ICONS.get(a.get("icon", ""), lambda s, c: "")(s, L.ink)
    ib = ICONS.get(b.get("icon", ""), lambda s, c: "")(s, L.accent)
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <div id="{sid}-a" style="position:absolute;left:{xa:.0f}px;top:{y:.0f}px;width:{s}px;text-align:center;">
        <svg width="{s}" height="{s}" style="overflow:visible">{ia}
          <line id="{sid}-x" x1="-10" y1="{s + 10}" x2="{s + 10}" y2="-10" stroke="#E77A5F" stroke-width="{L.px(0.012)}" stroke-linecap="round"
            stroke-dasharray="{s * 1.6:.0f}" stroke-dashoffset="{s * 1.6:.0f}"/></svg>
        <div style="font-size:{L.fs(0.032)}px;margin:{L.px(0.02)}px -{s * 0.4:.0f}px 0;font-weight:700;">{E(a['label'])}</div></div>
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <path id="{sid}-arw" d="M {xa + s + L.px(0.05):.0f} {y + s / 2:.0f} L {xb - L.px(0.05):.0f} {y + s / 2:.0f} m -{L.px(0.03)} -{L.px(0.025)} l {L.px(0.03)} {L.px(0.025)} l -{L.px(0.03)} {L.px(0.025)}"
          fill="none" stroke="{L.muted}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{L.w:.0f}" stroke-dashoffset="{L.w:.0f}"/></svg>
      <div id="{sid}-b" style="position:absolute;left:{xb:.0f}px;top:{y:.0f}px;width:{s}px;text-align:center;">
        <svg width="{s}" height="{s}" style="overflow:visible">{ib}</svg>
        <div class="acc" style="font-size:{L.fs(0.032)}px;margin:{L.px(0.02)}px -{s * 0.4:.0f}px 0;font-weight:700;white-space:nowrap;">{E(b['label'])}</div></div>
      {f'<div id="{sid}-ln" class="serif" style="position:absolute;left:0;right:0;top:{L.h * 0.76:.0f}px;text-align:center;font-size:{L.fs(0.06)}px;">{E(v["line"])}</div>' if v.get('line') else ''}
    </div>"""
    tw.append(_ft(f"#{sid}-a", "opacity: 0, y: 20", 'opacity: 1, y: 0, duration: 0.6, ease: "expo.out"', 0.3))
    t = cue(v.get("cue", ""), dur * 0.35)
    tw.append(_ft(f"#{sid}-x", f"strokeDashoffset: {s * 1.6:.0f}", 'strokeDashoffset: 0, duration: 0.35, ease: "power3.out"', t))
    tw.append(_ft(f"#{sid}-a", "opacity: 1, y: 0, rotation: 0", 'opacity: 0.35, y: 40, rotation: -6, duration: 0.9, ease: "power3.in"',
                  max(t + 0.45, 0.3 + 0.6 + 0.5 + 0.3 * len(a["label"].split())), later=True))
    tw.append(_ft(f"#{sid}-arw", f"strokeDashoffset: {L.w:.0f}", 'strokeDashoffset: 0, duration: 0.7, ease: "power2.inOut"', t + 0.6))
    tb = max(t + 1.1, cue(b.get("cue", ""), t + 1.2))
    tw.append(_ft(f"#{sid}-b", "opacity: 0, scale: 0.7", 'opacity: 1, scale: 1, duration: 0.6, ease: "back.out(1.6)"', tb))
    if v.get("line"):
        tw.append(_blur_in(f"#{sid}-ln", max(0.5, cue(v.get("line_cue", ""), tb + 0.8)), 0.45))
    return m, "", tw


ICONS["diaper"] = lambda s, c: (
    f'<path d="M{s * .06} {s * .3} L{s * .94} {s * .3} L{s * .9} {s * .5} C{s * .78} {s * .55} {s * .66} {s * .7} {s * .62} {s * .92} '
    f'L{s * .38} {s * .92} C{s * .34} {s * .7} {s * .22} {s * .55} {s * .1} {s * .5} Z" fill="{c}" fill-opacity="0.15" stroke="{c}" '
    f'stroke-width="{s * .035:.1f}" stroke-linejoin="round"/>'
    f'<rect x="{s * .08}" y="{s * .3}" width="{s * .14}" height="{s * .1}" rx="{s * .02}" fill="{c}"/>'
    f'<rect x="{s * .78}" y="{s * .3}" width="{s * .14}" height="{s * .1}" rx="{s * .02}" fill="{c}"/>')
ICONS["roll"] = lambda s, c: (
    f'<rect x="{s * .22}" y="{s * .2}" width="{s * .56}" height="{s * .7}" rx="{s * .04}" fill="{c}" fill-opacity="0.12" stroke="{c}" stroke-width="{s * .035:.1f}"/>'
    f'<ellipse cx="{s * .5}" cy="{s * .2}" rx="{s * .28}" ry="{s * .08}" fill="none" stroke="{c}" stroke-width="{s * .035:.1f}"/>'
    f'<ellipse cx="{s * .5}" cy="{s * .2}" rx="{s * .08}" ry="{s * .025}" fill="{c}"/>')


def _mill_art(L, sid, x, y, w, h) -> tuple[str, list[str]]:
    """A paper mill by a river, drawn in line: brick hall with a sawtooth roof, two stacks breathing smoke, logs
    waiting at the door and a finished roll of paper. Built in three strokes (ground, building, details)."""
    ink, acc = L.ink, L.accent
    sw = max(3, L.px(0.005))
    gy = y + h * 0.78  # ground line
    bx, bw, bh = x + w * 0.12, w * 0.56, h * 0.42
    by = gy - bh
    teeth = 4
    tw_ = bw / teeth
    roof = " ".join(f"L{bx + tw_ * k:.0f} {by - h * 0.1:.0f} L{bx + tw_ * (k + 1):.0f} {by:.0f}" for k in range(teeth))
    bricks = "".join(f'<line x1="{bx:.0f}" y1="{by + bh * f:.0f}" x2="{bx + bw:.0f}" y2="{by + bh * f:.0f}" stroke="{ink}" stroke-opacity="0.12" stroke-width="2"/>'
                     for f in (0.25, 0.5, 0.75))
    wins = "".join(f'<rect x="{bx + bw * (0.1 + 0.22 * k):.0f}" y="{by + bh * 0.3:.0f}" width="{bw * 0.12:.0f}" height="{bh * 0.22:.0f}" rx="4" '
                   f'fill="{acc}" fill-opacity="0.55"/>' for k in range(4))
    stacks, smoke, tw = "", "", []
    for k, sx in enumerate((bx + bw * 0.78, bx + bw * 0.92)):
        sh = h * (0.36 if k == 0 else 0.3)
        stacks += f'<rect x="{sx - w * 0.025:.0f}" y="{by - sh:.0f}" width="{w * 0.05:.0f}" height="{sh:.0f}" fill="{L.bg}" stroke="{ink}" stroke-width="{sw}"/>'
        for j in range(3):  # puffs rise, swell and fade on their own clocks: the mill is working
            pid = f"{sid}-pf{k}{j}"
            smoke += f'<circle id="{pid}" cx="{sx:.0f}" cy="{by - sh - L.px(0.02):.0f}" r="{L.px(0.022)}" fill="{ink}" opacity="0"/>'
            t0 = 0.6 + j * 1.3 + k * 0.5
            for rep in range(4):
                at = t0 + rep * 3.9
                tw.append(_ft(f"#{pid}", "opacity: 0.35, x: 0, y: 0, scale: 0.6", f'opacity: 0, x: {L.px(0.05)}, y: -{L.px(0.16)}, scale: 1.8, '
                              f'duration: 3.6, ease: "sine.out"', at, later=rep > 0))
    door = f'<rect x="{bx + bw * 0.42:.0f}" y="{gy - bh * 0.38:.0f}" width="{bw * 0.16:.0f}" height="{bh * 0.38:.0f}" fill="{ink}" fill-opacity="0.15" stroke="{ink}" stroke-width="{sw}"/>'
    # a log pile: three on the ground, two resting on top
    pile = [(0.05 + 0.045 * k, 0.02) for k in range(3)] + [(0.0725, 0.055), (0.1175, 0.055)]
    logs = "".join(f'<circle cx="{x + w * fx:.0f}" cy="{gy - L.px(fy):.0f}" r="{L.px(0.02)}" fill="none" stroke="{ink}" stroke-opacity="0.7" '
                   f'stroke-width="{sw}"/>' for fx, fy in pile)
    rx_ = bx + bw + w * 0.12
    roll = (f'<rect x="{rx_ - L.px(0.045):.0f}" y="{gy - L.px(0.11):.0f}" width="{L.px(0.09)}" height="{L.px(0.11)}" fill="{acc}" fill-opacity="0.2" stroke="{acc}" stroke-width="{sw}"/>'
            f'<ellipse cx="{rx_:.0f}" cy="{gy - L.px(0.11):.0f}" rx="{L.px(0.045)}" ry="{L.px(0.016)}" fill="{L.bg}" stroke="{acc}" stroke-width="{sw}"/>'
            f'<ellipse cx="{rx_:.0f}" cy="{gy - L.px(0.11):.0f}" rx="{L.px(0.012)}" ry="{L.px(0.005)}" fill="{acc}"/>')
    river = "".join(f'<path d="M{x:.0f} {gy + h * (0.08 + 0.06 * k):.0f} q {w * 0.06:.0f} -{L.px(0.012)} {w * 0.12:.0f} 0 t {w * 0.12:.0f} 0 t {w * 0.12:.0f} 0 '
                    f't {w * 0.12:.0f} 0 t {w * 0.12:.0f} 0 t {w * 0.12:.0f} 0 t {w * 0.12:.0f} 0 t {w * 0.12:.0f} 0" fill="none" stroke="{acc}" '
                    f'stroke-opacity="{0.45 - 0.12 * k:.2f}" stroke-width="2"/>' for k in range(3))
    m = f"""<g id="{sid}-g0" opacity="0"><line x1="{x:.0f}" y1="{gy:.0f}" x2="{x + w:.0f}" y2="{gy:.0f}" stroke="{ink}" stroke-opacity="0.5" stroke-width="{sw}"/>{river}</g>
      <g id="{sid}-g1" opacity="0">{stacks}<path d="M{bx:.0f} {gy:.0f} L{bx:.0f} {by:.0f} {roof} L{bx + bw:.0f} {gy:.0f}" fill="{ink}" fill-opacity="0.05"
        stroke="{ink}" stroke-width="{sw}" stroke-linejoin="round"/>{bricks}{door}</g>
      <g id="{sid}-g2" opacity="0">{wins}{logs}{roll}</g>{smoke}"""
    tw = [_ft(f"#{sid}-g0", "opacity: 0", 'opacity: 1, duration: 0.5, ease: "power2.out"', 0.1),
          _ft(f"#{sid}-g1", "opacity: 0, y: 30", 'opacity: 1, y: 0, duration: 0.8, ease: "expo.out"', 0.3),
          _ft(f"#{sid}-g2", "opacity: 0", 'opacity: 1, duration: 0.6, ease: "power2.out"', 0.9)] + tw
    return m, tw


ART = {"mill": _mill_art}


def company(L, sid, v, dur, cue):
    """Who the company is, as a picture: its world drawn on the left, its facts landing on their words, and the
    turning point arriving as a newspaper clipping."""
    aw, ah = L.w * 0.56, L.h * 0.56
    ax, ay = L.w * 0.04, L.h * 0.3
    art_m, tw = ART.get(v.get("art", "mill"), _mill_art)(L, sid, ax, ay, aw, ah)
    head, htw = _head(L, sid, v, 0.1)
    tw += htw
    rx = L.w * 0.62
    facts = ""
    for i, f in enumerate(v.get("facts", [])):
        facts += (f'<div id="{sid}-f{i}" style="display:flex;gap:{L.px(0.015)}px;align-items:baseline;margin-top:{L.px(0.02)}px;">'
                  f'<span class="serif acc" style="font-size:{L.fs(0.045)}px;min-width:{L.px(0.17)}px;white-space:nowrap;">{E(f.get("big", ""))}</span>'
                  f'<span style="font-size:{L.fs(0.027)}px;line-height:1.3;">{E(f["text"])}</span></div>')
        tw.append(_rise(f"#{sid}-f{i}", max(0.8, cue(f.get("cue", ""), 1.2 + i)), 0.5, 14))
    card = ""
    c = v.get("card")
    if c:
        card = f"""<div id="{sid}-cd" style="position:absolute;left:{rx - L.px(0.02):.0f}px;right:{L.px(0.05)}px;top:{L.h * 0.62:.0f}px;
          background:#EDE4D3;color:#1A1712;padding:{L.px(0.025)}px {L.px(0.03)}px;border-radius:4px;box-shadow:0 {L.px(0.012)}px {L.px(0.04)}px rgba(0,0,0,0.5);">
          <div style="font-size:{L.fs(0.02)}px;letter-spacing:0.25em;font-weight:800;border-bottom:2px solid #1A1712;padding-bottom:{L.px(0.008)}px;">{E(c.get('kicker', ''))}</div>
          <div class="serif" style="font-size:{L.fs(0.05)}px;line-height:1.08;margin-top:{L.px(0.012)}px;">{E(c['title'])}</div>
          <div style="font-size:{L.fs(0.026)}px;margin-top:{L.px(0.008)}px;opacity:0.75;">{E(c.get('sub', ''))}</div></div>"""
        tw.append(_ft(f"#{sid}-cd", "opacity: 0, y: 40, rotation: 6", 'opacity: 1, y: 0, rotation: -2, duration: 0.7, ease: "back.out(1.4)"',
                      max(1.5, cue(c.get("cue", ""), dur * 0.6))))
    name = (f'<div id="{sid}-nm" class="serif" style="font-size:{L.fs(0.06)}px;line-height:1;white-space:nowrap;">{E(v["name"])}</div>'
            if v.get("name") else "")
    if name:
        tw.append(_blur_in(f"#{sid}-nm", 0.4, 0.5))
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">{art_m}</svg>
      <div style="position:absolute;left:{rx:.0f}px;right:{L.px(0.04)}px;top:{L.h * 0.22:.0f}px;">{name}{facts}</div>{card}</div>"""
    return m, "", tw


def rise(L, sid, v, dur, cue):
    """Why it won, as a picture: the doubters' stamp, the climb against a flat market, the rivals it passed, and
    the products that carried it."""
    head, tw = _head(L, sid, v, 0.1)
    # left: the climb, ratio to the market (market = flat 1x line)
    cx0, cx1, cy0, cy1 = L.w * 0.07, L.w * 0.52, L.h * 0.36, L.h * 0.68
    top = float(v.get("value", 4.0))
    yv = lambda r: cy1 - (cy1 - cy0) * (r - 0.5) / (top - 0.5)  # noqa: E731
    n = 12
    pts = [(cx0 + (cx1 - cx0) * i / (n - 1), yv(1 + (top - 1) * (i / (n - 1)) ** 1.8)) for i in range(n)]
    path = "M " + " L ".join(f"{x:.0f} {y:.0f}" for x, y in pts)
    ln = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(n - 1)) + 10
    t_line = max(0.8, cue(v.get("cue", ""), dur * 0.35))
    stamp = v.get("stamp")
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <line x1="{cx0:.0f}" y1="{yv(1):.0f}" x2="{cx1:.0f}" y2="{yv(1):.0f}" stroke="{L.muted}" stroke-width="2" stroke-dasharray="8 8"/>
        <text x="{cx1:.0f}" y="{yv(1) + L.px(0.035):.0f}" text-anchor="end" fill="{L.muted}" font-family="Inter" font-size="{L.fs(0.022)}">{E(v.get('base_label', 'thị trường = 1×'))}</text>
        <path id="{sid}-ln" d="{path}" fill="none" stroke="{L.accent}" stroke-width="{max(5, L.px(0.008))}" stroke-linecap="round" stroke-linejoin="round"
          stroke-dasharray="{ln:.0f}" stroke-dashoffset="{ln:.0f}"/>
        <text id="{sid}-v" x="{cx1 - L.px(0.02):.0f}" y="{pts[-1][1] - L.px(0.07):.0f}" text-anchor="end" fill="{L.accent}" font-family="EB Garamond" font-size="{L.fs(0.11)}" opacity="0">{E(v.get('value_text', ''))}</text>
        <text id="{sid}-vl" x="{cx1 - L.px(0.02):.0f}" y="{pts[-1][1] - L.px(0.035):.0f}" text-anchor="end" fill="{L.ink}" font-family="Inter" font-size="{L.fs(0.022)}" opacity="0">{E(v.get('value_label', ''))}</text>
      </svg>
      {f'<div id="{sid}-st" style="position:absolute;left:{cx0 + L.px(0.01):.0f}px;top:{L.h * 0.47:.0f}px;padding:{L.px(0.008)}px {L.px(0.02)}px;border:3px solid #D8664B;color:#E77A5F;font-weight:800;letter-spacing:0.08em;font-size:{L.fs(0.026)}px;opacity:0;">{E(stamp["text"])}</div>' if stamp else ''}
    """
    tw.append(_ft(f"#{sid}-ln", f"strokeDashoffset: {ln:.0f}", f'strokeDashoffset: 0, duration: {min(2.6, dur * 0.3):.2f}, ease: "power2.in"', t_line))
    tw.append(_blur_in(f"#{sid}-v", t_line + min(2.6, dur * 0.3) - 0.2, 0.4))
    tw.append(_fade(f"#{sid}-vl", t_line + min(2.6, dur * 0.3) + 0.1, 0.4))
    if stamp:
        ts = max(0.4, cue(stamp.get("cue", ""), 0.6))
        tw.append(_ft(f"#{sid}-st", "opacity: 0, scale: 1.6, rotation: -10", 'opacity: 1, scale: 1, rotation: -6, duration: 0.3, ease: "expo.out"', ts))
        # proven wrong by the climb: the doubters' verdict leaves the frame
        tw.append(_ft(f"#{sid}-st", 'opacity: 1, filter: "blur(0px)"', 'opacity: 0, filter: "blur(6px)", duration: 0.6, ease: "power2.in"',
                      t_line + 0.6, later=True))
    # right: the ranking it climbed
    rk = v.get("ranking") or []
    rx, rw, rh = L.w * 0.6, L.w * 0.33, L.px(0.075)
    ry0 = L.h * 0.3
    hero = next((i for i, r in enumerate(rk) if r.get("hero")), len(rk) - 1)
    rows = ""
    for i, r in enumerate(rk):
        is_h = i == hero
        rows += (f'<div id="{sid}-r{i}" style="position:absolute;left:{rx:.0f}px;top:{ry0 + i * (rh + L.px(0.015)):.0f}px;width:{rw:.0f}px;height:{rh}px;'
                 f'border-radius:{L.px(0.012)}px;display:flex;align-items:center;padding-left:{L.px(0.025)}px;font-size:{L.fs(0.03)}px;'
                 f'font-weight:{800 if is_h else 500};color:{"#14110D" if is_h else L.muted};background:{L.accent if is_h else "rgba(255,255,255,0.05)"};'
                 f'border:2px solid {L.accent if is_h else L.muted + "44"};">{E(r["name"])}</div>')
        tw.append(_ft(f"#{sid}-r{i}", "opacity: 0, x: 30", 'opacity: 1, x: 0, duration: 0.5, ease: "expo.out"', 0.5 + 0.15 * i))
    if rk:
        t_pass = max(1.5, cue(v.get("pass_cue", ""), dur * 0.75))
        step = rh + L.px(0.015)
        tw.append(_ft(f"#{sid}-r{hero}", "y: 0", f'y: {-hero * step:.0f}, duration: 0.9, ease: "power3.inOut"', t_pass, later=True))
        for i in range(hero):
            tw.append(_ft(f"#{sid}-r{i}", "y: 0", f'y: {step:.0f}, duration: 0.9, ease: "power3.inOut"', t_pass, later=True))
    # bottom: the products that carried it, on a shelf
    prods = v.get("products") or []
    ps = L.px(0.09)
    gap = L.px(0.08)
    shelf_y = L.h * 0.84
    px0 = L.w * 0.6
    shelf = f'<div style="position:absolute;left:{px0 - L.px(0.02):.0f}px;width:{L.w * 0.35:.0f}px;top:{shelf_y:.0f}px;height:3px;background:{L.muted};opacity:0.5;"></div>'
    for i, pr in enumerate(prods):
        x = px0 + i * (ps + gap)
        shelf += (f'<div id="{sid}-p{i}" style="position:absolute;left:{x:.0f}px;top:{shelf_y - ps - L.px(0.005):.0f}px;width:{ps}px;text-align:center;">'
                  f'<svg width="{ps}" height="{ps}" style="overflow:visible">{ICONS.get(pr.get("icon", ""), lambda s, c: "")(ps, L.accent)}</svg>'
                  f'<div style="position:absolute;top:{ps + L.px(0.015)}px;left:-{gap / 2 - 4:.0f}px;right:-{gap / 2 - 4:.0f}px;font-size:{L.fs(0.02)}px;'
                  f'line-height:1.25;color:{L.ink};">{E(pr["label"])}</div></div>')
        tw.append(_ft(f"#{sid}-p{i}", "opacity: 0, y: 24", 'opacity: 1, y: 0, duration: 0.5, ease: "back.out(1.6)"',
                      max(1.0, cue(pr.get("cue", ""), dur * 0.45 + 0.4 * i))))
    why = ""
    if v.get("why"):
        why = (f'<div id="{sid}-wy" style="position:absolute;left:{cx0:.0f}px;width:{L.w * 0.47:.0f}px;top:{L.h * 0.76:.0f}px;">'
               f'<div class="kicker">{E(v.get("why_kicker", ""))}</div>'
               f'<div class="serif" style="font-size:{L.fs(0.042)}px;line-height:1.2;margin-top:{L.px(0.012)}px;">{E(v["why"])}</div></div>')
        tw.append(_blur_in(f"#{sid}-wy", max(1.5, cue(v.get("why_cue", ""), dur * 0.82)), 0.45))
    m += shelf + "".join([rows, why]) + "</div>"
    return m, "", tw


def _st(s, c, k=.035):
    return f'fill="none" stroke="{c}" stroke-width="{s * k:.1f}" stroke-linecap="round" stroke-linejoin="round"'


ICONS.update({
    "bulb": lambda s, c: (f'<path d="M{s * .34} {s * .62} C{s * .1} {s * .45} {s * .18} {s * .08} {s * .5} {s * .08} C{s * .82} {s * .08} {s * .9} {s * .45} '
                          f'{s * .66} {s * .62} L{s * .64} {s * .74} L{s * .36} {s * .74} Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                          f'<path d="M{s * .38} {s * .84} L{s * .62} {s * .84} M{s * .42} {s * .93} L{s * .58} {s * .93}" {_st(s, c)}/>'),
    "star": lambda s, c: ('<path d="' + " ".join(
        f'{"M" if k == 0 else "L"}{s * (.5 + (.42 if k % 2 == 0 else .18) * math.sin(math.pi * k / 5)):.1f} '
        f'{s * (.52 - (.42 if k % 2 == 0 else .18) * math.cos(math.pi * k / 5)):.1f}' for k in range(10)) + f' Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'),
    "rocket": lambda s, c: (f'<path d="M{s * .5} {s * .05} C{s * .72} {s * .22} {s * .7} {s * .55} {s * .62} {s * .7} L{s * .38} {s * .7} '
                            f'C{s * .3} {s * .55} {s * .28} {s * .22} {s * .5} {s * .05} Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                            f'<circle cx="{s * .5}" cy="{s * .35}" r="{s * .07}" {_st(s, c)}/>'
                            f'<path d="M{s * .38} {s * .55} L{s * .22} {s * .76} L{s * .4} {s * .7} M{s * .62} {s * .55} L{s * .78} {s * .76} L{s * .6} {s * .7} '
                            f'M{s * .44} {s * .8} L{s * .5} {s * .96} L{s * .56} {s * .8}" {_st(s, c)}/>'),
    "fox": lambda s, c: (f'<path d="M{s * .12} {s * .1} L{s * .32} {s * .4} L{s * .68} {s * .4} L{s * .88} {s * .1} L{s * .86} {s * .5} '
                         f'L{s * .5} {s * .92} L{s * .14} {s * .5} Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                         f'<circle cx="{s * .37}" cy="{s * .55}" r="{s * .035}" fill="{c}"/><circle cx="{s * .63}" cy="{s * .55}" r="{s * .035}" fill="{c}"/>'
                         f'<circle cx="{s * .5}" cy="{s * .8}" r="{s * .04}" fill="{c}"/>'),
    "hedgehog": lambda s, c: ('<path d="M' + " L".join(
        f'{s * (.5 + (.46 if k % 2 == 0 else .34) * math.cos(math.pi + math.pi * k / 16)):.1f} '
        f'{s * (.72 + (.46 if k % 2 == 0 else .34) * math.sin(math.pi + math.pi * k / 16)):.1f}' for k in range(17)) +
        f' Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
        f'<path d="M{s * .82} {s * .72} C{s * .98} {s * .7} {s * .98} {s * .86} {s * .82} {s * .86} L{s * .2} {s * .86} C{s * .1} {s * .86} {s * .1} {s * .72} {s * .2} {s * .72}" {_st(s, c)}/>'
        f'<circle cx="{s * .86}" cy="{s * .77}" r="{s * .025}" fill="{c}"/>'),
    "store": lambda s, c: (f'<path d="M{s * .1} {s * .4} L{s * .1} {s * .92} L{s * .9} {s * .92} L{s * .9} {s * .4}" fill="{c}" fill-opacity="0.08" {_st(s, c)}/>'
                           f'<path d="M{s * .05} {s * .4} L{s * .15} {s * .15} L{s * .85} {s * .15} L{s * .95} {s * .4} Z" fill="{c}" fill-opacity="0.25" {_st(s, c)}/>'
                           f'<path d="M{s * .5} {s * .2} L{s * .5} {s * .36} M{s * .42} {s * .28} L{s * .58} {s * .28}" {_st(s, c, .05)}/>'
                           f'<rect x="{s * .4}" y="{s * .6}" width="{s * .2}" height="{s * .32}" {_st(s, c)}/>'),
    "tea": lambda s, c: (f'<path d="M{s * .16} {s * .45} L{s * .7} {s * .45} L{s * .64} {s * .82} C{s * .62} {s * .9} {s * .24} {s * .9} {s * .22} {s * .82} Z" '
                         f'fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                         f'<path d="M{s * .68} {s * .52} C{s * .9} {s * .5} {s * .9} {s * .72} {s * .65} {s * .72}" {_st(s, c)}/>'
                         f'<path d="M{s * .08} {s * .93} L{s * .82} {s * .93}" {_st(s, c)}/>'),
    "book": lambda s, c: (f'<path d="M{s * .5} {s * .2} C{s * .38} {s * .12} {s * .2} {s * .12} {s * .08} {s * .18} L{s * .08} {s * .86} C{s * .2} {s * .8} '
                          f'{s * .38} {s * .8} {s * .5} {s * .88} C{s * .62} {s * .8} {s * .8} {s * .8} {s * .92} {s * .86} L{s * .92} {s * .18} '
                          f'C{s * .8} {s * .12} {s * .62} {s * .12} {s * .5} {s * .2} Z M{s * .5} {s * .2} L{s * .5} {s * .88}" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'),
})


def trio(L, sid, v, dur, cue):
    """Two to four ideas as pictures in a row, each popping in on its word; `cross` strikes each one out as it
    lands (the things that did NOT make the difference)."""
    items = v["items"][:4]
    n = len(items)
    s_ = L.px(0.17)
    gap = (L.w * 0.84 - n * s_) / max(1, n - 1) if n > 1 else 0
    x0 = L.w * 0.08 + (L.w * 0.84 - (n * s_ + (n - 1) * gap)) / 2
    y = L.h * 0.36
    head, tw = _head(L, sid, v, 0.12)
    cells = ""
    cross = bool(v.get("cross"))
    for i, it in enumerate(items):
        x = x0 + i * (s_ + gap)
        icon = ICONS.get(it.get("icon", ""), lambda s, c: "")(s_, L.accent)
        cells += (f'<div id="{sid}-i{i}" style="position:absolute;left:{x - L.px(0.04):.0f}px;top:{y:.0f}px;width:{s_ + L.px(0.08)}px;text-align:center;">'
                  f'<svg width="{s_}" height="{s_}" style="overflow:visible">{icon}'
                  + (f'<path id="{sid}-x{i}" d="M{-s_ * .05:.0f} {-s_ * .05:.0f} L{s_ * 1.05:.0f} {s_ * 1.05:.0f} M{s_ * 1.05:.0f} {-s_ * .05:.0f} L{-s_ * .05:.0f} {s_ * 1.05:.0f}" '
                     f'stroke="#E77A5F" stroke-width="{L.px(0.01)}" stroke-linecap="round" stroke-dasharray="{s_ * 3:.0f}" stroke-dashoffset="{s_ * 3:.0f}"/>' if cross else "")
                  + f'</svg><div style="font-size:{L.fs(0.03)}px;line-height:1.25;margin-top:{L.px(0.02)}px;font-weight:600;">{E(it["label"])}</div></div>')
        at = max(0.3 + 0.2 * i, cue(it.get("cue", ""), 0.5 + (dur - 1.5) * i / n))
        tw.append(_ft(f"#{sid}-i{i}", "opacity: 0, y: 30, scale: 0.85", 'opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(1.7)"', at))
        if cross:
            # read it first, then strike it: the label holds ~0.5 s + 0.3 s a word before anything touches it
            hold = 0.5 + 0.3 * len(it["label"].split())
            tw.append(_ft(f"#{sid}-x{i}", f"strokeDashoffset: {s_ * 3:.0f}", 'strokeDashoffset: 0, duration: 0.35, ease: "power3.out"', at + hold))
            tw.append(_ft(f"#{sid}-i{i}", "opacity: 1", 'opacity: 0.55, duration: 0.4, ease: "power2.out"', at + hold + 0.4, later=True))
    foot = ""
    if v.get("line"):
        foot = (f'<div id="{sid}-ln" class="serif" style="position:absolute;left:0;right:0;top:{L.h * 0.72:.0f}px;text-align:center;font-size:{L.fs(0.06)}px;">'
                f'{E(v["line"])}</div>')
        tw.append(_blur_in(f"#{sid}-ln", max(1.0, cue(v.get("line_cue", ""), dur * 0.75)), 0.45))
    return f'<div id="{sid}-c" style="position:absolute;inset:0;">{head}{cells}{foot}</div>', "", tw


def _icon_motion(L, sid, motion: str, s_: float, dur: float, at: float, v: dict) -> list[str]:
    """Motion that says something about the object: a wheel that keeps turning faster (spin), a pendulum between two
    extremes (swing), a snowball that grows (grow), a hope that rises (rise), a thing that sinks or breaks on the word
    that names it (sink, crack, shake). Finite tweens only: every frame is a function of time."""
    c = f"{s_ / 2:.0f} {s_ / 2:.0f}"
    if motion == "spin":
        turns = float(v.get("turns", 2.5))
        return [_ft(f"#{sid}-art", f'rotation: 0, svgOrigin: "{c}"', f'rotation: {360 * turns:.0f}, svgOrigin: "{c}", duration: {dur:.2f}, ease: "power2.in"', 0)]
    if motion == "swing":  # a pendulum hung from the top centre
        o, tw, t, k = f"{s_ / 2:.0f} 0", [], 0.3, 0
        period = float(v.get("period", 1.6))
        while t < dur - 0.2:
            a0, a1 = (22, -22) if k % 2 else (-22, 22)
            tw.append(_ft(f"#{sid}-art", f'rotation: {a0}, svgOrigin: "{o}"', f'rotation: {a1}, svgOrigin: "{o}", duration: {period / 2:.2f}, ease: "sine.inOut"', t, later=k > 0))
            t += period / 2
            k += 1
        return tw
    if motion == "grow":
        o = f"{s_ / 2:.0f} {s_:.0f}"
        return [_ft(f"#{sid}-art", f'scale: 0.45, svgOrigin: "{o}"', f'scale: 1.2, svgOrigin: "{o}", duration: {dur - 0.3:.2f}, ease: "power2.in"', 0.2)]
    if motion == "rise":
        return [_ft(f"#{sid}-art", "y: 40", f'y: -{s_ * 0.18:.0f}, duration: {dur - 0.3:.2f}, ease: "sine.inOut"', 0.2)]
    if motion == "sink":
        return [_ft(f"#{sid}-art", "y: 0, opacity: 1", f'y: {s_ * 0.35:.0f}, opacity: 0.3, duration: 1.2, ease: "power3.in"', at)]
    if motion == "shake":
        return [_ft(f"#{sid}-art", "x: 0", 'x: -14, duration: 0.06, ease: "none"', at),
                _ft(f"#{sid}-art", "x: -14", 'x: 12, duration: 0.08, ease: "none"', at + 0.06, later=True),
                _ft(f"#{sid}-art", "x: 12", 'x: 0, duration: 0.3, ease: "elastic.out(1, 0.4)"', at + 0.14, later=True)]
    if motion == "crack":
        return [_ft(f"#{sid}-a1", f'x: 0, rotation: 0, svgOrigin: "{c}"', f'x: -{s_ * 0.1:.0f}, rotation: -9, svgOrigin: "{c}", duration: 0.6, ease: "power3.out"', at),
                _ft(f"#{sid}-a2", f'x: 0, rotation: 0, svgOrigin: "{c}"', f'x: {s_ * 0.1:.0f}, rotation: 9, svgOrigin: "{c}", duration: 0.6, ease: "power3.out"', at)]
    return []


def icon(L, sid, v, dur, cue):
    """One drawn object, big, with its own small life (steam from a cup; or a `motion` that carries the meaning:
    spin, swing, grow, rise, sink, crack, shake, the event ones on `motion_cue`), and the line it stands for.
    Pick the object for what the line SAYS (a flywheel for momentum, a pendulum for swings), never for decoration."""
    s_ = L.px(0.3)
    x, y = (L.w - s_) / 2, L.h * 0.2
    head, tw = _head(L, sid, v, 0.12)
    art = ICONS.get(v.get("icon", ""), lambda s, c: "")(s_, L.accent)
    steam = ""
    if v.get("steam"):
        for k in range(3):
            pid = f"{sid}-sm{k}"
            sx = s_ * (0.3 + 0.13 * k)
            steam += (f'<path id="{pid}" d="M{sx:.0f} {s_ * .38:.0f} c {-s_ * .05:.0f} {-s_ * .06:.0f} {s_ * .05:.0f} {-s_ * .1:.0f} 0 {-s_ * .18:.0f} '
                      f'c {-s_ * .05:.0f} {-s_ * .06:.0f} {s_ * .05:.0f} {-s_ * .1:.0f} 0 {-s_ * .16:.0f}" fill="none" stroke="{L.ink}" stroke-width="{s_ * .02:.1f}" '
                      f'stroke-linecap="round" opacity="0"/>')
            for rep in range(int(dur / 2.2) + 1):
                at = 0.4 + k * 0.7 + rep * 2.2
                tw.append(_ft(f"#{pid}", "opacity: 0, y: 10", 'opacity: 0.6, y: -6, duration: 1.0, ease: "sine.out"', at, later=rep > 0))
                tw.append(_ft(f"#{pid}", "opacity: 0.6, y: -6", f'opacity: 0, y: -{L.px(0.04)}, duration: 1.0, ease: "sine.in"', at + 1.0, later=True))
    motion = v.get("motion", "")
    if motion == "crack":  # two halves of the same drawing, pulled apart on the cue
        art = (f'<defs><clipPath id="{sid}-hl"><rect x="-10" y="-10" width="{s_ / 2 + 10}" height="{s_ + 20}"/></clipPath>'
               f'<clipPath id="{sid}-hr"><rect x="{s_ / 2}" y="-10" width="{s_ / 2 + 10}" height="{s_ + 20}"/></clipPath></defs>'
               f'<g id="{sid}-a1" clip-path="url(#{sid}-hl)">{art}</g><g id="{sid}-a2" clip-path="url(#{sid}-hr)">{art}</g>')
    else:
        art = f'<g id="{sid}-art">{art}</g>'
    tw += _icon_motion(L, sid, motion, s_, dur, cue(v.get("motion_cue", ""), dur * 0.45) if v.get("motion_cue") else dur * 0.45, v)
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <svg id="{sid}-ic" width="{s_}" height="{s_}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;overflow:visible">{art}{steam}</svg>
      {f'<div id="{sid}-ln" class="serif" style="position:absolute;left:{L.px(0.08)}px;right:{L.px(0.08)}px;top:{y + s_ + L.px(0.06):.0f}px;text-align:center;font-size:{L.fs(0.065)}px;line-height:1.15;">{E(v["line"])}</div>' if v.get('line') else ''}
    </div>"""
    tw.insert(0, _ft(f"#{sid}-ic", "opacity: 0, scale: 0.8, y: 20", 'opacity: 1, scale: 1, y: 0, duration: 0.7, ease: "back.out(1.5)"', 0.1))
    if v.get("line"):
        tw.append(_blur_in(f"#{sid}-ln", max(0.5, cue(v.get("line_cue", ""), 0.7)), 0.45))
    return m, "", tw


def climb(L, sid, v, dur, cue):
    """A mountain path: the walker sets out, reaches a comfortable ledge (`rest`, e.g. "Tốt") and stops there on
    `stop_cue`, while the summit (`peak`, e.g. "Vĩ đại") lights up above, still unclimbed. For lines about settling:
    good enough, comfort, the plateau that keeps you from the top."""
    head, tw = _head(L, sid, v, 0.1)
    x0, x1, gy = L.w * 0.12, L.w * 0.88, L.h * 0.86
    px, py = L.w * 0.62, L.h * 0.22  # summit
    lx, ly = L.w * 0.42, L.h * 0.56  # ledge
    sw = max(3, L.px(0.005))
    ridge = f"M{x0:.0f} {gy:.0f} L{lx - L.px(0.12):.0f} {ly + L.px(0.06):.0f} L{lx + L.px(0.08):.0f} {ly:.0f} L{px:.0f} {py:.0f} L{x1:.0f} {gy:.0f} Z"
    path = [(x0 + L.px(0.06), gy - 4), (lx - L.px(0.2), ly + L.px(0.17)), (lx - L.px(0.02), ly - 4)]
    up = [(lx + L.px(0.06), ly - 6), (px - L.px(0.06), py + L.px(0.12)), (px, py - 6)]
    pd = "M" + " L".join(f"{a:.0f} {b:.0f}" for a, b in path)
    ud = "M" + " L".join(f"{a:.0f} {b:.0f}" for a, b in [path[-1]] + up)
    plen = sum(math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1)) + 4
    bench = (f'<path d="M{lx - L.px(0.05):.0f} {ly - L.px(0.03):.0f} L{lx + L.px(0.05):.0f} {ly - L.px(0.03):.0f} M{lx - L.px(0.045):.0f} {ly - L.px(0.03):.0f} '
             f'L{lx - L.px(0.045):.0f} {ly:.0f} M{lx + L.px(0.045):.0f} {ly - L.px(0.03):.0f} L{lx + L.px(0.045):.0f} {ly:.0f} M{lx - L.px(0.05):.0f} {ly - L.px(0.06):.0f} '
             f'L{lx + L.px(0.05):.0f} {ly - L.px(0.06):.0f}" fill="none" stroke="{L.ink}" stroke-width="{sw}" stroke-linecap="round"/>')
    flag = (f'<path d="M{px:.0f} {py:.0f} L{px:.0f} {py - L.px(0.09):.0f} L{px + L.px(0.06):.0f} {py - L.px(0.07):.0f} L{px:.0f} {py - L.px(0.05):.0f}" '
            f'fill="{L.accent}" fill-opacity="0.6" stroke="{L.accent}" stroke-width="{sw}" stroke-linejoin="round"/>')
    t_stop = max(1.6, cue(v.get("stop_cue", ""), dur * 0.45))
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">{head}
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <path id="{sid}-mt" d="{ridge}" fill="{L.ink}" fill-opacity="0.05" stroke="{L.ink}" stroke-opacity="0.6" stroke-width="{sw}" stroke-linejoin="round"/>
        <path id="{sid}-pt" d="{pd}" fill="none" stroke="{L.accent}" stroke-width="{sw}" stroke-dasharray="{plen:.0f}" stroke-dashoffset="{plen:.0f}" stroke-linecap="round"/>
        <path id="{sid}-up" d="{ud}" fill="none" stroke="{L.muted}" stroke-width="2" stroke-dasharray="6 10" opacity="0"/>
        <g id="{sid}-bn" opacity="0">{bench}</g>
        <g id="{sid}-fl" opacity="0">{flag}</g>
        <circle id="{sid}-w" cx="{path[0][0]:.0f}" cy="{path[0][1] - L.px(0.02):.0f}" r="{L.px(0.016)}" fill="{L.accent}"/>
        <text id="{sid}-rl" x="{lx:.0f}" y="{ly + L.px(0.06):.0f}" text-anchor="middle" fill="{L.ink}" font-family="EB Garamond" font-size="{L.fs(0.05)}" opacity="0">{E(v.get("rest", ""))}</text>
        <text id="{sid}-pl" x="{px:.0f}" y="{py - L.px(0.12):.0f}" text-anchor="middle" fill="{L.accent}" font-family="EB Garamond" font-size="{L.fs(0.06)}" opacity="0">{E(v.get("peak", ""))}</text>
      </svg>
      {f'<div id="{sid}-ln" class="muted" style="position:absolute;left:{L.px(0.08)}px;width:{L.w * 0.4:.0f}px;top:{L.h * 0.26:.0f}px;font-size:{L.fs(0.032)}px;line-height:1.35;opacity:0;">{E(v["line"])}</div>' if v.get('line') else ''}
    </div>"""
    tw += [_fade(f"#{sid}-mt", 0.1, 0.6), _fade(f"#{sid}-fl", 0.5, 0.5), _blur_in(f"#{sid}-pl", 0.6, 0.4), _fade(f"#{sid}-bn", 0.7, 0.4),
           _ft(f"#{sid}-pt", f"strokeDashoffset: {plen:.0f}", f'strokeDashoffset: 0, duration: {t_stop - 0.3:.2f}, ease: "power1.inOut"', 0.3)]
    # the walker follows the path to the ledge and sits down
    seg_t = (t_stop - 0.3) / (len(path) - 1)
    for i in range(1, len(path)):
        tw.append(_ft(f"#{sid}-w", f'attr: {{cx: {path[i - 1][0]:.0f}, cy: {path[i - 1][1] - L.px(0.02):.0f}}}',
                      f'attr: {{cx: {path[i][0]:.0f}, cy: {path[i][1] - L.px(0.02):.0f}}}, duration: {seg_t:.2f}, ease: "power1.inOut"', 0.3 + seg_t * (i - 1), later=i > 1))
    tw += [_blur_in(f"#{sid}-rl", t_stop, 0.4),
           _ft(f"#{sid}-up", "opacity: 0", 'opacity: 0.8, duration: 0.6, ease: "power2.out"', t_stop + 0.6)]
    if v.get("line"):
        tw.append(_fade(f"#{sid}-ln", max(t_stop + 0.8, cue(v.get("line_cue", ""), t_stop + 1.0)), 0.5))
    return m, "", tw


def book(L, sid, v, dur, cue):
    """A drawn book cover (title, author, year) with the facts about it landing beside it on their words."""
    bw, bh = L.px(0.36), L.px(0.5)
    bx, by = L.w * 0.1, L.h * 0.24
    head, tw = _head(L, sid, v, 0.12)
    cover = f"""<div id="{sid}-bk" style="position:absolute;left:{bx:.0f}px;top:{by:.0f}px;width:{bw}px;height:{bh}px;border-radius:6px {L.px(0.02)}px {L.px(0.02)}px 6px;
      background:linear-gradient(135deg, {L.accent} 0%, #B9844A 100%);box-shadow:{L.px(0.02)}px {L.px(0.02)}px {L.px(0.05)}px rgba(0,0,0,0.55), inset {L.px(0.018)}px 0 0 rgba(0,0,0,0.18);
      color:#17130E;padding:{L.px(0.04)}px {L.px(0.035)}px;display:flex;flex-direction:column;">
      <div style="font-size:{L.fs(0.02)}px;letter-spacing:0.3em;font-weight:800;opacity:0.7;">{E(v.get('year', ''))}</div>
      <div class="serif" style="font-size:{L.fs(0.07)}px;line-height:1;margin-top:{L.px(0.05)}px;">{E(v['title'])}</div>
      <div style="height:3px;width:40%;background:#17130E;margin:{L.px(0.03)}px 0;opacity:0.6;"></div>
      <div style="font-size:{L.fs(0.026)}px;font-weight:700;margin-top:auto;">{E(v.get('author', ''))}</div></div>"""
    tw.append(_ft(f"#{sid}-bk", "opacity: 0, rotationY: -35, x: -40", 'opacity: 1, rotationY: 0, x: 0, duration: 0.8, ease: "expo.out"', 0.15))
    rx = bx + bw + L.px(0.08)
    facts = ""
    for i, f in enumerate(v.get("facts", [])):
        facts += (f'<div id="{sid}-f{i}" style="display:flex;gap:{L.px(0.02)}px;align-items:baseline;margin-top:{L.px(0.03)}px;">'
                  f'<span class="serif acc" style="font-size:{L.fs(0.06)}px;min-width:{L.px(0.17)}px;white-space:nowrap;">{E(f.get("big", ""))}</span>'
                  f'<span style="font-size:{L.fs(0.03)}px;line-height:1.3;">{E(f["text"])}</span></div>')
        tw.append(_rise(f"#{sid}-f{i}", max(0.6, cue(f.get("cue", ""), 1.0 + 1.2 * i)), 0.5, 14))
    m = (f'<div id="{sid}-c" style="position:absolute;inset:0;perspective:{L.px(1.5)}px;">{head}{cover}'
         f'<div style="position:absolute;left:{rx:.0f}px;right:{L.px(0.06)}px;top:{by + L.px(0.02):.0f}px;">{facts}</div></div>')
    return m, "", tw


def _poly(s, pts, closed=True):
    return ("M" + " L".join(f"{s * x:.1f} {s * y:.1f}" for x, y in pts) + (" Z" if closed else ""))


ICONS.update({
    "brain": lambda s, c: (f'<path d="M{s*.5} {s*.16} C{s*.38} {s*.06} {s*.18} {s*.12} {s*.18} {s*.3} C{s*.06} {s*.36} {s*.06} {s*.56} {s*.18} {s*.62} '
                           f'C{s*.16} {s*.8} {s*.36} {s*.9} {s*.5} {s*.8} C{s*.64} {s*.9} {s*.84} {s*.8} {s*.82} {s*.62} C{s*.94} {s*.56} {s*.94} {s*.36} {s*.82} {s*.3} '
                           f'C{s*.82} {s*.12} {s*.62} {s*.06} {s*.5} {s*.16} Z" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                           f'<path d="M{s*.5} {s*.16} L{s*.5} {s*.8} M{s*.3} {s*.36} C{s*.38} {s*.4} {s*.38} {s*.5} {s*.3} {s*.54} M{s*.7} {s*.36} C{s*.62} {s*.4} {s*.62} {s*.5} {s*.7} {s*.54}" {_st(s, c, .03)}/>'),
    "lightning": lambda s, c: f'<path d="{_poly(s, [(.58,.04),(.2,.56),(.46,.56),(.38,.96),(.8,.4),(.54,.4)])}" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>',
    "turtle": lambda s, c: (f'<path d="M{s*.14} {s*.66} C{s*.14} {s*.3} {s*.74} {s*.3} {s*.74} {s*.66} Z" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                            f'<path d="M{s*.3} {s*.5} L{s*.58} {s*.5} M{s*.44} {s*.38} L{s*.44} {s*.66}" {_st(s, c, .025)}/>'
                            f'<circle cx="{s*.84}" cy="{s*.58}" r="{s*.08}" {_st(s, c)}/>'
                            f'<path d="M{s*.22} {s*.66} L{s*.2} {s*.8} M{s*.62} {s*.66} L{s*.64} {s*.8} M{s*.08} {s*.66} L{s*.8} {s*.66}" {_st(s, c)}/>'),
    "coin": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.4}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                          f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.3}" {_st(s, c, .02)}/>'
                          f'<path d="M{s*.58} {s*.38} C{s*.5} {s*.32} {s*.38} {s*.36} {s*.42} {s*.46} C{s*.46} {s*.54} {s*.6} {s*.52} {s*.58} {s*.62} '
                          f'C{s*.54} {s*.7} {s*.44} {s*.68} {s*.4} {s*.62} M{s*.5} {s*.28} L{s*.5} {s*.72}" {_st(s, c, .03)}/>'),
    "coins": lambda s, c: "".join(f'<ellipse cx="{s*.5}" cy="{s*(.82 - .14*k)}" rx="{s*.34}" ry="{s*.08}" fill="{c}" fill-opacity="{.1 + .05*k:.2f}" {_st(s, c, .03)}/>'
                                  for k in range(5)),
    "snowball": lambda s, c: (f'<path d="M{s*.04} {s*.9} L{s*.96} {s*.9}" {_st(s, c)}/>'
                              f'<circle cx="{s*.16}" cy="{s*.84}" r="{s*.05}" {_st(s, c, .025)}/><circle cx="{s*.36}" cy="{s*.76}" r="{s*.13}" {_st(s, c, .03)}/>'
                              f'<circle cx="{s*.7}" cy="{s*.62}" r="{s*.27}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'),
    "dice": lambda s, c: (f'<rect x="{s*.14}" y="{s*.14}" width="{s*.72}" height="{s*.72}" rx="{s*.12}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                          + "".join(f'<circle cx="{s*x}" cy="{s*y}" r="{s*.055}" fill="{c}"/>' for x, y in ((.32,.32),(.68,.32),(.5,.5),(.32,.68),(.68,.68)))),
    "scale": lambda s, c: (f'<path d="M{s*.5} {s*.12} L{s*.5} {s*.86} M{s*.3} {s*.86} L{s*.7} {s*.86} M{s*.14} {s*.24} L{s*.86} {s*.24}" {_st(s, c)}/>'
                           f'<path d="M{s*.14} {s*.24} L{s*.04} {s*.52} L{s*.24} {s*.52} Z M{s*.86} {s*.24} L{s*.76} {s*.52} L{s*.96} {s*.52} Z" fill="{c}" fill-opacity="0.15" {_st(s, c, .028)}/>'),
    "shield": lambda s, c: (f'<path d="M{s*.5} {s*.06} L{s*.86} {s*.2} C{s*.86} {s*.56} {s*.72} {s*.8} {s*.5} {s*.94} C{s*.28} {s*.8} {s*.14} {s*.56} {s*.14} {s*.2} Z" '
                            f'fill="{c}" fill-opacity="0.15" {_st(s, c)}/><path d="M{s*.34} {s*.5} L{s*.46} {s*.62} L{s*.68} {s*.38}" {_st(s, c, .045)}/>'),
    "people": lambda s, c: "".join(f'<circle cx="{s*x}" cy="{s*(y-.2)}" r="{s*r*.5}" {_st(s, c, .028)}/><path d="M{s*(x-r)} {s*(y+.22)} C{s*(x-r)} {s*(y-.06)} '
                                   f'{s*(x+r)} {s*(y-.06)} {s*(x+r)} {s*(y+.22)}" fill="{c}" fill-opacity="0.12" {_st(s, c, .028)}/>'
                                   for x, y, r in ((.22,.62,.15),(.78,.62,.15),(.5,.58,.2))),
    "compass": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.42}" fill="{c}" fill-opacity="0.08" {_st(s, c)}/>'
                             f'<path d="{_poly(s, [(.5,.16),(.6,.5),(.5,.84),(.4,.5)])}" fill="{c}" fill-opacity="0.3" {_st(s, c, .028)}/>'
                             f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.04}" fill="{c}"/>'),
    "binoculars": lambda s, c: (f'<circle cx="{s*.27}" cy="{s*.64}" r="{s*.2}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                                f'<circle cx="{s*.73}" cy="{s*.64}" r="{s*.2}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                                f'<path d="M{s*.14} {s*.5} L{s*.24} {s*.18} L{s*.4} {s*.18} L{s*.44} {s*.5} M{s*.86} {s*.5} L{s*.76} {s*.18} L{s*.6} {s*.18} L{s*.56} {s*.5} '
                                f'M{s*.44} {s*.46} L{s*.56} {s*.46}" {_st(s, c)}/>'),
    "target": lambda s, c: ("".join(f'<circle cx="{s*.46}" cy="{s*.54}" r="{s*r}" {_st(s, c, .03)} fill="{c}" fill-opacity="{o}"/>'
                                    for r, o in ((.4, .06), (.27, .1), (.13, .2)))
                            + f'<path d="M{s*.46} {s*.54} L{s*.9} {s*.1} M{s*.78} {s*.1} L{s*.9} {s*.1} L{s*.9} {s*.22}" {_st(s, c)}/>'),
    "clock": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.42}" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                           f'<path d="M{s*.5} {s*.22} L{s*.5} {s*.5} L{s*.7} {s*.62}" {_st(s, c, .045)}/>'),
    "hourglass": lambda s, c: (f'<path d="M{s*.2} {s*.08} L{s*.8} {s*.08} M{s*.2} {s*.92} L{s*.8} {s*.92}" {_st(s, c)}/>'
                               f'<path d="M{s*.26} {s*.08} C{s*.26} {s*.36} {s*.46} {s*.42} {s*.46} {s*.5} C{s*.46} {s*.58} {s*.26} {s*.64} {s*.26} {s*.92} '
                               f'L{s*.74} {s*.92} C{s*.74} {s*.64} {s*.54} {s*.58} {s*.54} {s*.5} C{s*.54} {s*.42} {s*.74} {s*.36} {s*.74} {s*.08} Z" fill="none" {_st(s, c)}/>'
                               f'<path d="{_poly(s, [(.3,.88),(.7,.88),(.5,.66)])}" fill="{c}" fill-opacity="0.45"/>'),
    "swan": lambda s, c: (f'<path d="M{s*.14} {s*.62} C{s*.2} {s*.86} {s*.7} {s*.9} {s*.86} {s*.62} C{s*.7} {s*.66} {s*.56} {s*.62} {s*.52} {s*.52} '
                          f'C{s*.46} {s*.38} {s*.6} {s*.2} {s*.5} {s*.12} C{s*.42} {s*.06} {s*.3} {s*.12} {s*.32} {s*.2} L{s*.22} {s*.24} L{s*.34} {s*.26} '
                          f'C{s*.42} {s*.3} {s*.38} {s*.4} {s*.36} {s*.5} C{s*.34} {s*.6} {s*.24} {s*.64} {s*.14} {s*.62} Z" fill="{c}" fill-opacity="0.3" {_st(s, c)}/>'),
    "mask": lambda s, c: (f'<path d="M{s*.08} {s*.3} C{s*.3} {s*.22} {s*.7} {s*.22} {s*.92} {s*.3} C{s*.92} {s*.62} {s*.74} {s*.86} {s*.5} {s*.86} '
                          f'C{s*.26} {s*.86} {s*.08} {s*.62} {s*.08} {s*.3} Z" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                          f'<path d="M{s*.24} {s*.44} C{s*.3} {s*.38} {s*.38} {s*.38} {s*.42} {s*.44} M{s*.58} {s*.44} C{s*.62} {s*.38} {s*.7} {s*.38} {s*.76} {s*.44} '
                          f'M{s*.34} {s*.66} C{s*.44} {s*.74} {s*.56} {s*.74} {s*.66} {s*.66}" {_st(s, c, .035)}/>'),
    "umbrella": lambda s, c: (f'<path d="M{s*.06} {s*.5} C{s*.1} {s*.14} {s*.9} {s*.14} {s*.94} {s*.5} C{s*.8} {s*.42} {s*.64} {s*.42} {s*.5} {s*.5} '
                              f'C{s*.36} {s*.42} {s*.2} {s*.42} {s*.06} {s*.5} Z" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'
                              f'<path d="M{s*.5} {s*.5} L{s*.5} {s*.84} C{s*.5} {s*.94} {s*.36} {s*.94} {s*.36} {s*.84}" {_st(s, c)}/>'),
    "chart": lambda s, c: (f'<path d="M{s*.08} {s*.08} L{s*.08} {s*.92} L{s*.92} {s*.92}" {_st(s, c)}/>'
                           f'<path d="{_poly(s, [(.14,.78),(.34,.6),(.5,.68),(.7,.4),(.88,.18)], False)}" {_st(s, c, .045)}/>'),
    "pie": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.52}" r="{s*.4}" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                         f'<path d="M{s*.5} {s*.52} L{s*.5} {s*.12} M{s*.5} {s*.52} L{s*.85} {s*.72} M{s*.5} {s*.52} L{s*.15} {s*.72}" {_st(s, c, .03)}/>'
                         f'<path d="M{s*.5} {s*.52} L{s*.5} {s*.12} A{s*.4} {s*.4} 0 0 1 {s*.85} {s*.72} Z" fill="{c}" fill-opacity="0.4"/>'),
})


ICONS.update({
    "anchor": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.16}" r="{s*.08}" {_st(s, c)}/><path d="M{s*.5} {s*.24} L{s*.5} {s*.88} M{s*.32} {s*.36} L{s*.68} {s*.36} '
                            f'M{s*.14} {s*.6} C{s*.16} {s*.8} {s*.34} {s*.88} {s*.5} {s*.88} C{s*.66} {s*.88} {s*.84} {s*.8} {s*.86} {s*.6} '
                            f'M{s*.08} {s*.66} L{s*.14} {s*.58} L{s*.22} {s*.66} M{s*.78} {s*.66} L{s*.86} {s*.58} L{s*.92} {s*.66}" {_st(s, c)}/>'),
    "hammer": lambda s, c: (f'<path d="{_poly(s, [(.18,.18),(.62,.18),(.7,.3),(.62,.4),(.18,.4)])}" fill="{c}" fill-opacity="0.25" {_st(s, c)}/>'
                            f'<path d="M{s*.42} {s*.4} L{s*.42} {s*.92}" {_st(s, c, .07)}/>'),
    "pendulum": lambda s, c: (f'<path d="M{s*.2} {s*.06} L{s*.8} {s*.06} M{s*.5} {s*.06} L{s*.5} {s*.72}" {_st(s, c)}/>'
                              f'<circle cx="{s*.5}" cy="{s*.8}" r="{s*.11}" fill="{c}" fill-opacity="0.35" {_st(s, c)}/>'),
    "letter": lambda s, c: (f'<rect x="{s*.08}" y="{s*.22}" width="{s*.84}" height="{s*.56}" rx="{s*.04}" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                            f'<path d="M{s*.08} {s*.24} L{s*.5} {s*.56} L{s*.92} {s*.24}" {_st(s, c)}/>'),
    "house": lambda s, c: (f'<path d="{_poly(s, [(.06,.48),(.5,.1),(.94,.48)], False)}" {_st(s, c)}/>'
                           f'<path d="{_poly(s, [(.16,.4),(.16,.9),(.84,.9),(.84,.4)], False)}" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                           f'<rect x="{s*.42}" y="{s*.6}" width="{s*.16}" height="{s*.3}" {_st(s, c, .03)}/>'
                           f'<rect x="{s*.24}" y="{s*.52}" width="{s*.12}" height="{s*.12}" {_st(s, c, .025)}/><rect x="{s*.64}" y="{s*.52}" width="{s*.12}" height="{s*.12}" {_st(s, c, .025)}/>'),
    "haystack": lambda s, c: (f'<path d="M{s*.06} {s*.88} C{s*.1} {s*.4} {s*.3} {s*.14} {s*.5} {s*.14} C{s*.7} {s*.14} {s*.9} {s*.4} {s*.94} {s*.88} Z" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'
                              + "".join(f'<path d="M{s*x} {s*.86} L{s*(x+.06)} {s*y}" {_st(s, c, .02)}/>' for x, y in ((.2,.5),(.36,.36),(.52,.3),(.66,.42),(.78,.6)))),
    "chess": lambda s, c: (f'<path d="M{s*.3} {s*.9} L{s*.72} {s*.9} L{s*.68} {s*.76} L{s*.66} {s*.5} C{s*.74} {s*.42} {s*.74} {s*.22} {s*.58} {s*.12} '
                           f'L{s*.5} {s*.06} L{s*.46} {s*.16} C{s*.36} {s*.2} {s*.24} {s*.34} {s*.22} {s*.48} L{s*.4} {s*.44} L{s*.36} {s*.76} Z" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'),
    "cards": lambda s, c: (f'<rect x="{s*.12}" y="{s*.2}" width="{s*.44}" height="{s*.62}" rx="{s*.05}" transform="rotate(-12 {s*.34} {s*.5})" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                           f'<rect x="{s*.42}" y="{s*.16}" width="{s*.44}" height="{s*.62}" rx="{s*.05}" transform="rotate(10 {s*.64} {s*.47})" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'
                           f'<path d="M{s*.64} {s*.36} C{s*.56} {s*.28} {s*.5} {s*.4} {s*.64} {s*.54} C{s*.78} {s*.4} {s*.72} {s*.28} {s*.64} {s*.36} Z" fill="{c}"/>'),
    "submarine": lambda s, c: (f'<path d="M{s*.12} {s*.62} C{s*.12} {s*.48} {s*.24} {s*.44} {s*.36} {s*.44} L{s*.74} {s*.44} C{s*.9} {s*.44} {s*.94} {s*.56} {s*.94} {s*.62} '
                               f'C{s*.94} {s*.7} {s*.86} {s*.78} {s*.74} {s*.78} L{s*.36} {s*.78} C{s*.24} {s*.78} {s*.12} {s*.74} {s*.12} {s*.62} Z" fill="{c}" fill-opacity="0.18" {_st(s, c)}/>'
                               f'<path d="M{s*.46} {s*.44} L{s*.5} {s*.28} L{s*.64} {s*.28} L{s*.66} {s*.44} M{s*.56} {s*.28} L{s*.56} {s*.16} L{s*.64} {s*.16} '
                               f'M{s*.12} {s*.62} L{s*.04} {s*.5} M{s*.12} {s*.62} L{s*.04} {s*.74}" {_st(s, c)}/>'
                               + "".join(f'<circle cx="{s*x}" cy="{s*.6}" r="{s*.035}" {_st(s, c, .02)}/>' for x in (.44, .58, .72))),
    "ship": lambda s, c: (f'<path d="{_poly(s, [(.06,.6),(.94,.6),(.8,.84),(.2,.84)])}" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'
                          f'<path d="M{s*.5} {s*.6} L{s*.5} {s*.1} M{s*.5} {s*.14} L{s*.78} {s*.5} L{s*.5} {s*.5} M{s*.5} {s*.2} L{s*.26} {s*.5} L{s*.5} {s*.5}" {_st(s, c)}/>'),
    "mountain": lambda s, c: (f'<path d="{_poly(s, [(.04,.9),(.38,.28),(.52,.5),(.66,.2),(.96,.9)])}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                              f'<path d="{_poly(s, [(.58,.34),(.66,.2),(.74,.34)], False)}" {_st(s, c, .03)}/>'),
    "sprout": lambda s, c: (f'<path d="M{s*.5} {s*.9} L{s*.5} {s*.44} M{s*.5} {s*.56} C{s*.3} {s*.56} {s*.18} {s*.42} {s*.2} {s*.28} C{s*.36} {s*.28} {s*.5} {s*.38} {s*.5} {s*.56} '
                            f'M{s*.5} {s*.46} C{s*.52} {s*.26} {s*.66} {s*.14} {s*.84} {s*.16} C{s*.84} {s*.34} {s*.7} {s*.46} {s*.5} {s*.46}" fill="{c}" fill-opacity="0.2" {_st(s, c)}/>'
                            f'<path d="M{s*.24} {s*.9} L{s*.76} {s*.9}" {_st(s, c)}/>'),
    "tree": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.36}" r="{s*.28}" fill="{c}" fill-opacity="0.18" {_st(s, c)}/>'
                          f'<path d="M{s*.5} {s*.92} L{s*.5} {s*.46} M{s*.5} {s*.62} L{s*.36} {s*.48} M{s*.5} {s*.56} L{s*.62} {s*.44} M{s*.3} {s*.92} L{s*.7} {s*.92}" {_st(s, c)}/>'),
    "magnifier": lambda s, c: (f'<circle cx="{s*.42}" cy="{s*.42}" r="{s*.28}" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                               f'<path d="M{s*.62} {s*.62} L{s*.9} {s*.9}" {_st(s, c, .07)}/>'),
    "mirror": lambda s, c: (f'<ellipse cx="{s*.5}" cy="{s*.4}" rx="{s*.26}" ry="{s*.32}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                            f'<path d="M{s*.5} {s*.72} L{s*.5} {s*.92} M{s*.34} {s*.92} L{s*.66} {s*.92} M{s*.38} {s*.26} L{s*.46} {s*.18} M{s*.36} {s*.38} L{s*.54} {s*.2}" {_st(s, c, .03)}/>'),
    "key": lambda s, c: (f'<circle cx="{s*.28}" cy="{s*.5}" r="{s*.16}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                         f'<path d="M{s*.44} {s*.5} L{s*.92} {s*.5} M{s*.78} {s*.5} L{s*.78} {s*.64} M{s*.88} {s*.5} L{s*.88} {s*.62}" {_st(s, c)}/>'),
    "lock": lambda s, c: (f'<rect x="{s*.2}" y="{s*.44}" width="{s*.6}" height="{s*.46}" rx="{s*.06}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                          f'<path d="M{s*.32} {s*.44} L{s*.32} {s*.3} C{s*.32} {s*.08} {s*.68} {s*.08} {s*.68} {s*.3} L{s*.68} {s*.44} M{s*.5} {s*.6} L{s*.5} {s*.74}" {_st(s, c)}/>'),
    "bridge": lambda s, c: (f'<path d="M{s*.04} {s*.62} L{s*.96} {s*.62} M{s*.04} {s*.62} C{s*.3} {s*.2} {s*.7} {s*.2} {s*.96} {s*.62} '
                            f'M{s*.2} {s*.62} L{s*.2} {s*.44} M{s*.35} {s*.62} L{s*.35} {s*.34} M{s*.5} {s*.62} L{s*.5} {s*.31} M{s*.65} {s*.62} L{s*.65} {s*.34} M{s*.8} {s*.62} L{s*.8} {s*.44} '
                            f'M{s*.1} {s*.62} L{s*.1} {s*.9} M{s*.9} {s*.62} L{s*.9} {s*.9}" {_st(s, c)}/>'
                            f'<path d="M{s*.04} {s*.84} q {s*.08} -{s*.04} {s*.16} 0 t {s*.16} 0 t {s*.16} 0 t {s*.16} 0 t {s*.16} 0" {_st(s, c, .02)}/>'),
    "checklist": lambda s, c: (f'<rect x="{s*.16}" y="{s*.08}" width="{s*.68}" height="{s*.84}" rx="{s*.05}" fill="{c}" fill-opacity="0.08" {_st(s, c)}/>'
                               + "".join(f'<path d="M{s*.26} {s*y} L{s*.32} {s*(y+.05)} L{s*.42} {s*(y-.05)} M{s*.5} {s*y} L{s*.74} {s*y}" {_st(s, c, .03)}/>'
                                         for y in (.28, .5, .72))),
    "eye": lambda s, c: (f'<path d="M{s*.04} {s*.5} C{s*.24} {s*.18} {s*.76} {s*.18} {s*.96} {s*.5} C{s*.76} {s*.82} {s*.24} {s*.82} {s*.04} {s*.5} Z" fill="{c}" fill-opacity="0.1" {_st(s, c)}/>'
                         f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.15}" fill="{c}" fill-opacity="0.4" {_st(s, c)}/>'),
    "fork": lambda s, c: (f'<path d="M{s*.5} {s*.94} L{s*.5} {s*.56} C{s*.5} {s*.4} {s*.24} {s*.34} {s*.18} {s*.1} M{s*.5} {s*.56} C{s*.5} {s*.4} {s*.76} {s*.34} {s*.82} {s*.1}" {_st(s, c, .06)}/>'
                          f'<path d="M{s*.1} {s*.18} L{s*.18} {s*.08} L{s*.26} {s*.18} M{s*.74} {s*.18} L{s*.82} {s*.08} L{s*.9} {s*.18}" {_st(s, c)}/>'),
    "gear": lambda s, c: ("".join(f'<rect x="{s*.45}" y="{s*.04}" width="{s*.1}" height="{s*.18}" rx="{s*.02}" transform="rotate({a} {s*.5} {s*.5})" fill="{c}" fill-opacity="0.3" {_st(s, c, .025)}/>'
                                  for a in range(0, 360, 45))
                          + f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.3}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/><circle cx="{s*.5}" cy="{s*.5}" r="{s*.1}" {_st(s, c)}/>'),
    "bubble": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.48}" r="{s*.38}" fill="{c}" fill-opacity="0.08" {_st(s, c)}/>'
                            f'<path d="M{s*.28} {s*.36} C{s*.32} {s*.24} {s*.42} {s*.18} {s*.52} {s*.18}" {_st(s, c, .03)}/>'),
    "lighthouse": lambda s, c: (f'<path d="{_poly(s, [(.4,.92),(.44,.34),(.56,.34),(.6,.92)])}" fill="{c}" fill-opacity="0.15" {_st(s, c)}/>'
                                f'<rect x="{s*.4}" y="{s*.2}" width="{s*.2}" height="{s*.14}" fill="{c}" fill-opacity="0.5" {_st(s, c, .03)}/>'
                                f'<path d="M{s*.38} {s*.2} L{s*.5} {s*.1} L{s*.62} {s*.2} M{s*.4} {s*.27} L{s*.06} {s*.14} M{s*.4} {s*.27} L{s*.06} {s*.4} '
                                f'M{s*.6} {s*.27} L{s*.94} {s*.14} M{s*.6} {s*.27} L{s*.94} {s*.4} M{s*.2} {s*.92} L{s*.8} {s*.92}" {_st(s, c, .025)}/>'),
    "wave": lambda s, c: "".join(f'<path d="M{s*.04} {s*y} q {s*.115} -{s*.12} {s*.23} 0 t {s*.23} 0 t {s*.23} 0 t {s*.23} 0" {_st(s, c, .035)} opacity="{o}"/>'
                                 for y, o in ((.4, 1), (.6, .7), (.8, .45))),
    "puzzle": lambda s, c: (f'<path d="M{s*.14} {s*.3} L{s*.38} {s*.3} C{s*.34} {s*.14} {s*.6} {s*.14} {s*.56} {s*.3} L{s*.8} {s*.3} L{s*.8} {s*.5} C{s*.94} {s*.46} {s*.94} {s*.72} {s*.8} {s*.68} '
                            f'L{s*.8} {s*.88} L{s*.14} {s*.88} Z" fill="{c}" fill-opacity="0.18" {_st(s, c)}/>'),
    "door": lambda s, c: (f'<rect x="{s*.24}" y="{s*.08}" width="{s*.52}" height="{s*.84}" rx="{s*.03}" fill="{c}" fill-opacity="0.12" {_st(s, c)}/>'
                          f'<circle cx="{s*.66}" cy="{s*.52}" r="{s*.035}" fill="{c}"/><path d="M{s*.1} {s*.92} L{s*.9} {s*.92}" {_st(s, c)}/>'),
    "flywheel": lambda s, c: (f'<circle cx="{s*.5}" cy="{s*.5}" r="{s*.42}" {_st(s, c, .07)}/><circle cx="{s*.5}" cy="{s*.5}" r="{s*.08}" fill="{c}" fill-opacity="0.4" {_st(s, c)}/>'
                              + "".join(f'<path d="M{s*.5} {s*.5} L{s*(.5 + .38 * math.cos(math.pi * k / 4)):.1f} {s*(.5 + .38 * math.sin(math.pi * k / 4)):.1f}" {_st(s, c, .03)}/>' for k in range(8))
                              + f'<circle cx="{s*.5}" cy="{s*.08}" r="{s*.04}" fill="{c}"/>'),
    "bench": lambda s, c: (f'<path d="M{s*.06} {s*.5} L{s*.94} {s*.5} M{s*.06} {s*.34} L{s*.94} {s*.34} M{s*.14} {s*.5} L{s*.14} {s*.82} M{s*.86} {s*.5} L{s*.86} {s*.82} '
                           f'M{s*.14} {s*.34} L{s*.14} {s*.5} M{s*.86} {s*.34} L{s*.86} {s*.5}" {_st(s, c, .05)}/>'),
})


_TAG = re.compile(r"<[^<>]+>")
_ATTR = re.compile(r'\s([\w:-]+)="[^"]*"')


def _first_attrs(svg: str) -> str:
    """Keep the first of any repeated attribute in each tag (an explicit fill before the shared stroke style wins)."""
    def tag(m):
        seen = set()

        def attr(a):
            if a.group(1) in seen:
                return ""
            seen.add(a.group(1))
            return a.group(0)
        return _ATTR.sub(attr, m.group(0))
    return _TAG.sub(tag, svg)


ICONS = {k: (lambda f: (lambda s, c: _first_attrs(f(s, c))))(f) for k, f in ICONS.items()}


METAPHORS = {"funnel": funnel, "ladder": ladder, "venn": venn, "flywheel": flywheel, "halo": halo, "swap": swap,
             "company": company, "rise": rise, "trio": trio, "icon": icon, "book": book, "climb": climb}
GENERATORS.update(METAPHORS)
