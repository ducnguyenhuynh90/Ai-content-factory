"""Visual metaphors for lessons: the abstract idea drawn as a concrete, moving picture.

Charts prove a number; a metaphor makes the idea stick (dual coding: words + an image the viewer can replay).
Each kind is line art in the brand look (ink strokes, one accent), drawn as SVG and animated with GSAP, with
its key action landing on a narration cue. Test for every scene: watch the pictures with the sound off and
they still tell the story (HyperFrames story rule).

A kind returns (svg, css, tweens); `scenes.metaphor` adds the caption and the scene wrapper.
Coordinates are in pixels of the full frame; the picture lives above y = 0.70 h, the caption below it.
"""

from __future__ import annotations

import html
import math

E = html.escape


def _ft(sel, frm, to, at, later=False):
    extra = ", immediateRender: false" if later else ""
    return f'tl.fromTo("{sel}", {{{frm}}}, {{{to}{extra}}}, {max(0.0, at):.3f});'


def _show(sel, at, d=0.3):
    return _ft(sel, "opacity: 0", f'opacity: 1, duration: {d}, ease: "power2.out"', at)


def _bob(sel, t0, t1, amp, period=0.36):
    """A finite walk/breath cycle between t0 and t1 (odd repeat count so it ends where it began)."""
    n = max(1, int((t1 - t0) / (period / 2)))
    n += (n + 1) % 2  # odd
    return _ft(sel, "y: 0", f'y: {-amp:.1f}, duration: {period / 2:.3f}, repeat: {n}, yoyo: true, ease: "sine.inOut"', t0)


def figure(fid, x, gy, h, cls="fig"):
    """A person as five strokes and a head. Outer <g> travels, inner <g id=…-b> bobs."""
    r = h * 0.12
    hip, sh = gy - h * 0.42, gy - h * 0.70
    d = (f"M{x:.1f} {gy - h + 2 * r:.1f} L{x:.1f} {hip:.1f} M{x:.1f} {hip:.1f} L{x - h * 0.13:.1f} {gy:.1f} "
         f"M{x:.1f} {hip:.1f} L{x + h * 0.13:.1f} {gy:.1f} M{x - h * 0.17:.1f} {gy - h * 0.38:.1f} L{x:.1f} {sh:.1f} "
         f"L{x + h * 0.17:.1f} {gy - h * 0.38:.1f}")
    return (f'<g id="{fid}" class="{cls}"><g id="{fid}-b"><circle cx="{x:.1f}" cy="{gy - h + r:.1f}" r="{r:.1f}" class="hd"/>'
            f'<path d="{d}" class="ln"/></g></g>')


def xf(x, y, scale=1.0, rot=0.0):
    """An SVG transform turning/scaling about (x, y). Scene templates are built before layout, so GSAP's
    bbox-based origins (transformOrigin, svgOrigin) can be wrong; tween this as an attribute instead."""
    return f"translate({x:.1f} {y:.1f}) rotate({rot:.2f}) scale({scale:.3f}) translate({-x:.1f} {-y:.1f})"


def _xf(sel, x, y, frm, to, at, dur, ease="power2.out", later=False):
    """Tween an element's transform attribute from (scale, rot) `frm` to `to` about (x, y)."""
    return _ft(sel, f'attr: {{ transform: "{xf(x, y, *frm)}" }}', f'attr: {{ transform: "{xf(x, y, *to)}" }}, duration: {dur:.2f}, '
               f'ease: "{ease}"', at, later)


def coin(cid, x, y, r, L):
    return (f'<g id="{cid}"><circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{L.accent}"/>'
            f'<text x="{x:.1f}" y="{y + r * 0.36:.1f}" text-anchor="middle" font-family="{L.serif}" font-weight="700" '
            f'font-size="{r * 1.1:.0f}" fill="{L.bg}">£</text></g>')


def base_css(L, sid):
    sw = max(3, L.px(0.0045))
    return f"""
    #{sid}-svg .fig {{ stroke: {L.ink}; fill: {L.ink}; }}
    #{sid}-svg .hero {{ stroke: {L.accent}; fill: {L.accent}; }}
    #{sid}-svg .ghost {{ stroke: {L.muted}; fill: {L.muted}; }}
    #{sid}-svg .ln {{ fill: none; stroke-width: {sw}; stroke-linecap: round; stroke-linejoin: round; }}
    #{sid}-svg .hd {{ stroke: none; }}
    #{sid}-svg .lbl {{ font-family: {L.sans}; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; }}
    #{sid}-svg .num {{ font-family: {L.serif}; font-weight: 500; font-variant-numeric: tabular-nums; }}
    """


def _label(lid, x, y, text, L, size=0.028, color=None, anchor="middle", cls="lbl"):
    return (f'<text id="{lid}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="{cls}" font-size="{L.fs(size)}" '
            f'fill="{color or L.ink}">{E(text)}</text>')


def _counter(sid, key, el_id, frm, to, at, dur, dec=0):
    return (f'const {sid}{key} = {{ v: {frm} }};\n'
            f'tl.fromTo({sid}{key}, {{ v: {frm} }}, {{ v: {to}, duration: {dur:.2f}, ease: "power2.out", onUpdate: () => {{ '
            f'document.getElementById("{el_id}").textContent = {sid}{key}.v.toLocaleString("en-US", '
            f'{{minimumFractionDigits: {dec}, maximumFractionDigits: {dec}}}); }} }}, {at:.3f});')


# ---------------------------------------------------------------- kinds

