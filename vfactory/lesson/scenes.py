"""HyperFrames scene generators for lessons ("Ledger" look: brand accent on off-black, serif for history).

Every generator returns (markup, css, tweens) for one sub-composition. Rules kept (HyperFrames contract):
ids prefixed with the beat id; only children of the timed host are animated; transforms only through GSAP
`fromTo` (never CSS transform on a tweened element); later tweens on the same target use
`immediateRender: false`; everything is a pure function of timeline time (counters use a proxy tween).
Signalling (Mayer): one new element at a time, revealed on the word that introduces it.
"""

from __future__ import annotations

import html
import math
import re

E = html.escape

LABELS = {
    "en": {"think": "Pause and think", "answer": "Answer:", "next": "Next:", "attributed": "ATTRIBUTED · NOT VERIFIED",
           "done": "Lesson complete", "principle": "Principle", "locale": "en-US"},
    "vi": {"think": "Dừng lại và nghĩ", "answer": "Đáp án:", "next": "Tập sau:", "attributed": "ĐƯỢC CHO LÀ · CHƯA KIỂM CHỨNG",
           "done": "Hết bài", "principle": "Bài học", "locale": "vi-VN"},
}


class Look:
    def __init__(self, brand: dict, width: int, height: int, lang: str = "en"):
        self.w, self.h = width, height
        self.t = LABELS.get(lang, LABELS["en"])
        self.accent = brand.get("primary_color", "#FF4F00")
        self.bg = brand.get("secondary_color", "#0E0E0E")
        self.ink = brand.get("text_color", "#F2EDE4")
        self.muted = "#9A9388"
        self.sans = f"'{brand.get('font', 'Inter')}'"
        self.serif = "'EB Garamond'"
        self.u = min(width, height)  # layout unit

    def px(self, f: float) -> int:
        return int(round(self.u * f))

    def fs(self, f: float) -> int:
        """A font size: never under the 2.6%-of-short-side floor a phone can read (28 px at 1080)."""
        return max(int(round(self.u * 0.026)) + 1, self.px(f))


def _ft(sel: str, frm: str, to: str, at: float, later: bool = False) -> str:
    extra = ", immediateRender: false" if later else ""
    return f'tl.fromTo("{sel}", {{{frm}}}, {{{to}{extra}}}, {max(0.0, at):.3f});'


def _rise(sel, at, dur=0.6, dist=24, later=False):
    return _ft(sel, f"opacity: 0, y: {dist}", f'opacity: 1, y: 0, duration: {dur}, ease: "power3.out"', at, later)


def _fade(sel, at, dur=0.5):
    return _ft(sel, "opacity: 0", f'opacity: 1, duration: {dur}, ease: "power2.out"', at)


def _exit(sel, dur_scene, d=0.22):
    # a quick blur-swap exit; the next scene starts drawing almost at once, so cuts never leave a dead, empty frame
    return _ft(sel, 'opacity: 1, filter: "blur(0px)"', f'opacity: 0, filter: "blur(8px)", duration: {d}, ease: "power2.in"',
               dur_scene - d - 0.02, later=True)


def base_css(L: Look, sid: str) -> str:
    return f"""
    #root {{ position: absolute; inset: 0; }}
    #{sid}-wrap {{ position: absolute; left: 0; top: 0; width: {L.w}px; height: {L.h}px; color: {L.ink};
      font-family: {L.sans}; }}
    #{sid}-wrap .kicker {{ font-family: {L.sans}; font-weight: 700; font-size: {L.fs(0.022)}px; letter-spacing: 0.32em;
      text-transform: uppercase; color: {L.accent}; }}
    #{sid}-wrap .serif {{ font-family: {L.serif}; font-weight: 500; }}
    #{sid}-wrap .muted {{ color: {L.muted}; }}
    #{sid}-wrap .acc {{ color: {L.accent}; }}
    """


# ---------------------------------------------------------------- scene types

