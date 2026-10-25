"""Metaphor scenes: the object on screen IS the explanation (HyperFrames explainer guidance).

Each one is a small machine whose working is the idea, built up one part per spoken cue:
- funnel   "one chosen out of many": a field of dots counts in, then all but a few dim and the survivors gather in a row
- ladder   a hierarchy that builds step by step; the top step lights and two qualities fuse onto it
- venn     three circles arrive on their words; their intersection fills and is named
- flywheel a heavy wheel pushed turn by turn, accelerating until speed lines appear and it runs on its own
- halo     cards wearing a halo; on the cue the halo fails and the verdict stamps over the card
- swap     one thing is let go (struck and dropped) so another can take its place

Same contract as scenes.py: ids prefixed with the beat id, fromTo tweens only, everything a function of timeline time,
deterministic (seeded) layouts.
"""

from __future__ import annotations

import math
import random

from .scenes import E, _fade, _fmt_num, _ft, _rise


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
    tw.append(_ft(f"#{sid}-a", "opacity: 1, y: 0, rotation: 0", 'opacity: 0.35, y: 40, rotation: -6, duration: 0.9, ease: "power3.in"', t + 0.45, later=True))
    tw.append(_ft(f"#{sid}-arw", f"strokeDashoffset: {L.w:.0f}", 'strokeDashoffset: 0, duration: 0.7, ease: "power2.inOut"', t + 0.6))
    tb = max(t + 1.1, cue(b.get("cue", ""), t + 1.2))
    tw.append(_ft(f"#{sid}-b", "opacity: 0, scale: 0.7", 'opacity: 1, scale: 1, duration: 0.6, ease: "back.out(1.6)"', tb))
    if v.get("line"):
        tw.append(_blur_in(f"#{sid}-ln", max(0.5, cue(v.get("line_cue", ""), tb + 0.8)), 0.45))
    return m, "", tw


METAPHORS = {"funnel": funnel, "ladder": ladder, "venn": venn, "flywheel": flywheel, "halo": halo, "swap": swap}