def bubble(L, sid, v, dur, cue):
    """A price inflating as a bubble over the people under it, then bursting on the cue (`cue`: 'burst')."""
    W, H = L.w, L.h
    cx, cy, R = W / 2, H * 0.33, H * 0.215
    gy = H * 0.665
    t_pop = cue(v.get("cue", ""), dur * 0.4)
    pre = E(v.get("prefix", ""))
    frm, peak, to = float(v.get("from", 0)), float(v.get("peak", v.get("from", 0))), float(v.get("to", 0))
    fs = L.fs(0.085)
    frags, tw = [], []
    for i in range(14):
        a = 2 * math.pi * i / 14 + 0.2
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        x2, y2 = cx + R * 1.0 * math.cos(a + 0.18), cy + R * math.sin(a + 0.18)
        frags.append(f'<path id="{sid}-f{i}" d="M{x:.1f} {y:.1f} Q{cx + R * 1.06 * math.cos(a + 0.09):.1f} '
                     f'{cy + R * 1.06 * math.sin(a + 0.09):.1f} {x2:.1f} {y2:.1f}" stroke="{L.accent}" fill="none" '
                     f'stroke-width="{max(3, L.px(0.005))}" stroke-linecap="round" style="opacity:0"/>')
        k = 0.55 + 0.25 * ((i * 7) % 5) / 4
        tw.append(_ft(f"#{sid}-f{i}", "x: 0, y: 0", f'x: {math.cos(a) * R * k:.1f}, y: {math.sin(a) * R * k + H * 0.04:.1f}, '
                      f'duration: 0.7, ease: "power3.out"', t_pop))
        tw.append(_ft(f"#{sid}-f{i}", "opacity: 0", 'opacity: 1, duration: 0.02, ease: "none"', t_pop))
        tw.append(_ft(f"#{sid}-f{i}", "opacity: 1", 'opacity: 0, duration: 0.45, ease: "power2.in"', t_pop + 0.3, later=True))
    people = "".join(figure(f"{sid}-p{i}", W * x, gy, H * 0.1, "ghost") for i, x in enumerate((0.16, 0.22, 0.28, 0.72, 0.78)))
    svg = f"""
      <line x1="{W * 0.12:.0f}" y1="{gy:.0f}" x2="{W * 0.88:.0f}" y2="{gy:.0f}" stroke="{L.muted}" stroke-width="2" opacity="0.6"/>
      {people}
      <g id="{sid}-bub" transform="{xf(cx, cy, 0.75)}">
        <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" fill="{L.accent}" fill-opacity="0.10" stroke="{L.accent}" stroke-width="{max(3, L.px(0.005))}"/>
        <path d="M{cx - R * 0.62:.1f} {cy - R * 0.38:.1f} A{R * 0.75:.1f} {R * 0.75:.1f} 0 0 1 {cx - R * 0.2:.1f} {cy - R * 0.7:.1f}"
          stroke="{L.ink}" stroke-opacity="0.55" stroke-width="{max(3, L.px(0.006))}" fill="none" stroke-linecap="round"/>
      </g>
      <circle id="{sid}-ring" cx="{cx:.1f}" cy="{cy:.1f}" r="{R:.1f}" fill="none" stroke="{L.ink}" stroke-width="2" style="opacity:0"/>
      {''.join(frags)}
      <g id="{sid}-val"><text x="{cx:.1f}" y="{cy + fs * 0.33:.1f}" text-anchor="middle" class="num" font-size="{fs}" fill="{L.ink}">{pre}<tspan id="{sid}-v">{frm:,.0f}</tspan></text></g>
      {_label(f"{sid}-after", cx, cy + H * 0.07 + fs * 0.33 + L.fs(0.06), v.get("after", ""), L, 0.028, L.muted)}"""
    # inflate (with a slight wobble), the price counting up with it
    grow = max(0.6, t_pop - 0.35)
    tw = [_xf(f"#{sid}-bub", cx, cy, (0.75,), (1.0,), 0.05, grow, "power1.in"),
          _xf(f"#{sid}-bub", cx, cy, (1.0,), (1.1,), t_pop - 0.07, 0.07, later=True),
          _ft(f"#{sid}-bub", "opacity: 1", 'opacity: 0, duration: 0.05, ease: "none"', t_pop),
          _ft(f"#{sid}-ring", "opacity: 0", 'opacity: 0.8, duration: 0.05, ease: "none"', t_pop),
          _ft(f"#{sid}-ring", "opacity: 0.8", 'opacity: 0, duration: 0.5, ease: "power2.out"', t_pop + 0.05, later=True),
          _ft(f"#{sid}-ring", "attr: { r: %.1f }" % R, 'attr: { r: %.1f }, duration: 0.55, ease: "power2.out"' % (R * 1.35), t_pop),
          _ft(f"#{sid}-val", "y: 0", f'y: {H * 0.07:.1f}, duration: 0.6, ease: "bounce.out"', t_pop + 0.05),
          _ft(f"#{sid}-after", "opacity: 0, y: 10", 'opacity: 1, y: 0, duration: 0.35, ease: "power2.out"', t_pop + 0.7)]
    for i in range(5):
        tw.append(_ft(f"#{sid}-p{i}-b", "y: 0", f'y: 6, duration: 0.18, ease: "power2.out"', t_pop + 0.02 * i))
    if peak != frm:
        tw.append(_counter(sid, "U", f"{sid}-v", frm, peak, 0.1, grow - 0.1))
    tw.append(_counter(sid, "D", f"{sid}-v", peak, to, t_pop + 0.05, 0.8))
    return svg, "", tw + [_ft(f"#{sid}-val text", f"fill: \"{L.ink}\"", f'fill: "{L.accent}", duration: 0.2', t_pop + 0.05)]


def _stairs(W, H, gy, n=7):
    x0, x1, top = W * 0.34, W * 0.92, H * 0.20
    sw_, sh_ = (x1 - x0) / n, (gy - top) / n
    d = f"M{x0:.1f} {gy:.1f}"
    for i in range(n):
        d += f" L{x0 + sw_ * i:.1f} {gy - sh_ * (i + 1):.1f} L{x0 + sw_ * (i + 1):.1f} {gy - sh_ * (i + 1):.1f}"
    return d, x0, sw_, sh_