def title(L, sid, v, dur, cue):
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.1)}px;right:{L.px(0.1)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
      <div id="{sid}-k" class="kicker">{E(v.get('kicker', ''))}</div>
      <div id="{sid}-t" class="serif" style="font-size:{L.fs(0.105)}px;line-height:1.02;margin-top:{L.px(0.03)}px;">{E(v['title'])}</div>
      <div id="{sid}-r" style="width:{L.px(0.14)}px;height:{max(3, L.px(0.005))}px;background:{L.accent};margin:{L.px(0.035)}px 0;transform-origin:0 50%;"></div>
      <div id="{sid}-s" class="muted" style="font-size:{L.fs(0.034)}px;line-height:1.35;max-width:{L.px(1.0)}px;">{E(v.get('subtitle', ''))}</div></div>"""
    fast = 0.4 if v.get("hold") else 1.0  # a silent title sting lands at once, on its sound accent
    tw = [_fade(f"#{sid}-k", 0.05), _rise(f"#{sid}-t", 0.1, 0.9 * fast + 0.2, 30),
          _ft(f"#{sid}-r", "scaleX: 0", 'scaleX: 1, duration: 0.8, ease: "expo.out"', 0.6 * fast), _rise(f"#{sid}-s", 1.0 * fast)]
    return m, "", tw


def _phrase_at(words: list[str], phrase: str) -> int:
    pw = phrase.split()
    norm = lambda w: w.strip(".,;:!?…\"'“”").lower()  # noqa: E731
    for j in range(len(words) - len(pw) + 1):
        if [norm(w) for w in words[j:j + len(pw)]] == [norm(w) for w in pw]:
            return j
    return -1


def statement(L, sid, v, dur, cue):
    """The key phrase, word by word out of a blur (one of HyperFrames' title entrances). A highlight underlines on
    its cue word. A myth: `strike` names the wrong phrase, which is struck through on `strike_cue` while `replace`
    writes the correction over it."""
    words = v["text"].split()
    groups = {}  # start index -> (end index, kind, i, phrase)
    spans = []
    for i, h in enumerate(v.get("highlight") or []):
        j = _phrase_at(words, h)
        if j >= 0:
            groups[j] = (j + len(h.split()), "hl", i, h)
            spans.append((i, h))
    if v.get("strike"):
        j = _phrase_at(words, v["strike"])
        if j >= 0:
            groups[j] = (j + len(v["strike"].split()), "st", 0, v["strike"])
    out, k, wi = [], 0, 0
    while k < len(words):
        if k in groups:
            end, kind, i, _ = groups[k]
            inner = " ".join(f'<span id="{sid}-w{wi + n}" class="w">{E(w)}</span>' for n, w in enumerate(words[k:end]))
            wi += end - k
            if kind == "hl":
                out.append(f'<span id="{sid}-h{i}" class="hl">{inner}<span id="{sid}-u{i}" class="ul"></span></span>')
            else:
                out.append(f'<span id="{sid}-st" class="st">{inner}<span id="{sid}-sl" class="sl"></span>'
                           f'<span id="{sid}-rp" class="rp">{E(v.get("replace", ""))}</span></span>')
            k = end
        else:
            out.append(f'<span id="{sid}-w{wi}" class="w">{E(words[k])}</span>')
            wi += 1
            k += 1
    text = " ".join(out)
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.1)}px;right:{L.px(0.1)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
      {f'<div id="{sid}-k" class="kicker" style="margin-bottom:{L.px(0.03)}px">{E(v["kicker"])}</div>' if v.get('kicker') else ''}
      <div id="{sid}-t" class="serif" style="font-size:{L.fs(0.075)}px;line-height:1.18;">{text}</div></div>"""
    css = f"""#{sid}-wrap .hl {{ position: relative; color: {L.accent}; }}
    #{sid}-wrap .w {{ display: inline-block; }}
    #{sid}-wrap .ul {{ position: absolute; left: 0; right: 0; bottom: -{L.px(0.006)}px; height: {max(3, L.px(0.005))}px;
      background: {L.accent}; transform-origin: 0 50%; }}
    #{sid}-wrap .st {{ position: relative; display: inline-block; }}
    #{sid}-wrap .sl {{ position: absolute; left: -4%; right: -4%; top: 55%; height: {max(4, L.px(0.008))}px; background: #E77A5F;
      transform-origin: 0 50%; border-radius: 4px; }}
    #{sid}-wrap .rp {{ position: absolute; left: 0; top: 102%; white-space: nowrap; color: {L.accent}; font-style: italic;
      font-size: 0.8em; }}"""
    tw = ([_fade(f"#{sid}-k", 0.04)] if v.get("kicker") else [])
    for n in range(wi):  # per word: blur 6 px -> 0 and opacity 0 -> 1, ~0.09 s apart, no translate
        tw.append(_ft(f"#{sid}-w{n}", 'opacity: 0, filter: "blur(6px)"', 'opacity: 1, filter: "blur(0px)", duration: 0.2, ease: "power2.out"',
                      0.12 + 0.09 * n))
    for i, h in spans:
        tw.append(_ft(f"#{sid}-u{i}", "scaleX: 0", 'scaleX: 1, duration: 0.5, ease: "power3.out"', max(0.9, cue(h, 1.0 + i))))
    if v.get("strike") and f'id="{sid}-st"' in text:
        ts = max(1.0, cue(v.get("strike_cue", ""), dur * 0.6))
        tw.append(_ft(f"#{sid}-sl", "scaleX: 0", 'scaleX: 1, duration: 0.3, ease: "power3.out"', ts))
        tw.append(_ft(f"#{sid}-st .w", "opacity: 1", 'opacity: 0.4, duration: 0.3, ease: "power2.out"', ts + 0.15, later=True))
        tw.append(_ft(f"#{sid}-rp", 'opacity: 0, filter: "blur(8px)", y: 10', 'opacity: 1, filter: "blur(0px)", y: 0, duration: 0.4, ease: "expo.out"',
                      ts + 0.35))
    return m, css, tw


def _fmt_num(x: float, decimals: int, locale: str = "en-US") -> str:
    s = f"{x:,.{decimals}f}"
    if locale != "en-US":  # 1.435 / 6,9: dot groups thousands, comma marks decimals
        s = s.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return s


def stat(L, sid, v, dur, cue):
    to_v = float(v["value"])
    from_v = float(v.get("from", 0))
    dec = int(v.get("decimals", 0))
    pre, suf = E(v.get("prefix", "")), E(v.get("suffix", ""))
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">
      <div id="{sid}-l" class="kicker">{E(v['label'])}</div>
      <div id="{sid}-n" class="serif" style="font-size:{L.fs(0.22)}px;line-height:1;margin:{L.px(0.03)}px 0;font-variant-numeric:tabular-nums;">{pre}<span id="{sid}-v">{_fmt_num(from_v, dec, L.t['locale'])}</span>{suf}</div>
      <div id="{sid}-no" class="muted" style="font-size:{L.fs(0.034)}px;max-width:{L.px(1.0)}px;">{E(v.get('note', ''))}</div></div>"""
    t0 = cue(v.get("cue", ""), 0.6) if v.get("cue") else 0.6
    count = min(2.6, max(1.2, dur * 0.45))
    tw = [_fade(f"#{sid}-l", 0.1), _rise(f"#{sid}-n", 0.3, 0.7, 30),
          f'const {sid}P = {{ v: {from_v} }};',
          f'tl.fromTo({sid}P, {{ v: {from_v} }}, {{ v: {to_v}, duration: {count:.2f}, ease: "power2.out", '
          f'onUpdate: () => {{ document.getElementById("{sid}-v").textContent = {sid}P.v.toLocaleString("{L.t['locale']}", '
          f'{{minimumFractionDigits: {dec}, maximumFractionDigits: {dec}}}); }} }}, {t0:.3f});',
          _rise(f"#{sid}-no", t0 + count * 0.7)]
    return m, "", tw


def chart(L, sid, v, dur, cue):
    pts = v["points"]  # [[label, value], ...]
    W, H = L.w * 0.78, L.h * 0.52
    x0, y0 = (L.w - W) / 2, L.h * 0.27
    vals = [float(p[1]) for p in pts]
    raw_step = max(vals) / 4
    mag = 10 ** math.floor(math.log10(raw_step))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw_step), default=raw_step)
    n_ticks = math.ceil(max(vals) * 1.05 / step)
    vmax = step * n_ticks
    vmin = 0.0
    xs = [x0 + W * i / (len(pts) - 1) for i in range(len(pts))]
    ys = [y0 + H - H * (val - vmin) / (vmax - vmin) for val in vals]
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in zip(xs, ys))
    length = sum(math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(len(xs) - 1)) + 10
    area = path + f" L {xs[-1]:.1f} {y0 + H:.1f} L {xs[0]:.1f} {y0 + H:.1f} Z"
    grid = []
    for g in range(n_ticks + 1):
        gv = step * g
        gy = y0 + H - H * g / n_ticks
        grid.append(f'<line x1="{x0:.0f}" y1="{gy:.1f}" x2="{x0 + W:.0f}" y2="{gy:.1f}" stroke="{L.muted}" stroke-opacity="0.25" stroke-width="1"/>'
                    f'<text x="{x0 - 14:.0f}" y="{gy + 6:.1f}" text-anchor="end" fill="{L.muted}" font-family="Inter" font-size="{L.fs(0.02)}">'
                    f'{E(v.get("unit", ""))}{gv:,.0f}</text>')
    labels = []
    step = max(1, len(pts) // 6)
    for i in range(0, len(pts), step):
        labels.append(f'<text x="{xs[i]:.1f}" y="{y0 + H + L.px(0.04):.1f}" text-anchor="middle" fill="{L.muted}" '
                      f'font-family="Inter" font-size="{L.fs(0.02)}">{E(str(pts[i][0]))}</text>')
    draw_t0 = 0.5
    draw_d = max(1.5, dur * 0.62)
    ann, tw = [], []
    for j, a in enumerate(v.get("annotations", [])):
        i = int(a["at"])
        ax, ay = xs[i], ys[i]
        default_t = draw_t0 + draw_d * i / max(1, len(pts) - 1)
        at = max(default_t, cue(a["cue"], default_t)) if a.get("cue") else default_t
        above = ay - L.px(0.08) > y0 - L.px(0.05)
        ly = ay - L.px(0.05) if above else ay + L.px(0.07)
        anchor = "end" if ax > x0 + W * 0.75 else ("start" if ax < x0 + W * 0.25 else "middle")
        ann.append(f'<g id="{sid}-a{j}"><circle cx="{ax:.1f}" cy="{ay:.1f}" r="{L.px(0.011)}" fill="{L.accent}"/>'
                   f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{ax:.1f}" y2="{ly + (8 if above else -L.px(0.03)):.1f}" stroke="{L.accent}" stroke-width="2"/>'
                   f'<text x="{ax + (16 if anchor == "start" else -16 if anchor == "end" else 0):.1f}" y="{ly:.1f}" text-anchor="{anchor}" fill="{L.ink}" font-family="Inter" font-weight="700" '
                   f'font-size="{L.fs(0.024)}">{E(a["text"])}</text></g>')
        tw.append(_ft(f"#{sid}-a{j}", "opacity: 0, y: 8", 'opacity: 1, y: 0, duration: 0.45, ease: "back.out(2)"', at))
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">
      <div id="{sid}-ti" class="kicker" style="position:absolute;left:{x0:.0f}px;top:{L.h * 0.13:.0f}px;">{E(v.get('title', ''))}</div>
      <svg id="{sid}-svg" width="{L.w}" height="{L.h}" viewBox="0 0 {L.w} {L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <g id="{sid}-grid">{''.join(grid)}{''.join(labels)}</g>
        <path id="{sid}-area" d="{area}" fill="{L.accent}" fill-opacity="0.10"/>
        <path id="{sid}-line" d="{path}" fill="none" stroke="{L.ink}" stroke-width="{max(3, L.px(0.005))}" stroke-linejoin="round"
          stroke-linecap="round" stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}"/>
        {''.join(ann)}
      </svg></div>"""
    tw = [_fade(f"#{sid}-ti", 0.1), _fade(f"#{sid}-grid", 0.2, 0.6),
          _ft(f"#{sid}-line", f"strokeDashoffset: {length:.0f}", f'strokeDashoffset: 0, duration: {draw_d:.2f}, ease: "power1.inOut"', draw_t0),
          _ft(f"#{sid}-area", "opacity: 0", 'opacity: 1, duration: 0.8, ease: "power2.out"', draw_t0 + draw_d * 0.8)] + tw
    return m, "", tw


def timeline(L, sid, v, dur, cue):
    ev = v["events"]
    n = len(ev)
    x0, x1, y = L.w * 0.1, L.w * 0.9, L.h * 0.52
    items, tw = [], [_fade(f"#{sid}-ti", 0.1),
                     _ft(f"#{sid}-ln", "scaleX: 0", f'scaleX: 1, duration: {min(1.4, dur * 0.3):.2f}, ease: "power2.inOut"', 0.3)]
    for i, e in enumerate(ev):
        inset = (x1 - x0) * 0.12
        x = x0 + inset + (x1 - x0 - 2 * inset) * (i / max(1, n - 1) if n > 1 else 0.5)
        up = i % 2 == 0
        default_t = 0.8 + (dur - 1.8) * i / max(1, n)
        at = max(default_t * 0.6, cue(e.get("cue", ""), default_t)) if e.get("cue") else default_t
        items.append(f"""<div id="{sid}-e{i}" style="position:absolute;left:{x - L.px(0.13):.0f}px;width:{L.px(0.26)}px;
          top:{(y - L.px(0.21)) if up else (y + L.px(0.035)):.0f}px;text-align:center;">
          <div class="serif acc" style="font-size:{L.fs(0.05)}px">{E(str(e['year']))}</div>
          <div style="font-size:{L.fs(0.024)}px;line-height:1.3;margin-top:6px">{E(e['text'])}</div></div>
          <div id="{sid}-d{i}" style="position:absolute;left:{x - L.px(0.011):.0f}px;top:{y - L.px(0.011):.0f}px;width:{L.px(0.022)}px;
          height:{L.px(0.022)}px;border-radius:50%;background:{L.accent};"></div>""")
        tw.append(_ft(f"#{sid}-d{i}", "scale: 0", 'scale: 1, duration: 0.35, ease: "back.out(3)"', at))
        tw.append(_rise(f"#{sid}-e{i}", at + 0.1, 0.5, 14 if up else -14))
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">
      <div id="{sid}-ti" class="kicker" style="position:absolute;left:{x0:.0f}px;top:{L.h * 0.14:.0f}px;">{E(v.get('title', ''))}</div>
      <div id="{sid}-ln" style="position:absolute;left:{x0:.0f}px;top:{y - 1:.0f}px;width:{x1 - x0:.0f}px;height:3px;background:{L.muted};transform-origin:0 50%;"></div>
      {''.join(items)}</div>"""
    return m, "", tw


def quote(L, sid, v, dur, cue):
    attributed = v.get("attribution") in ("attributed", "disputed", "apocryphal")
    badge = ""
    if attributed:
        badge = (f'<div id="{sid}-b" style="display:inline-block;margin-top:{L.px(0.03)}px;padding:6px 14px;border:2px solid {L.accent};'
                 f'color:{L.accent};font-weight:700;font-size:{L.fs(0.019)}px;letter-spacing:0.2em;">{E(L.t['attributed'])}</div>')
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.12)}px;right:{L.px(0.12)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
      <div id="{sid}-q" class="serif acc" style="font-size:{L.fs(0.2)}px;line-height:0.6;height:{L.px(0.09)}px;">&ldquo;</div>
      <div id="{sid}-t" class="serif" style="font-size:{L.fs(0.062)}px;line-height:1.22;font-style:italic;">{E(v['text'])}</div>
      <div id="{sid}-by" style="margin-top:{L.px(0.035)}px;font-size:{L.fs(0.028)}px;font-weight:700;">— {E(v['by'])}{(', ' + E(str(v['year']))) if v.get('year') else ''}</div>
      <div>{badge}</div></div>"""
    tw = [_fade(f"#{sid}-q", 0.15), _rise(f"#{sid}-t", 0.35, 0.9), _rise(f"#{sid}-by", 1.2)]
    if attributed:
        tw.append(_ft(f"#{sid}-b", "opacity: 0, scale: 1.3", 'opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)"',
                      max(1.8, cue(v.get("badge_cue", "attributed"), 1.8))))
    return m, "", tw


def portrait(L, sid, v, dur, cue):
    """No faked likenesses: an engraved medallion with initials stands in for the person."""
    r = L.px(0.17)
    cx, cy = L.w * 0.25, L.h * 0.5
    initials = E(v.get("initials") or "".join(p[0] for p in v["name"].split()[:2]).upper())
    hatch = "".join(f'<line x1="{-r + i * 9}" y1="{-r}" x2="{-r + i * 9 - r}" y2="{r}" stroke="{L.ink}" stroke-opacity="0.13" stroke-width="1.5"/>'
                    for i in range(0, int(4 * r / 9)))
    circ = 2 * math.pi * (r - 6)
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <defs><clipPath id="{sid}-clip"><circle cx="0" cy="0" r="{r - 10}"/></clipPath></defs>
        <g transform="translate({cx:.0f},{cy:.0f})">
          <g id="{sid}-h" clip-path="url(#{sid}-clip)">{hatch}</g>
          <circle id="{sid}-ring" cx="0" cy="0" r="{r - 6}" fill="none" stroke="{L.accent}" stroke-width="4"
            stroke-dasharray="{circ:.0f}" stroke-dashoffset="{circ:.0f}"/>
          <text id="{sid}-i" x="0" y="{r * 0.18:.0f}" text-anchor="middle" font-family="EB Garamond" font-size="{r * 0.62:.0f}" fill="{L.ink}">{initials}</text>
        </g></svg>
      <div id="{sid}-txt" style="position:absolute;left:{cx + r + L.px(0.06):.0f}px;right:{L.px(0.06)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
        <div id="{sid}-ro" class="kicker" style="letter-spacing:0.18em">{E(v.get('role', ''))}</div>
        <div id="{sid}-n" class="serif" style="font-size:{L.fs(0.085)}px;line-height:1.05;margin:{L.px(0.02)}px 0;">{E(v['name'])}</div>
        <div id="{sid}-y" class="muted" style="font-size:{L.fs(0.032)}px;">{E(v.get('years', ''))}</div></div></div>"""
    tw = [_ft(f"#{sid}-ring", f"strokeDashoffset: {circ:.0f}", 'strokeDashoffset: 0, duration: 1.4, ease: "power2.inOut"', 0.2),
          _fade(f"#{sid}-h", 0.6, 1.0), _rise(f"#{sid}-i", 0.9, 0.8, 18), _fade(f"#{sid}-ro", 0.6),
          _rise(f"#{sid}-n", 0.8, 0.8), _rise(f"#{sid}-y", 1.2)]
    return m, "", tw


def principle(L, sid, v, dur, cue):
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.1)}px;right:{L.px(0.1)}px;top:0;bottom:0;display:flex;align-items:center;gap:{L.px(0.06)}px;">
      <div id="{sid}-num" class="serif" style="font-size:{L.fs(0.34)}px;line-height:1;color:#2A1A10;-webkit-text-stroke:2px {L.accent};">{int(v['n']):02d}</div>
      <div><div id="{sid}-k" class="kicker">{E(L.t['principle'])} {int(v['n'])}</div>
        <div id="{sid}-nm" class="serif" style="font-size:{L.fs(0.08)}px;line-height:1.08;margin:{L.px(0.02)}px 0;">{E(v['name'])}</div>
        <div id="{sid}-ln" class="muted" style="font-size:{L.fs(0.032)}px;line-height:1.4;">{E(v.get('line', ''))}</div></div></div>"""
    tw = [_ft(f"#{sid}-num", "opacity: 0, x: -30", 'opacity: 1, x: 0, duration: 0.8, ease: "expo.out"', 0.2),
          _fade(f"#{sid}-k", 0.5), _rise(f"#{sid}-nm", 0.7, 0.8), _rise(f"#{sid}-ln", max(1.4, cue(v.get("line_cue", ""), 1.4)))]
    return m, "", tw


def compare(L, sid, v, dur, cue):
    left, right = v["left"], v["right"]
    n = max(len(left.get("items", [])), len(right.get("items", [])))

    def col(side, data, x):
        rows = "".join(f'<div id="{sid}-{side}{i}" style="font-size:{L.fs(0.03)}px;line-height:1.35;margin-top:{L.px(0.022)}px;">{E(t)}</div>'
                       for i, t in enumerate(data.get("items", [])))
        color = L.accent if side == "r" else L.muted
        return (f'<div style="position:absolute;left:{x}px;width:{L.w * 0.36:.0f}px;top:{L.h * 0.29:.0f}px;">'
                f'<div id="{sid}-{side}h" class="kicker" style="color:{color}">{E(data["title"])}</div>{rows}</div>')

    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">
      {f'<div id="{sid}-ti" class="serif" style="position:absolute;left:{L.w * 0.1:.0f}px;top:{L.h * 0.14:.0f}px;font-size:{L.fs(0.055)}px;">{E(v["title"])}</div>' if v.get('title') else ''}
      {col('l', left, int(L.w * 0.1))}
      <div id="{sid}-div" style="position:absolute;left:{L.w * 0.5 - 1:.0f}px;top:{L.h * 0.29:.0f}px;width:2px;height:{L.h * 0.55:.0f}px;background:{L.muted};opacity:0.4;transform-origin:50% 0;"></div>
      {col('r', right, int(L.w * 0.54))}</div>"""
    tw = ([_fade(f"#{sid}-ti", 0.1)] if v.get("title") else []) + [
        _fade(f"#{sid}-lh", 0.3), _fade(f"#{sid}-rh", 0.5),
        _ft(f"#{sid}-div", "scaleY: 0", 'scaleY: 1, duration: 0.8, ease: "power2.out"', 0.4)]
    span = max(1.0, dur - 2.2)
    k = 0
    for i in range(n):
        for side, data in (("l", left), ("r", right)):
            if i < len(data.get("items", [])):
                tw.append(_rise(f"#{sid}-{side}{i}", 1.0 + span * k / max(1, 2 * n), 0.45, 12))
                k += 1
    return m, "", tw


def list_(L, sid, v, dur, cue):
    items = [x if isinstance(x, str) else x["text"] for x in v["items"]]
    rows = "".join(f'<div id="{sid}-i{i}" style="display:flex;align-items:center;gap:{L.px(0.025)}px;margin-top:{L.px(0.03)}px;">'
                   f'<svg width="{L.px(0.05)}" height="{L.px(0.05)}" viewBox="0 0 40 40"><circle cx="20" cy="20" r="18" fill="none" stroke="{L.accent}" stroke-width="3"/>'
                   f'<path id="{sid}-ck{i}" d="M11 21 L18 28 L30 13" fill="none" stroke="{L.accent}" stroke-width="4" stroke-linecap="round" '
                   f'stroke-dasharray="30" stroke-dashoffset="30"/></svg>'
                   f'<div class="serif" style="font-size:{L.fs(0.05)}px;line-height:1.15;">{E(t)}</div></div>' for i, t in enumerate(items))
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.12)}px;right:{L.px(0.1)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
      <div id="{sid}-ti" class="kicker">{E(v.get('title', ''))}</div>{rows}</div>"""
    tw = [_fade(f"#{sid}-ti", 0.1)]
    span = max(1.2, dur - 1.8)
    for i, it in enumerate(v["items"]):
        default_t = 0.6 + span * i / max(1, len(items))
        at = max(0.4, cue(it.get("cue", ""), default_t)) if isinstance(it, dict) and it.get("cue") else default_t
        tw.append(_rise(f"#{sid}-i{i}", at, 0.5, 16))
        tw.append(_ft(f"#{sid}-ck{i}", "strokeDashoffset: 30", 'strokeDashoffset: 0, duration: 0.4, ease: "power2.out"', at + 0.25))
    return m, "", tw


def question(L, sid, v, dur, cue, narr: float = 0.0):
    think = float(v.get("think_seconds", 4.0))
    choices = v.get("choices") or []
    ch = "".join(f'<div id="{sid}-o{i}" style="font-size:{L.fs(0.034)}px;margin-top:{L.px(0.02)}px;padding:{L.px(0.012)}px {L.px(0.025)}px;'
                 f'border:2px solid {L.muted};border-radius:10px;"><b class="acc">{chr(65 + i)}</b>&nbsp;&nbsp;{E(c)}</div>'
                 for i, c in enumerate(choices))
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.12)}px;right:{L.px(0.12)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
      <div id="{sid}-k" class="kicker">{E(L.t['think'])}</div>
      <div id="{sid}-q" class="serif" style="font-size:{L.fs(0.064)}px;line-height:1.18;margin:{L.px(0.03)}px 0;">{E(v['question'])}</div>
      {ch}
      <div style="margin-top:{L.px(0.045)}px;height:6px;background:rgba(255,255,255,0.12);border-radius:3px;">
        <div id="{sid}-bar" style="height:6px;width:100%;background:{L.accent};border-radius:3px;transform-origin:0 50%;"></div></div>
      {f'<div id="{sid}-a" style="margin-top:{L.px(0.03)}px;font-size:{L.fs(0.034)}px;font-weight:700;"><span class="acc">{E(L.t['answer'])}</span> {E(v["answer"])}</div>' if v.get('answer') else ''}
      </div>"""
    t_think = narr + 0.2
    tw = [_fade(f"#{sid}-k", 0.1), _rise(f"#{sid}-q", 0.3, 0.8)]
    for i in range(len(choices)):
        tw.append(_rise(f"#{sid}-o{i}", 0.9 + 0.35 * i, 0.45, 12))
    tw.append(_ft(f"#{sid}-bar", "scaleX: 1", f'scaleX: 0, duration: {think:.2f}, ease: "none"', t_think))
    if v.get("answer"):
        tw.append(_rise(f"#{sid}-a", t_think + think + 0.1, 0.5, 12))
    return m, "", tw


def _ask_bubble(L, sid, v) -> str:
    dot = "".join(f'<span id="{sid}-d{k}" style="display:inline-block;width:{L.px(0.014)}px;height:{L.px(0.014)}px;border-radius:50%;'
                  f'background:{L.ink};margin-right:{L.px(0.01)}px;opacity:0.25;"></span>' for k in range(3))
    return (f'<div id="{sid}-ab" style="position:relative;align-self:flex-start;max-width:{L.px(1.0)}px;margin-top:{L.px(0.03)}px;'
            f'padding:{L.px(0.025)}px {L.px(0.035)}px;border-radius:{L.px(0.03)}px {L.px(0.03)}px {L.px(0.03)}px 6px;'
            f'background:rgba(255,255,255,0.07);border:2px solid {L.accent}88;">'
            f'<div id="{sid}-dots" style="position:absolute;left:{L.px(0.035)}px;top:{L.px(0.035)}px;">{dot}</div>'
            f'<div id="{sid}-aq" class="serif" style="font-size:{L.fs(0.045)}px;line-height:1.2;">{E(v["ask"])}</div>'
            + (f'<div id="{sid}-ah" class="muted" style="font-size:{L.fs(0.024)}px;margin-top:{L.px(0.012)}px;">{E(v["ask_hint"])}</div>'
               if v.get("ask_hint") else "") + '</div>')


def end(L, sid, v, dur, cue):
    m = f"""<div id="{sid}-c" style="position:absolute;left:{L.px(0.1)}px;right:{L.px(0.1)}px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;">
      <div id="{sid}-k" class="kicker">{E(v.get('kicker', L.t['done']))}</div>
      <div id="{sid}-t" class="serif" style="font-size:{L.fs(0.085)}px;line-height:1.08;margin:{L.px(0.025)}px 0;">{E(v['title'])}</div>
      {f'<div id="{sid}-n" style="font-size:{L.fs(0.032)}px;"><span class="muted">{E(L.t['next'])}</span> {E(v["next"])}</div>' if v.get('next') else ''}
      {_ask_bubble(L, sid, v) if v.get('ask') else ''}
      {f'<div id="{sid}-cta" style="display:inline-block;align-self:flex-start;margin-top:{L.px(0.035)}px;padding:{L.px(0.014)}px {L.px(0.03)}px;background:{L.accent};color:#0B0B0B;font-weight:800;font-size:{L.fs(0.028)}px;border-radius:999px;">{E(v["cta"])}</div>' if v.get('cta') else ''}
      <div id="{sid}-src" class="muted" style="position:absolute;left:0;right:0;bottom:{L.px(0.09)}px;font-size:{L.fs(0.019)}px;line-height:1.45;">
        {E(v.get('sources_line', ''))}<br/>{E(v.get('disclaimer', ''))}</div></div>"""
    tw = [_fade(f"#{sid}-k", 0.1), _rise(f"#{sid}-t", 0.3, 0.8)]
    t_next = max(0.9, cue(v.get("next_cue", ""), 0.9))
    t_cta = max(t_next + 0.5, cue(v.get("cta_cue", ""), 1.3))
    if v.get("next"):
        tw.append(_rise(f"#{sid}-n", t_next))
    if v.get("ask"):  # the viewer is asked, not told: typing dots, then the question lands in a comment bubble
        t_ask = max(0.8, cue(v.get("ask_cue", ""), 0.9))
        tw.append(_ft(f"#{sid}-ab", "opacity: 0, y: 24, scale: 0.92", 'opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(1.6)"', t_ask))
        for k in range(3):
            tw.append(_ft(f"#{sid}-d{k}", "opacity: 0.25", 'opacity: 1, duration: 0.18, ease: "power1.inOut"', t_ask + 0.25 + 0.12 * k))
            tw.append(_ft(f"#{sid}-d{k}", "opacity: 1", 'opacity: 0.25, duration: 0.18, ease: "power1.inOut"', t_ask + 0.43 + 0.12 * k, later=True))
        tw.append(_ft(f"#{sid}-dots", "opacity: 1", 'opacity: 0, duration: 0.15, ease: "power2.in"', t_ask + 0.9, later=True))
        tw.append(_ft(f"#{sid}-aq", 'opacity: 0, filter: "blur(6px)"', 'opacity: 1, filter: "blur(0px)", duration: 0.35, ease: "power2.out"', t_ask + 1.0))
        if v.get("ask_hint"):
            tw.append(_fade(f"#{sid}-ah", t_ask + 1.8, 0.5))
    if v.get("cta"):
        tw.append(_ft(f"#{sid}-cta", "opacity: 0, scale: 0.85", 'opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)"', t_cta))
    tw.append(_fade(f"#{sid}-src", max(1.6, cue(v.get("sources_cue", ""), t_cta + 1.5)), 0.8))
    return m, "", tw


def hook(L, sid, v, dur, cue):
    """The first five seconds. Frame 0 is already a composed claim over the data (it is the thumbnail).
    On the cue word the line crashes: flash, shake, and the second line slams in, all on the same beat
    as the narration and the sound hit (spoken, visual and on-screen text carry one hook).
    `split` (default: the peak) is the point where the accent segment starts, so a breakout (flat, then a climb)
    uses the same beat: the climb is the accent line and `peak_label` marks the turning point."""
    pts = v.get("points") or [[i, x] for i, x in enumerate([128, 170, 330, 340, 550, 1000, 950, 800, 300, 210, 200, 185])]
    vals = [float(p[1]) for p in pts]
    breakout = "split" in v  # the label sits left of the turning point, clear of the climbing line
    peak = int(v.get("split", vals.index(max(vals))))
    W, H = L.w * 0.86, L.h * 0.46
    x0, y0 = L.w * 0.07, L.h * 0.47  # below the two-line headline
    xs = [x0 + W * i / (len(vals) - 1) for i in range(len(vals))]
    ys = [y0 + H - H * val / (max(vals) * 1.08) for val in vals]

    def path(a, b):
        return "M " + " L ".join(f"{xs[i]:.1f} {ys[i]:.1f}" for i in range(a, b + 1))

    def plen(a, b):
        return sum(math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(a, b)) + 8

    up_len, down_len = plen(0, peak), plen(peak, len(vals) - 1)
    # the impact (flash, slam, sound hit) lands ON the cue word; the fall starts just before it
    t_crash = max(0.9, cue(v.get("crash_cue", ""), dur * 0.55) - 0.45)
    lines = v["lines"]
    m = f"""<div id="{sid}-c" style="position:absolute;inset:0;">
      <svg width="{L.w}" height="{L.h}" style="position:absolute;left:0;top:0;overflow:visible">
        <path id="{sid}-up" d="{path(0, peak)}" fill="none" stroke="{L.ink}" stroke-opacity="0.8" stroke-width="{max(5, L.px(0.008))}"
          stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{up_len:.0f}" stroke-dashoffset="{up_len * 0.12:.0f}"/>
        <path id="{sid}-down" d="{path(peak, len(vals) - 1)}" fill="none" stroke="{L.accent}" stroke-width="{max(6, L.px(0.01))}"
          stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{down_len:.0f}" stroke-dashoffset="{down_len:.0f}"/>
        <circle id="{sid}-pk" cx="{xs[peak]:.1f}" cy="{ys[peak]:.1f}" r="{L.px(0.013)}" fill="{L.ink}" opacity="0"/>
        <text id="{sid}-pkl" x="{xs[peak] - (L.px(0.02) if breakout else 0):.1f}" y="{ys[peak] - L.px(0.035):.1f}" text-anchor="{'end' if breakout else 'middle'}" fill="{L.ink}" font-family="Inter"
          font-weight="700" font-size="{L.fs(0.03)}">{E(v.get('peak_label', ''))}</text>
        <text id="{sid}-endl" x="{xs[-1]:.1f}" y="{ys[-1] - L.px(0.035):.1f}" text-anchor="end" fill="{L.accent}" font-family="Inter"
          font-weight="800" font-size="{L.fs(0.034)}">{E(v.get('end_label', ''))}</text>
      </svg>
      <div id="{sid}-t" style="position:absolute;left:{L.px(0.08)}px;right:{L.px(0.06)}px;top:{L.h * 0.08:.0f}px;">
        <div id="{sid}-k" class="kicker" style="margin-bottom:{L.px(0.02)}px">{E(v.get('kicker', ''))}</div>
        <div id="{sid}-l1" class="serif" style="font-size:{L.fs(0.12)}px;line-height:1.02;">{E(lines[0])}</div>
        <div id="{sid}-l2" class="serif acc" style="font-size:{L.fs(0.12)}px;line-height:1.02;text-wrap:balance;margin-top:{L.px(0.01)}px;">{E(lines[1]) if len(lines) > 1 else ''}</div>
      </div>
      <div id="{sid}-flash" data-layout-ignore style="position:absolute;inset:0;background:{L.accent};opacity:0;"></div>
    </div>"""
    tw = [
        # frame 0: line 1 and part of the rising curve are already there; the rise keeps moving
        _ft(f"#{sid}-up", f"strokeDashoffset: {up_len * 0.12:.0f}", f'strokeDashoffset: 0, duration: {max(0.8, t_crash - 0.3):.2f}, ease: "power2.in"', 0),
        _ft(f"#{sid}-pkl", "opacity: 0", 'opacity: 1, duration: 0.25, ease: "power2.out"', max(0.6, t_crash - 0.3)),
        _ft(f"#{sid}-pk", "opacity: 0", 'opacity: 1, duration: 0.15, ease: "power2.out"', max(0.6, t_crash - 0.3)),
        # the crash
        _ft(f"#{sid}-down", f"strokeDashoffset: {down_len:.0f}", 'strokeDashoffset: 0, duration: 0.55, ease: "power4.in"', t_crash),
        _ft(f"#{sid}-flash", "opacity: 0", 'opacity: 0.28, duration: 0.06, ease: "none"', t_crash + 0.5),
        _ft(f"#{sid}-flash", "opacity: 0.28", 'opacity: 0, duration: 0.45, ease: "power2.out"', t_crash + 0.56, later=True),
        _ft(f"#{sid}-t", "x: 0", 'x: -14, duration: 0.05, ease: "none"', t_crash + 0.5),
        _ft(f"#{sid}-t", "x: -14", 'x: 9, duration: 0.07, ease: "none"', t_crash + 0.55, later=True),
        _ft(f"#{sid}-t", "x: 9", 'x: 0, duration: 0.25, ease: "elastic.out(1, 0.4)"', t_crash + 0.62, later=True),
        _ft(f"#{sid}-l2", "opacity: 0, scale: 1.35", 'opacity: 1, scale: 1, duration: 0.35, ease: "expo.out"', t_crash + 0.45),
        _ft(f"#{sid}-endl", "opacity: 0, y: -10", 'opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)"', t_crash + 0.6),
    ]
    css = f"#{sid}-l2 {{ transform-origin: 0 60%; }}"
    return m, css, tw


GENERATORS = {"hook": hook, "title": title, "statement": statement, "stat": stat, "chart": chart, "timeline": timeline, "quote": quote,
              "portrait": portrait, "principle": principle, "compare": compare, "list": list_, "question": question, "end": end}


from . import metaphors  # noqa: E402,F401  (builds on the helpers above and registers itself in GENERATORS)


_AT = re.compile(r", (-?\d+(?:\.\d+)?)\);$")


def _shift(tween: str, by: float) -> str:
    """Move a tl.fromTo line later on the timeline (its position is the last argument)."""
    if not tween.startswith("tl.fromTo"):
        return tween
    return _AT.sub(lambda m: f", {float(m.group(1)) + by:.3f});", tween)


def shots(L, sid, v, dur, cue):
    """Several pictures for one spoken line: each shot is any visual type, enters on its cue word (blur swap) and
    gives way to the next. Keeps a new picture on screen every few seconds while the voice runs on (a narrated
    explainer holds one framing for ~19 spoken words, and something inside it moves every 2-3 s)."""
    items = v["shots"]
    n = len(items)
    starts = [0.0]
    for i, sh in enumerate(items[1:], 1):
        default = dur * i / n
        starts.append(max(starts[-1] + 1.5, min(dur - 1.5, cue(sh.get("cue", ""), default) if sh.get("cue") else default)))
    ends = starts[1:] + [dur]
    m, css, tw = [], [], []
    for i, (sh, t0, t1) in enumerate(zip(items, starts, ends)):
        ssid = f"{sid}s{i}"
        local = (lambda w, d, t0=t0: (cue(w, d + t0) - t0) if w else d)
        gm, gcss, gtw = GENERATORS[sh["type"]](L, ssid, sh, t1 - t0, local)
        m.append(f'<div id="{ssid}-shot" style="position:absolute;inset:0;"><div id="{ssid}-wrap" style="position:absolute;inset:0;">{gm}</div></div>')
        css.append(gcss)
        tw += [_shift(t, t0) for t in gtw]
        if i:
            tw.append(_ft(f"#{ssid}-shot", 'opacity: 0, filter: "blur(8px)"', 'opacity: 1, filter: "blur(0px)", duration: 0.25, ease: "power2.out"', t0))
        if i < n - 1:
            tw.append(_ft(f"#{ssid}-shot", 'opacity: 1, filter: "blur(0px)"', 'opacity: 0, filter: "blur(8px)", duration: 0.2, ease: "power2.in"',
                          t1 - 0.05, later=True))
    return f'<div id="{sid}-c" style="position:absolute;inset:0;">{"".join(m)}</div>', "\n".join(css), tw


GENERATORS["shots"] = shots


def scene_file(L: Look, sid: str, visual: dict, dur: float, cue, narr: float, last: bool) -> str:
    gen = GENERATORS[visual["type"]]
    if visual["type"] == "question":
        markup, css, tweens = gen(L, sid, visual, dur, cue, narr)
    else:
        markup, css, tweens = gen(L, sid, visual, dur, cue)
    if not last:
        tweens.append(_exit(f"#{sid}-c", dur))
    return f"""<template>
  <style>
    {base_css(L, sid)}
    {css}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="{L.w}" data-height="{L.h}">
    <div id="{sid}-wrap">{markup}</div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + t for t in tweens)}
    window.__timelines["{sid}"] = tl;
  </script>
</template>
"""