def crowd(L, sid, v, dur, cue):
    """People and a rising price, three ways (`mode`):
    climb  - a crowd climbs a staircase of rising prices; on `cue` the hero steps off with a bag of profit;
    watch  - the hero stands on the ground while the crowd keeps climbing, coins popping over their heads;
    follow - everyone marches after the person in front toward the edge; on `cue` the front ones go over it."""
    W, H = L.w, L.h
    gy = H * 0.665
    mode = v.get("mode", "follow")
    fh = H * 0.13
    t_cue = cue(v.get("cue", ""), dur * 0.5)
    hero = v.get("hero", "")
    parts, tw = [], []
    if mode in ("climb", "watch"):
        d, x0, sw_, sh_ = _stairs(W, H, gy)
        parts.append(f'<path id="{sid}-st" d="{d}" stroke="{L.muted}" stroke-width="{max(3, L.px(0.004))}" fill="none"/>')
        parts.append(f'<line x1="{W * 0.05:.0f}" y1="{gy:.0f}" x2="{x0:.0f}" y2="{gy:.0f}" stroke="{L.muted}" stroke-width="{max(3, L.px(0.004))}"/>')
        parts.append(_label(f"{sid}-up", W * 0.93, H * 0.16, v.get("label", "PRICE ↑"), L, 0.026, L.accent, "end"))
        tw.append(_show(f"#{sid}-up", 0.3))
        steps = [1, 2, 3, 4]
        climb = 1 if mode == "climb" else 2
        for j, s in enumerate(steps):
            x = x0 + sw_ * (s - 0.5)
            y = gy - sh_ * s
            fid = f"{sid}-m{j}"
            parts.append(figure(fid, x, y, fh))
            t0 = 0.2 + 0.12 * j
            t1 = (t_cue if mode == "climb" else dur) - 0.3
            tw.append(_ft(f"#{fid}", "x: 0, y: 0", f'x: {sw_ * climb:.1f}, y: {-sh_ * climb:.1f}, duration: {max(0.5, t1 - t0):.2f}, ease: "none"', t0))
            tw.append(_bob(f"#{fid}-b", t0, t1, fh * 0.05))
        if mode == "climb":  # the hero stands on the lowest step, then steps down and walks away with the profit
            hx = x0 + sw_ * 0.5
            hy = gy - sh_
            parts.append(figure(f"{sid}-h", hx - sw_ * 0.25, hy, fh, "fig hero"))
            parts.append(f'<g id="{sid}-bag">{coin(f"{sid}-bc", hx - W * 0.22 + fh * 0.32, gy - fh * 0.42, fh * 0.16, L)}</g>')
            parts.append(_label(f"{sid}-pl", hx - W * 0.22, gy + L.fs(0.05), v.get("gain", "+ profit"), L, 0.028, L.accent))
            tw.append(_ft(f"#{sid}-h", "x: 0, y: 0", f'x: {-W * 0.22 + sw_ * 0.25:.1f}, y: {sh_:.1f}, duration: 0.9, ease: "power2.inOut"', t_cue))
            tw.append(_bob(f"#{sid}-h-b", t_cue, t_cue + 0.9, fh * 0.05))
            tw.append(_ft(f"#{sid}-bag", "opacity: 0, scale: 0.4", f'opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.5)", transformOrigin: "50% 50%"', t_cue + 0.85))
            tw.append(_show(f"#{sid}-pl", t_cue + 1.0))
            if hero:
                parts.append(_label(f"{sid}-hn", hx - W * 0.22, gy + L.fs(0.05) * 2.1, hero, L, 0.026, L.muted))
                tw.append(_show(f"#{sid}-hn", t_cue + 1.1))
        else:  # watch: the hero on the ground; coins pop over the climbers
            hx = W * 0.14
            parts.append(figure(f"{sid}-h", hx, gy, fh, "fig hero"))
            if hero:
                parts.append(_label(f"{sid}-hn", hx, gy + L.fs(0.05), hero, L, 0.026, L.accent))
                tw.append(_show(f"#{sid}-hn", 0.3))
            for j, s in enumerate(steps):
                for k in range(2):
                    t = 0.6 + j * 0.45 + k * (dur * 0.42)
                    if t > dur - 0.8:
                        continue
                    x = x0 + sw_ * (s - 0.5) + sw_ * climb * (t / dur)
                    y = gy - sh_ * s - sh_ * climb * (t / dur) - fh * 1.25
                    cid = f"{sid}-c{j}{k}"
                    parts.append(f'<g id="{cid}" style="opacity:0">{coin(cid + "i", x, y, fh * 0.12, L)}</g>')
                    tw.append(_ft(f"#{cid}", "opacity: 0, y: 10", 'opacity: 1, y: -10, duration: 0.25, ease: "back.out(2)"', t))
                    tw.append(_ft(f"#{cid}", "opacity: 1, y: -10", 'opacity: 0, y: -40, duration: 0.5, ease: "power1.in"', t + 0.6, later=True))
            # the hero's head turns from side to side as they watch: a small lean toward the crowd on the cue
            tw.append(_ft(f"#{sid}-h-b", "rotation: 0", f'rotation: 6, duration: 0.6, ease: "power2.inOut", svgOrigin: "{hx:.0f} {gy:.0f}"', t_cue))
    else:  # follow
        edge = W * 0.74
        parts.append(f'<path d="M{W * 0.04:.0f} {gy:.0f} L{edge:.0f} {gy:.0f} L{edge - W * 0.01:.0f} {gy + H * 0.06:.0f}" stroke="{L.muted}" '
                     f'stroke-width="{max(3, L.px(0.004))}" fill="none"/>')
        sign_x = W * 0.86
        parts.append(f'<g id="{sid}-sign"><text x="{sign_x:.0f}" y="{H * 0.3:.0f}" text-anchor="middle" class="num" '
                     f'font-size="{L.fs(0.06)}" fill="{L.accent}">{E(v.get("label", "£ ↑"))}</text></g>')
        tw.append(_ft(f"#{sid}-sign", "opacity: 0, y: 14", 'opacity: 1, y: 0, duration: 0.5, ease: "power2.out"', 0.2))
        tw.append(_ft(f"#{sid}-sign", "y: 0", f'y: -12, duration: 0.9, repeat: {max(1, int(dur / 1.8) * 2 - 1)}, yoyo: true, ease: "sine.inOut"', 0.7, later=True))
        n = 8
        gap = W * 0.075
        walk = W * 0.16
        t_stop = max(0.8, t_cue)
        for j in range(n):
            x = W * 0.08 + gap * j
            fid = f"{sid}-m{j}"
            fig_svg = figure(fid, x, gy, fh, "fig hero" if j == 1 and v.get("hero_in_crowd") else "fig")
            parts.append(f'<g id="{fid}-tip">{fig_svg}</g>' if j >= n - 3 else fig_svg)
            tw.append(_ft(f"#{fid}", "x: 0", f'x: {walk:.1f}, duration: {t_stop - 0.1:.2f}, ease: "none"', 0.1))
            tw.append(_bob(f"#{fid}-b", 0.1, t_stop, fh * 0.05))
            if j >= n - 3:  # the front three keep walking, one after another, off the edge
                k = n - 1 - j
                to_edge = edge - (x + walk) + gap * 0.25
                at = t_stop + 0.25 * k
                step = 0.45 + 0.3 * k  # they hurry: the last ones follow the first over the edge
                tw.append(_ft(f"#{fid}", f"x: {walk:.1f}", f'x: {walk + to_edge:.1f}, duration: {step:.2f}, ease: "none"', at, later=True))
                tw.append(_xf(f"#{fid}-tip", edge + gap * 0.25, gy, (1.0, 0.0), (1.0, 75.0), at + step, 0.45, "power2.in"))
                tw.append(_ft(f"#{fid}", "y: 0", f'y: {H * 0.05:.1f}, duration: 0.45, ease: "power2.in"', at + step + 0.1, later=True))
                tw.append(_ft(f"#{fid}", "opacity: 1", 'opacity: 0, duration: 0.2, ease: "none"', at + step + 0.3, later=True))
    return "".join(parts), "", tw


def balance(L, sid, v, dur, cue):
    """Price vs value on a scale: the price side floats up as hype inflates it (`cue`), then the gap closes
    (`close_cue`): the beam swings back and the hype pops."""
    W, H = L.w, L.h
    cx, py, gy = W / 2, H * 0.2, H * 0.665
    a, hang = H * 0.34, H * 0.2
    sw = max(3, L.px(0.005))
    t_up = cue(v.get("cue", ""), dur * 0.25)
    t_close = cue(v.get("close_cue", ""), dur * 0.75) if v.get("close_cue") else None
    th = float(v.get("tilt", 16))
    dy = a * math.sin(math.radians(th))
    dx = a * (1 - math.cos(math.radians(th)))  # the pans hang from the beam ends, which swing inward

    def pan(pid, x, text, content):
        return (f'<g id="{pid}"><line x1="{x - H * 0.09:.1f}" y1="{py + hang:.1f}" x2="{x:.1f}" y2="{py:.1f}" stroke="{L.muted}" stroke-width="2"/>'
                f'<line x1="{x + H * 0.09:.1f}" y1="{py + hang:.1f}" x2="{x:.1f}" y2="{py:.1f}" stroke="{L.muted}" stroke-width="2"/>'
                f'<path d="M{x - H * 0.11:.1f} {py + hang:.1f} Q{x:.1f} {py + hang + H * 0.07:.1f} {x + H * 0.11:.1f} {py + hang:.1f} Z" '
                f'fill="{L.ink}" fill-opacity="0.12" stroke="{L.ink}" stroke-width="{sw}"/>{content}'
                f'{_label(pid + "-t", x, py + hang + H * 0.07 + L.fs(0.042), text, L, 0.03)}</g>')

    lx, rx = cx - a, cx + a
    hype = (f'<g id="{sid}-hy"><circle cx="{lx:.1f}" cy="{py + hang - H * 0.075:.1f}" r="{H * 0.07:.1f}" fill="{L.accent}" fill-opacity="0.18" '
            f'stroke="{L.accent}" stroke-width="{sw}"/></g>')
    gold = (f'<path d="M{rx - H * 0.07:.1f} {py + hang:.1f} L{rx - H * 0.05:.1f} {py + hang - H * 0.06:.1f} L{rx + H * 0.05:.1f} {py + hang - H * 0.06:.1f} '
            f'L{rx + H * 0.07:.1f} {py + hang:.1f} Z" fill="{L.ink}" fill-opacity="0.85"/>')
    svg = f"""
      <path d="M{cx - H * 0.1:.1f} {gy:.1f} L{cx + H * 0.1:.1f} {gy:.1f} L{cx:.1f} {gy - H * 0.04:.1f} Z" fill="{L.muted}"/>
      <line x1="{cx:.1f}" y1="{py:.1f}" x2="{cx:.1f}" y2="{gy - H * 0.03:.1f}" stroke="{L.muted}" stroke-width="{sw}"/>
      <g id="{sid}-beam"><line x1="{lx:.1f}" y1="{py:.1f}" x2="{rx:.1f}" y2="{py:.1f}" stroke="{L.ink}" stroke-width="{sw * 1.4:.0f}" stroke-linecap="round"/></g>
      <circle cx="{cx:.1f}" cy="{py:.1f}" r="{sw * 2}" fill="{L.accent}"/>
      {pan(f"{sid}-pl", lx, v.get("left", "Price"), hype)}
      {pan(f"{sid}-pr", rx, v.get("right", "Value"), gold)}"""
    up = 1.6
    tw = [_ft(f"#{sid}-beam", "rotation: 0", f'rotation: {th}, duration: {up}, ease: "power2.inOut", svgOrigin: "{cx:.0f} {py:.0f}"', t_up),
          _ft(f"#{sid}-pl", "x: 0, y: 0", f'x: {dx:.1f}, y: {-dy:.1f}, duration: {up}, ease: "power2.inOut"', t_up),
          _ft(f"#{sid}-pr", "x: 0, y: 0", f'x: {-dx:.1f}, y: {dy:.1f}, duration: {up}, ease: "power2.inOut"', t_up),
          _ft(f"#{sid}-hy", "scale: 0.25", f'scale: 1.1, duration: {up + 0.4}, ease: "power1.inOut", transformOrigin: "50% 100%"', t_up - 0.2)]
    if t_close:
        tw += [_ft(f"#{sid}-hy", "opacity: 1", 'opacity: 0, duration: 0.08, ease: "none"', t_close),
               _ft(f"#{sid}-beam", f"rotation: {th}", f'rotation: -4, duration: 0.7, ease: "back.out(1.6)", svgOrigin: "{cx:.0f} {py:.0f}"', t_close, later=True),
               _ft(f"#{sid}-pl", f"x: {dx:.1f}, y: {-dy:.1f}", f'x: 0, y: {a * math.sin(math.radians(4)):.1f}, duration: 0.7, ease: "back.out(1.6)"', t_close, later=True),
               _ft(f"#{sid}-pr", f"x: {-dx:.1f}, y: {dy:.1f}", f'x: 0, y: {-a * math.sin(math.radians(4)):.1f}, duration: 0.7, ease: "back.out(1.6)"', t_close, later=True)]
    return svg, "", tw


def ship(L, sid, v, dur, cue):
    """A ship sails out along a dotted route to a destination (`cue`); on `cargo_cue` its real cargo is tagged."""
    W, H = L.w, L.h
    sea = H * 0.56
    sw = max(3, L.px(0.0045))
    t_dest = cue(v.get("cue", ""), dur * 0.3)
    t_cargo = cue(v.get("cargo_cue", ""), dur * 0.6)
    per = W * 0.18
    waves = []
    for k in range(3):
        y = sea + H * (0.035 + 0.045 * k)
        d = f"M{-per:.0f} {y:.0f}"
        x = -per
        while x < W + per:
            d += f" q{per / 4:.0f} {-H * 0.012:.0f} {per / 2:.0f} 0 t{per / 2:.0f} 0"
            x += per
        waves.append(f'<path id="{sid}-w{k}" d="{d}" stroke="{L.muted}" stroke-opacity="{0.8 - 0.2 * k:.1f}" stroke-width="{max(2, sw - k)}" fill="none"/>')
    sx = W * 0.2  # ship anchor point at the waterline
    hull = (f'<path d="M{sx - H * 0.14:.1f} {sea - H * 0.04:.1f} L{sx + H * 0.16:.1f} {sea - H * 0.04:.1f} L{sx + H * 0.11:.1f} {sea + H * 0.02:.1f} '
            f'L{sx - H * 0.1:.1f} {sea + H * 0.02:.1f} Z" fill="{L.ink}" stroke="{L.ink}" stroke-width="{sw}" stroke-linejoin="round"/>')
    masts = (f'<line x1="{sx - H * 0.03:.1f}" y1="{sea - H * 0.04:.1f}" x2="{sx - H * 0.03:.1f}" y2="{sea - H * 0.25:.1f}" stroke="{L.ink}" stroke-width="{sw}"/>'
             f'<line x1="{sx + H * 0.07:.1f}" y1="{sea - H * 0.04:.1f}" x2="{sx + H * 0.07:.1f}" y2="{sea - H * 0.19:.1f}" stroke="{L.ink}" stroke-width="{sw}"/>'
             f'<path d="M{sx - H * 0.03:.1f} {sea - H * 0.24:.1f} Q{sx + H * 0.045:.1f} {sea - H * 0.165:.1f} {sx - H * 0.03:.1f} {sea - H * 0.08:.1f} Z" fill="{L.ink}" fill-opacity="0.9"/>'
             f'<path d="M{sx + H * 0.07:.1f} {sea - H * 0.18:.1f} Q{sx + H * 0.13:.1f} {sea - H * 0.125:.1f} {sx + H * 0.07:.1f} {sea - H * 0.07:.1f} Z" fill="{L.accent}"/>'
             f'<path d="M{sx - H * 0.03:.1f} {sea - H * 0.25:.1f} l{H * 0.05:.1f} {H * 0.012:.1f} l{-H * 0.05:.1f} {H * 0.012:.1f}" fill="{L.accent}"/>')
    travel = W * 0.2
    tag_x, tag_y = sx + H * 0.02, sea - H * 0.36  # inside the ship group: it sails with her
    cargo = v.get("cargo", "")
    tag = ""
    if cargo:
        tag = (f'<g id="{sid}-tag"><line x1="{tag_x:.1f}" y1="{tag_y + L.fs(0.03) * 0.6:.1f}" x2="{tag_x:.1f}" y2="{sea - H * 0.27:.1f}" stroke="{L.accent}" stroke-width="2"/>'
               f'{_label(sid + "-tg", tag_x, tag_y, cargo, L, 0.03, L.accent)}</g>')
    # the route: dots on a curve from the ship to the destination pin
    dx0, dy0, dx1, dy1 = sx + travel + H * 0.18, sea - H * 0.06, W * 0.86, sea - H * 0.02
    dots = []
    for i in range(14):
        t = (i + 1) / 15
        x = (1 - t) ** 2 * dx0 + 2 * (1 - t) * t * (dx0 + dx1) / 2 + t * t * dx1
        y = (1 - t) ** 2 * dy0 + 2 * (1 - t) * t * (sea - H * 0.22) + t * t * dy1
        dots.append(f'<circle id="{sid}-d{i}" cx="{x:.1f}" cy="{y:.1f}" r="{max(3, L.px(0.004))}" fill="{L.accent}" style="opacity:0"/>')
    pin = (f'<g id="{sid}-pin"><circle cx="{dx1:.1f}" cy="{dy1 - H * 0.03:.1f}" r="{H * 0.016:.1f}" fill="{L.accent}"/>'
           f'<line x1="{dx1:.1f}" y1="{dy1 - H * 0.03:.1f}" x2="{dx1:.1f}" y2="{dy1:.1f}" stroke="{L.accent}" stroke-width="{sw}"/></g>'
           f'{_label(sid + "-dest", dx1, dy1 + H * 0.12, v.get("destination", ""), L, 0.026, L.ink)}')
    svg = f"""<line x1="0" y1="{sea:.0f}" x2="{W}" y2="{sea:.0f}" stroke="{L.muted}" stroke-width="2" opacity="0.5"/>
      {''.join(dots)}{pin}
      <g id="{sid}-ship"><g id="{sid}-rock">{masts}{hull}</g>{tag}</g>
      {''.join(waves)}"""
    tw = [_ft(f"#{sid}-w{k}", "x: 0", f'x: {-per * (2 - k * 0.5):.0f}, duration: {dur:.2f}, ease: "none"', 0) for k in range(3)]
    tw.append(_ft(f"#{sid}-ship", "x: 0", f'x: {travel:.0f}, duration: {dur:.2f}, ease: "sine.inOut"', 0))
    tw.append(_ft(f"#{sid}-rock", "rotation: -2", f'rotation: 2, duration: 1.1, repeat: {max(1, int(dur / 1.1) // 2 * 2 - 1)}, yoyo: true, '
                  f'ease: "sine.inOut", svgOrigin: "{sx:.0f} {sea:.0f}"', 0))
    for i in range(14):
        tw.append(_show(f"#{sid}-d{i}", t_dest - 0.7 + 0.05 * i, 0.12))
    tw.append(_ft(f"#{sid}-pin", "opacity: 0, y: -24", 'opacity: 1, y: 0, duration: 0.4, ease: "bounce.out"', t_dest))
    tw.append(_show(f"#{sid}-dest", t_dest + 0.15))
    if cargo:
        tw.append(_ft(f"#{sid}-tag", "opacity: 0, y: 12", 'opacity: 1, y: 0, duration: 0.35, ease: "back.out(2)"', t_cargo))
    return svg, "", tw


def mood(L, sid, v, dur, cue):
    """Graham's Mr. Market: a bowler-hatted partner whose mood (and price) swings on the cues; on
    `decline_cue` the offer is declined. `prices`: [euphoric, despairing]."""
    W, H = L.w, L.h
    cx, cy, r = W * 0.36, H * 0.33, H * 0.13
    sw = max(3, L.px(0.0055))
    t_hi = cue(v.get("up_cue", ""), dur * 0.4)
    t_lo = cue(v.get("down_cue", ""), dur * 0.6)
    t_no = cue(v.get("decline_cue", ""), dur * 0.82) if v.get("decline_cue") else None
    hi, lo = (v.get("prices") or ["£150", "£40"])[:2]
    tx, ty = W * 0.68, H * 0.36
    tag_w, tag_h = H * 0.3, H * 0.15
    svg = f"""
      <path d="M{cx - r * 1.25:.1f} {H * 0.665:.1f} Q{cx:.1f} {cy + r * 0.9:.1f} {cx + r * 1.25:.1f} {H * 0.665:.1f} Z" fill="{L.ink}" fill-opacity="0.9"/>
      <path d="M{cx - r * 0.18:.1f} {cy + r * 1.05:.1f} L{cx:.1f} {cy + r * 1.45:.1f} L{cx + r * 0.18:.1f} {cy + r * 1.05:.1f} Z" fill="{L.accent}"/>
      <g id="{sid}-head">
        <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{L.bg}" stroke="{L.ink}" stroke-width="{sw}"/>
        <path d="M{cx - r * 1.05:.1f} {cy - r * 0.6:.1f} L{cx + r * 1.05:.1f} {cy - r * 0.6:.1f}" stroke="{L.ink}" stroke-width="{sw * 1.6:.0f}" stroke-linecap="round"/>
        <path d="M{cx - r * 0.68:.1f} {cy - r * 0.62:.1f} Q{cx - r * 0.7:.1f} {cy - r * 1.55:.1f} {cx:.1f} {cy - r * 1.5:.1f} Q{cx + r * 0.7:.1f} {cy - r * 1.55:.1f} {cx + r * 0.68:.1f} {cy - r * 0.62:.1f} Z" fill="{L.ink}"/>
        <circle cx="{cx - r * 0.35:.1f}" cy="{cy - r * 0.1:.1f}" r="{sw * 1.2:.1f}" fill="{L.ink}"/>
        <circle cx="{cx + r * 0.35:.1f}" cy="{cy - r * 0.1:.1f}" r="{sw * 1.2:.1f}" fill="{L.ink}"/>
        <path id="{sid}-calm" d="M{cx - r * 0.35:.1f} {cy + r * 0.42:.1f} L{cx + r * 0.35:.1f} {cy + r * 0.42:.1f}" stroke="{L.ink}" stroke-width="{sw}" stroke-linecap="round" fill="none"/>
        <path id="{sid}-grin" d="M{cx - r * 0.45:.1f} {cy + r * 0.3:.1f} Q{cx:.1f} {cy + r * 0.85:.1f} {cx + r * 0.45:.1f} {cy + r * 0.3:.1f}" stroke="{L.accent}" stroke-width="{sw}" stroke-linecap="round" fill="none" style="opacity:0"/>
        <path id="{sid}-frown" d="M{cx - r * 0.4:.1f} {cy + r * 0.6:.1f} Q{cx:.1f} {cy + r * 0.2:.1f} {cx + r * 0.4:.1f} {cy + r * 0.6:.1f}" stroke="{L.ink}" stroke-width="{sw}" stroke-linecap="round" fill="none" style="opacity:0"/>
      </g>
      <g id="{sid}-tag">
        <rect x="{tx - tag_w / 2:.1f}" y="{ty - tag_h / 2:.1f}" width="{tag_w:.1f}" height="{tag_h:.1f}" rx="{H * 0.012:.1f}" fill="none" stroke="{L.ink}" stroke-width="{sw}"/>
        <circle cx="{tx - tag_w / 2 + H * 0.03:.1f}" cy="{ty:.1f}" r="{H * 0.01:.1f}" fill="{L.ink}"/>
        <text id="{sid}-of" x="{tx + H * 0.015:.1f}" y="{ty + L.fs(0.03) * 0.34:.1f}" text-anchor="middle" class="lbl" font-size="{L.fs(0.03)}" fill="{L.muted}">{E(v.get("offer", "Offer"))}</text>
        <text id="{sid}-ph" x="{tx + H * 0.015:.1f}" y="{ty + L.fs(0.07) * 0.34:.1f}" text-anchor="middle" class="num" font-size="{L.fs(0.07)}" fill="{L.accent}" style="opacity:0">{E(hi)}</text>
        <text id="{sid}-pl" x="{tx + H * 0.015:.1f}" y="{ty + L.fs(0.07) * 0.34:.1f}" text-anchor="middle" class="num" font-size="{L.fs(0.07)}" fill="{L.ink}" style="opacity:0">{E(lo)}</text>
      </g>
      {_label(sid + "-mh", tx, ty + tag_h / 2 + L.fs(0.05), v.get("up_label", "Euphoric"), L, 0.028, L.accent)}
      {_label(sid + "-ml", tx, ty + tag_h / 2 + L.fs(0.05), v.get("down_label", "Despairing"), L, 0.028, L.muted)}
      <g id="{sid}-no" data-layout-allow-overlap><text x="{tx:.1f}" y="{ty + L.fs(0.03):.1f}" text-anchor="middle" class="lbl" font-size="{L.fs(0.05)}" fill="{L.accent}"
        stroke="{L.bg}" stroke-width="{sw * 2}" paint-order="stroke">{E(v.get("decline", "No, thanks"))}</text></g>"""
    tw = [_ft(f"#{sid}-head", "y: 30, opacity: 0", 'y: 0, opacity: 1, duration: 0.6, ease: "back.out(1.6)"', 0.1),
          _ft(f"#{sid}-tag", "opacity: 0, rotation: -10", f'opacity: 1, rotation: 0, duration: 0.6, ease: "back.out(2)", svgOrigin: "{tx - tag_w / 2:.0f} {ty:.0f}"', 0.35),
          # euphoric
          _ft(f"#{sid}-calm", "opacity: 1", 'opacity: 0, duration: 0.15', t_hi),
          _ft(f"#{sid}-of", "opacity: 1", 'opacity: 0, duration: 0.15', t_hi),
          _show(f"#{sid}-grin", t_hi, 0.15), _show(f"#{sid}-ph", t_hi, 0.2), _show(f"#{sid}-mh", t_hi, 0.2),
          _ft(f"#{sid}-head", "rotation: 0, y: 0", f'rotation: -8, y: -16, duration: 0.4, ease: "back.out(2)", svgOrigin: "{cx:.0f} {cy + r:.0f}"', t_hi, later=True),
          # despairing
          _ft(f"#{sid}-grin", "opacity: 1", 'opacity: 0, duration: 0.15', t_lo, later=True),
          _ft(f"#{sid}-ph", "opacity: 1", 'opacity: 0, duration: 0.15', t_lo, later=True),
          _ft(f"#{sid}-mh", "opacity: 1", 'opacity: 0, duration: 0.15', t_lo, later=True),
          _show(f"#{sid}-frown", t_lo, 0.15), _show(f"#{sid}-pl", t_lo, 0.2), _show(f"#{sid}-ml", t_lo, 0.2),
          _ft(f"#{sid}-head", "rotation: -8, y: -16", f'rotation: 10, y: 22, duration: 0.6, ease: "power2.out", svgOrigin: "{cx:.0f} {cy + r:.0f}"', t_lo, later=True)]
    if t_no:
        tw += [_ft(f"#{sid}-tag", "opacity: 1", 'opacity: 0.25, duration: 0.3', t_no, later=True),
               _ft(f"#{sid}-no", "opacity: 0, scale: 1.6, rotation: -12", f'opacity: 1, scale: 1, rotation: -8, duration: 0.3, ease: "expo.out", svgOrigin: "{tx:.0f} {ty:.0f}"', t_no)]
    else:
        tw.append(_ft(f"#{sid}-no", "opacity: 0", "opacity: 0, duration: 0.01", 0))
    return svg, "", tw


def lock(L, sid, v, dur, cue):
    """Rules written in calm and locked in: the shackle snaps shut on `cue`; on `test_cue` a storm of price
    swings hits the card and it holds."""
    W, H = L.w, L.h
    sw = max(3, L.px(0.005))
    t_lock = cue(v.get("cue", ""), dur * 0.3)
    t_test = cue(v.get("test_cue", ""), dur * 0.8) if v.get("test_cue") else None
    items = v.get("items", [])[:3]
    cw, ch = W * 0.42, H * (0.13 + 0.1 * len(items))
    cx0, cy0 = W * 0.14, H * 0.2
    rows = []
    for i, it in enumerate(items):
        y = cy0 + H * 0.15 + i * H * 0.1
        text, icue = (it, None) if isinstance(it, str) else (it["text"], it.get("cue"))
        rows.append((f'<g id="{sid}-r{i}"><rect x="{cx0 + H * 0.04:.1f}" y="{y - H * 0.028:.1f}" width="{H * 0.034:.1f}" height="{H * 0.034:.1f}" '
                     f'fill="none" stroke="{L.accent}" stroke-width="{sw * 0.8:.1f}"/>'
                     f'<path id="{sid}-k{i}" d="M{cx0 + H * 0.047:.1f} {y - H * 0.012:.1f} l{H * 0.01:.1f} {H * 0.01:.1f} l{H * 0.02:.1f} {-H * 0.022:.1f}" '
                     f'stroke="{L.accent}" stroke-width="{sw:.0f}" fill="none" stroke-linecap="round" style="opacity:0"/>'
                     f'<text x="{cx0 + H * 0.1:.1f}" y="{y:.1f}" font-family="{L.sans}" font-size="{L.fs(0.03)}" fill="{L.ink}">{E(text)}</text></g>',
                     cue(icue, 0.6 + i * 0.5) if icue else 0.6 + i * 0.5))
    lx, ly = cx0 + cw + W * 0.17, cy0 + ch * 0.45
    lw, lh = H * 0.15, H * 0.12
    svg = f"""
      <g id="{sid}-card">
        <rect x="{cx0:.1f}" y="{cy0:.1f}" width="{cw:.1f}" height="{ch:.1f}" rx="{H * 0.012:.1f}" fill="{L.ink}" fill-opacity="0.06" stroke="{L.ink}" stroke-width="{sw}"/>
        <text x="{cx0 + H * 0.04:.1f}" y="{cy0 + H * 0.07:.1f}" class="lbl" font-size="{L.fs(0.026)}" fill="{L.muted}">{E(v.get("title", "My rules"))}</text>
        {''.join(r for r, _ in rows)}
      </g>
      <g id="{sid}-lock">
        <path id="{sid}-sh" d="M{lx - lw * 0.3:.1f} {ly:.1f} L{lx - lw * 0.3:.1f} {ly - lh * 0.55:.1f} A{lw * 0.3:.1f} {lw * 0.3:.1f} 0 0 1 {lx + lw * 0.3:.1f} {ly - lh * 0.55:.1f} L{lx + lw * 0.3:.1f} {ly:.1f}"
          fill="none" stroke="{L.ink}" stroke-width="{sw * 1.8:.0f}" stroke-linecap="round"/>
        <rect x="{lx - lw / 2:.1f}" y="{ly:.1f}" width="{lw:.1f}" height="{lh:.1f}" rx="{H * 0.012:.1f}" fill="{L.accent}"/>
        <circle cx="{lx:.1f}" cy="{ly + lh * 0.42:.1f}" r="{lh * 0.11:.1f}" fill="{L.bg}"/>
      </g>
      {_label(sid + "-cal", lx, ly + lh + L.fs(0.05), v.get("lock_label", "Decided in calm"), L, 0.026, L.accent)}"""
    tw = [_ft(f"#{sid}-card", "opacity: 0, y: 20", 'opacity: 1, y: 0, duration: 0.5, ease: "power3.out"', 0.1),
          _ft(f"#{sid}-lock", "opacity: 0", 'opacity: 1, duration: 0.4', 0.3),
          _ft(f"#{sid}-sh", "y: 0", f'y: {-lh * 0.45:.1f}, duration: 0.01', 0),
          _ft(f"#{sid}-sh", f"y: {-lh * 0.45:.1f}", 'y: 0, duration: 0.18, ease: "power4.in"', t_lock, later=True),
          _ft(f"#{sid}-lock", "x: 0", 'x: -6, duration: 0.05, repeat: 3, yoyo: true, ease: "none"', t_lock + 0.18),
          _show(f"#{sid}-cal", t_lock + 0.3)]
    for i, (_, at) in enumerate(rows):
        tw.append(_ft(f"#{sid}-r{i}", "opacity: 0, x: -14", 'opacity: 1, x: 0, duration: 0.4, ease: "power2.out"', at))
        tw.append(_ft(f"#{sid}-k{i}", "opacity: 0, scale: 0.3", 'opacity: 1, scale: 1, duration: 0.25, ease: "back.out(3)", transformOrigin: "30% 70%"', at + 0.35))
    if t_test:  # the frenzy: jagged price swings strike the card, which shakes and holds
        bolts = []
        for k in range(3):
            x = cx0 + cw * (0.25 + 0.3 * k)
            d = f"M{x:.0f} {cy0 - H * 0.1:.0f} l{-H * 0.025:.0f} {H * 0.045:.0f} l{H * 0.035:.0f} 0 l{-H * 0.025:.0f} {H * 0.05:.0f}"
            bolts.append(f'<path id="{sid}-z{k}" d="{d}" stroke="{L.accent}" stroke-width="{sw}" fill="none" stroke-linejoin="round" style="opacity:0"/>')
            tw.append(_ft(f"#{sid}-z{k}", "opacity: 0", 'opacity: 1, duration: 0.04', t_test + 0.12 * k))
            tw.append(_ft(f"#{sid}-z{k}", "opacity: 1", 'opacity: 0, duration: 0.3', t_test + 0.12 * k + 0.15, later=True))
        svg += "".join(bolts)
        tw.append(_ft(f"#{sid}-card", "x: 0", 'x: 8, duration: 0.05, repeat: 7, yoyo: true, ease: "none"', t_test))
    return svg, "", tw


def mirror(L, sid, v, dur, cue):
    """A person facing a mirror; on `cue` the reflection lights up: the risk was us. Optional `comet_cue`."""
    W, H = L.w, L.h
    gy = H * 0.665
    sw = max(3, L.px(0.005))
    mx, my, mrx, mry = W * 0.6, H * 0.4, H * 0.15, H * 0.26
    fh = H * 0.24
    t_us = cue(v.get("cue", ""), dur * 0.8)
    svg = f"""
      <line x1="{W * 0.12:.0f}" y1="{gy:.0f}" x2="{W * 0.88:.0f}" y2="{gy:.0f}" stroke="{L.muted}" stroke-width="2" opacity="0.6"/>
      <ellipse cx="{mx:.1f}" cy="{my:.1f}" rx="{mrx:.1f}" ry="{mry:.1f}" fill="{L.ink}" fill-opacity="0.05" stroke="{L.ink}" stroke-width="{sw * 1.6:.0f}"/>
      <line x1="{mx:.1f}" y1="{my + mry:.1f}" x2="{mx:.1f}" y2="{gy:.1f}" stroke="{L.ink}" stroke-width="{sw}"/>
      <line x1="{mx - H * 0.07:.1f}" y1="{gy:.1f}" x2="{mx + H * 0.07:.1f}" y2="{gy:.1f}" stroke="{L.ink}" stroke-width="{sw}"/>
      <g id="{sid}-me">{figure(f"{sid}-p", W * 0.33, gy, fh)}</g>
      <g id="{sid}-rf" style="opacity:0.45">{figure(f"{sid}-q", mx, my + mry * 0.8, fh * 0.62, "fig ghost")}</g>
      {_label(sid + "-us", mx, my - mry * 0.55, v.get("label", "The risk"), L, 0.03, L.accent)}"""
    tw = [_ft(f"#{sid}-me", "x: -40, opacity: 0", 'x: 0, opacity: 1, duration: 0.8, ease: "power2.out"', 0.1),
          _ft(f"#{sid}-rf", "opacity: 0", 'opacity: 0.45, duration: 0.8', 0.3),
          _ft(f"#{sid}-q", f'stroke: "{L.muted}", fill: "{L.muted}"', f'stroke: "{L.accent}", fill: "{L.accent}", duration: 0.3', t_us),
          _ft(f"#{sid}-rf", "opacity: 0.45", 'opacity: 1, duration: 0.3', t_us, later=True),
          _ft(f"#{sid}-us", "opacity: 0, y: 10", 'opacity: 1, y: 0, duration: 0.35, ease: "back.out(2)"', t_us + 0.1)]
    if v.get("comet_cue"):
        t_c = cue(v["comet_cue"], 0.8)
        svg += (f'<g id="{sid}-cm"><line x1="{W * 0.05:.0f}" y1="{H * 0.2:.0f}" x2="{W * 0.15:.0f}" y2="{H * 0.14:.0f}" stroke="{L.ink}" '
                f'stroke-opacity="0.5" stroke-width="2"/><circle cx="{W * 0.15:.0f}" cy="{H * 0.14:.0f}" r="{sw * 1.6}" fill="{L.ink}"/></g>')
        tw.append(_ft(f"#{sid}-cm", "x: 0, y: 0, opacity: 0", f'x: {W * 0.3:.0f}, y: {-H * 0.06:.0f}, opacity: 1, duration: 2.2, ease: "sine.out"', t_c))
        tw.append(_ft(f"#{sid}-cm", "opacity: 1", 'opacity: 0, duration: 0.5', t_c + 2.2, later=True))
    return svg, "", tw


KINDS = {"bubble": bubble, "crowd": crowd, "balance": balance, "ship": ship, "mood": mood, "lock": lock, "mirror": mirror}
