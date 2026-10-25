"""Stage scenes: picture-book worlds where characters and objects act out the idea on the spoken word.

Made for a four-year-old's eye: one bright world, two to six big familiar pictures (Fluent Emoji 3D, see
assets.py), each doing one clear thing - it pops in, grows, bursts, walks, falls, changes face, says two words in
a speech bubble. The key phrase sits under the picture as the caption.

visual = {"type": "stage", "world": "meadow|sky|sea|room|night|plain", "caption": "...", "kicker": "...",
          "actors": [{"id": "n", "asset": "Man scientist", "x": 0.3, "y": 0.68, "size": 0.3, "label": "Newton",
                      "enter": "pop|drop|rise|slide-left|slide-right|fade|none", "cue": "word" | "at": 1.2,
                      "flip": false, "still": false, "z": 2,
                      "repeat": 1, "dx": 0.09, "dy": 0, "stagger": 0.12,
                      "do": [{"act": "grow", "cue": "word", "to": 1.5, "dur": 1.2}, ...]}]}
x is the actor's centre, y its feet (fractions of the frame); size is its height as a fraction of the frame
height. Acts: bounce, jump, shake, wobble, grow, shrink, pop (bursts), fall (by `to` x frame height), walk (to x, or `by` dx), fly (to [x, y]),
swap (to another asset), say (speech bubble), count (number from -> to), fade, tilt (to degrees), glow.
"""

from __future__ import annotations

import html

from .assets import slug

E = html.escape

WORLDS = {
    #          sky top,   sky bottom, ground,    ground far, caption ink, kicker
    "meadow": ("#8FD3FF", "#E3F5FF", "#3F8F3A", "#86CB6E", "#FFFFFF", "#FFE39A"),
    "sky": ("#7CC6FF", "#E8F6FF", "#2E6B5A", "#7CC4A4", "#FFFFFF", "#FFE39A"),
    "sea": ("#8FD3FF", "#E3F5FF", "#1F5F8B", "#3D8FC6", "#FFFFFF", "#FFE39A"),
    "room": ("#FBEBD6", "#F6DDBE", "#8A5A35", "#B07A4D", "#FFFFFF", "#FFE39A"),
    "night": ("#0E1638", "#26346E", "#141B3D", "#1F2A5A", "#FFFFFF", "#FFB27A"),
    "plain": (None, None, None, None, None, None),
}
GROUND = 0.68  # where feet stand and the caption band begins
ACTS = ("bounce", "jump", "shake", "wobble", "grow", "shrink", "pop", "fall", "walk", "fly", "swap", "say", "count",
        "fade", "tilt", "glow")
ENTERS = ("pop", "drop", "rise", "slide-left", "slide-right", "fade", "none")


def src(name: str) -> str:
    return f"assets/img/{slug(name)}.png"


def expand(actors: list[dict]) -> list[dict]:
    """`repeat` turns one actor into a row (a flock of sheep), each a little later than the one before."""
    out = []
    for a in actors:
        n = int(a.get("repeat", 1))
        for k in range(n):
            b = dict(a)
            b["id"] = a["id"] if n == 1 else f"{a['id']}{k}"
            b["x"] = a.get("x", 0.5) + a.get("dx", 0.09) * k
            b["y"] = a.get("y", GROUND) + a.get("dy", 0.0) * k
            b["_delay"] = a.get("stagger", 0.12) * k
            if k and not a.get("label_all"):
                b.pop("label", None)
            out.append(b)
    return out


def assets_used(v: dict) -> set[str]:
    names = set()
    for a in v.get("actors", []):
        names.add(a["asset"])
        for d in a.get("do", []):
            if d.get("act") == "swap":
                names.add(d["asset"])
            if d.get("act") == "pop":
                names.add("Collision")
    if v.get("world", "meadow") in ("meadow", "sky", "sea"):
        names.add("Cloud")
    return names


def _ft(sel, frm, to, at, later=False):
    extra = ", immediateRender: false" if later else ""
    return f'tl.fromTo("{sel}", {{{frm}}}, {{{to}{extra}}}, {max(0.0, at):.3f});'


class _Track:
    """Remembers each element's animated state so every fromTo starts where the last one ended, and marks
    later tweens on the same element immediateRender: false (HyperFrames contract)."""

    def __init__(self):
        self.seen, self.state = set(), {}

    def tw(self, sel, frm: dict, to: dict, at, dur, ease="power2.out", extra=""):
        later = sel in self.seen
        self.seen.add(sel)
        st = self.state.setdefault(sel, {})
        frm = {**{k: st.get(k, v) for k, v in frm.items()}}
        st.update(to)
        f = ", ".join(f"{k}: {_js(v)}" for k, v in frm.items())
        t = ", ".join(f"{k}: {_js(v)}" for k, v in to.items())
        return _ft(sel, f, f'{t}, duration: {dur:.3f}, ease: "{ease}"{extra}', at, later)


def _js(v):
    return f'"{v}"' if isinstance(v, str) else (f"{v:.3f}" if isinstance(v, float) else str(v))


def world_markup(L, sid, world) -> tuple[str, str, list[str]]:
    if world == "plain" or world not in WORLDS:
        return "", "", []
    top, bot, gnd, far, _, _ = WORLDS[world]
    W, H = L.w, L.h
    gy = H * GROUND
    hills = (f'<path d="M0 {gy - H * 0.06:.0f} C {W * 0.25:.0f} {gy - H * 0.16:.0f}, {W * 0.45:.0f} {gy - H * 0.02:.0f}, {W * 0.62:.0f} {gy - H * 0.09:.0f} '
             f'S {W * 0.9:.0f} {gy - H * 0.12:.0f}, {W} {gy - H * 0.07:.0f} L {W} {H} L 0 {H} Z" fill="{far}"/>'
             f'<path d="M0 {gy:.0f} C {W * 0.3:.0f} {gy - H * 0.035:.0f}, {W * 0.7:.0f} {gy + H * 0.02:.0f}, {W} {gy - H * 0.015:.0f} L {W} {H} L 0 {H} Z" fill="{gnd}"/>')
    if world == "sea":
        hills = (f'<rect x="0" y="{gy - H * 0.1:.0f}" width="{W}" height="{H}" fill="{far}"/>'
                 f'<path d="M0 {gy:.0f} q {W * 0.05:.0f} {-H * 0.02:.0f} {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 '
                 f't {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 t {W * 0.1:.0f} 0 L {W} {H} L 0 {H} Z" fill="{gnd}"/>')
    if world == "room":
        hills = (f'<rect x="0" y="{gy:.0f}" width="{W}" height="{H}" fill="{gnd}"/>'
                 f'<rect x="0" y="{gy - H * 0.012:.0f}" width="{W}" height="{H * 0.012:.0f}" fill="{far}"/>')
    stars = ""
    if world == "night":
        pts = [(0.08, 0.12), (0.22, 0.2), (0.35, 0.09), (0.52, 0.17), (0.66, 0.08), (0.8, 0.22), (0.92, 0.11), (0.45, 0.3)]
        stars = "".join(f'<circle cx="{W * x:.0f}" cy="{H * y:.0f}" r="{L.px(0.004)}" fill="#FFF6D8" opacity="0.8"/>' for x, y in pts)
    m = (f'<div id="{sid}-world" style="position:absolute;inset:0;background:linear-gradient(180deg,{top} 0%,{bot} {GROUND * 100:.0f}%);">'
         f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="position:absolute;left:0;top:0">{stars}{hills}</svg></div>')
    tw = []
    if world in ("meadow", "sky", "sea"):
        for k, (x, y, s) in enumerate(((0.12, 0.13, 0.13), (0.72, 0.09, 0.1))):
            cid = f"{sid}-cl{k}"
            m += (f'<img id="{cid}" src="{src("Cloud")}" alt="" style="position:absolute;left:{W * x:.0f}px;top:{H * y:.0f}px;'
                  f'width:{H * s * 1.3:.0f}px;height:{H * s * 1.3:.0f}px;opacity:0.9">')
            tw.append(_ft(f"#{cid}", "x: 0", f'x: {W * 0.05 * (1 if k else -1):.0f}, duration: 12, ease: "none"', 0))
    return m, "", tw


def stage(L, sid, v, dur, cue):
    W, H = L.w, L.h
    world = v.get("world", "meadow")
    T = _Track()
    wm, wcss, tw = world_markup(L, sid, world)
    parts = [wm]
    for i, a in enumerate(expand(v["actors"])):
        aid = f"{sid}-{a['id']}"
        s = H * float(a.get("size", 0.26))
        x, y = W * float(a.get("x", 0.5)), H * float(a.get("y", GROUND))
        delay = a.get("_delay", 0.0)

        def when(d, default, delay=delay):
            extra = delay + float(d.get("delay", 0.0))
            if d.get("cue"):
                return cue(d["cue"], default) + extra
            return float(d.get("at", default)) + extra

        flip = "transform:scaleX(-1);" if a.get("flip") else ""
        imgs = [a["asset"]] + [d["asset"] for d in a.get("do", []) if d.get("act") == "swap"]
        img_html = "".join(f'<img id="{aid}-i{k}" src="{src(n)}" alt="" class="pic" style="{flip}{"opacity:0;" if k else ""}">'
                           for k, n in enumerate(imgs))
        extras, lbl = "", ""
        if a.get("label"):
            lbl = f'<div id="{aid}-lb" class="lbl" style="top:{s + L.px(0.012)}px">{E(a["label"])}</div>'
        says = [d for d in a.get("do", []) if d.get("act") == "say"]
        for k, d in enumerate(says):
            side = d.get("side", "right")
            pos = (f"left:{s * 0.62:.0f}px;" if side == "right" else f"right:{s * 0.62:.0f}px;")
            extras += (f'<div id="{aid}-say{k}" class="say say-{side}" style="{pos}bottom:{s * 0.98:.0f}px">'
                       f'{E(d["text"])}</div>')
        counts = [d for d in a.get("do", []) if d.get("act") == "count"]
        if counts:
            c0 = counts[0]
            img_html += (f'<div id="{aid}-cnt" class="cnt" style="top:{s * float(c0.get("pos", 0.42)) - L.fs(0.06) * 0.6:.0f}px">'
                       f'{E(c0.get("prefix", ""))}<span id="{aid}-cv">{float(c0.get("from", 0)):,.0f}</span>{E(c0.get("suffix", ""))}</div>')
        if any(d.get("act") == "pop" for d in a.get("do", [])):
            extras += f'<img id="{aid}-boom" src="{src("Collision")}" alt="" class="pic" style="opacity:0">'
        if any(d.get("act") == "glow" for d in a.get("do", [])):
            extras = f'<div id="{aid}-glow" class="glow" style="opacity:0"></div>' + extras
        parts.append(
            f'<div id="{aid}" class="actor" style="left:{x - s / 2:.0f}px;top:{y - s:.0f}px;width:{s:.0f}px;height:{s:.0f}px;z-index:{int(a.get("z", 2 + i))}">'
            f'<div id="{aid}-m" class="fill"><div id="{aid}-d" class="fill"><div id="{aid}-x" class="fill">{img_html}</div></div>{lbl}{extras}</div></div>')
        # entrance
        how = a.get("enter", "pop")
        t_in = when(a, 0.15 + 0.12 * i)
        if how == "pop":
            tw.append(T.tw(f"#{aid}", {"opacity": 0, "scale": 0.2}, {"opacity": 1, "scale": 1}, t_in, 0.55, "back.out(2.2)",
                           ', transformOrigin: "50% 100%"'))
        elif how == "drop":
            tw.append(T.tw(f"#{aid}", {"opacity": 0, "y": -H * 0.5}, {"opacity": 1, "y": 0}, t_in, 0.8, "bounce.out"))
        elif how == "rise":
            tw.append(T.tw(f"#{aid}", {"opacity": 0, "y": H * 0.08}, {"opacity": 1, "y": 0}, t_in, 0.6, "power3.out"))
        elif how in ("slide-left", "slide-right"):
            dx = -W * 0.6 if how == "slide-left" else W * 0.6
            tw.append(T.tw(f"#{aid}", {"opacity": 1, "x": dx}, {"opacity": 1, "x": 0}, t_in, 1.0, "power2.out"))
        elif how == "fade":
            tw.append(T.tw(f"#{aid}", {"opacity": 0}, {"opacity": 1}, t_in, 0.5))
        # idle: a gentle breath so nothing on screen is ever frozen
        if not a.get("still"):
            per = 1.1 + 0.13 * (i % 4)
            n = max(1, int((dur - t_in) / per))
            n += (n + 1) % 2
            tw.append(_ft(f"#{aid}-d", "y: 0", f'y: {-s * 0.03:.1f}, duration: {per:.2f}, repeat: {n}, yoyo: true, ease: "sine.inOut"', t_in + 0.5))
        k_say = 0
        for d in a.get("do", []):
            act = d["act"]
            t = when(d, t_in + 1.0)
            X = f"#{aid}-x"
            M = f"#{aid}-m"
            if act == "bounce":
                tw.append(_ft(X, "y: 0", f'y: {-s * 0.16:.1f}, duration: 0.18, repeat: 3, yoyo: true, ease: "power1.out"', t, X in T.seen))
                T.seen.add(X)
            elif act == "jump":
                tw.append(_ft(X, "y: 0", f'y: {-s * 0.35:.1f}, duration: 0.3, repeat: 1, yoyo: true, ease: "power2.out"', t, X in T.seen))
                T.seen.add(X)
            elif act == "shake":
                tw.append(_ft(X, "x: 0", f'x: {s * 0.06:.1f}, duration: 0.05, repeat: 9, yoyo: true, ease: "none"', t, X in T.seen))
                T.seen.add(X)
            elif act == "wobble":
                tw.append(_ft(X, "rotation: 0", 'rotation: 9, duration: 0.15, repeat: 5, yoyo: true, ease: "sine.inOut"', t, X in T.seen))
                T.seen.add(X)
            elif act in ("grow", "shrink"):
                to = float(d.get("to", 1.5 if act == "grow" else 0.6))
                origin = "50% 50%" if d.get("origin") == "center" else "50% 100%"
                tw.append(T.tw(X, {"scale": 1.0}, {"scale": to}, t, float(d.get("dur", 1.2)), d.get("ease", "power1.inOut"),
                               f', transformOrigin: "{origin}"'))
            elif act == "pop":
                sc = T.state.get(X, {}).get("scale", 1.0)
                tw.append(T.tw(X, {"scale": sc}, {"scale": sc * 1.12}, t - 0.08, 0.08, "power2.out", ', transformOrigin: "50% 50%"'))
                tw.append(T.tw(X, {"opacity": 1}, {"opacity": 0}, t, 0.04, "none"))
                tw.append(_ft(f"#{aid}-boom", "opacity: 0, scale: 0.3", f'opacity: 1, scale: {sc * 1.15:.2f}, duration: 0.18, ease: "expo.out"', t))
                tw.append(_ft(f"#{aid}-boom", "opacity: 1", 'opacity: 0, duration: 0.4, ease: "power2.in"', t + 0.35, True))
            elif act == "fall":
                dy = H * float(d.get("to", 0.3))  # how far it drops, as a fraction of the frame height
                tw.append(T.tw(M, {"y": 0.0}, {"y": dy}, t, float(d.get("dur", 0.8)), d.get("ease", "bounce.out")))
                if d.get("spin"):
                    tw.append(T.tw(X, {"rotation": 0}, {"rotation": float(d["spin"])}, t, 0.6))
            elif act == "walk":
                tx = (float(d["to"]) - float(a.get("x", 0.5))) * W if "to" in d else float(d.get("by", 0.2)) * W
                dd = float(d.get("dur", 1.6))
                tw.append(T.tw(M, {"x": 0.0}, {"x": tx}, t, dd, "none"))
                n = max(1, int(dd / 0.18)) | 1
                tw.append(_ft(X, "y: 0", f'y: {-s * 0.06:.1f}, duration: 0.09, repeat: {n}, yoyo: true, ease: "sine.inOut"', t, X in T.seen))
                T.seen.add(X)
            elif act == "fly":
                tx, ty = d["to"]
                tw.append(T.tw(M, {"x": 0.0, "y": 0.0}, {"x": (tx - float(a.get("x", 0.5))) * W, "y": (ty - float(a.get("y", GROUND))) * H},
                               t, float(d.get("dur", 1.4)), d.get("ease", "power2.inOut")))
            elif act == "swap":
                k = imgs.index(d["asset"], 1)
                prev = T.state.get("_cur" + aid, 0)
                tw.append(_ft(f"#{aid}-i{prev}", "opacity: 1", 'opacity: 0, duration: 0.12, ease: "none"', t, f"#{aid}-i{prev}" in T.seen))
                T.seen.add(f"#{aid}-i{prev}")
                tw.append(_ft(f"#{aid}-i{k}", "opacity: 0, scale: 0.7", 'opacity: 1, scale: 1, duration: 0.35, ease: "back.out(3)"', t))
                T.seen.add(f"#{aid}-i{k}")
                T.state["_cur" + aid] = k
            elif act == "say":
                el = f"#{aid}-say{k_say}"
                k_say += 1
                origin = "0% 100%" if d.get("side", "right") == "right" else "100% 100%"
                tw.append(_ft(el, "opacity: 0, scale: 0.3", f'opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.5)", transformOrigin: "{origin}"', t))
                hold = float(d.get("hold", 2.2))
                if hold > 0:
                    tw.append(_ft(el, "opacity: 1", 'opacity: 0, duration: 0.2, ease: "power2.in"', t + hold, True))
            elif act == "count":
                frm, to = float(d.get("from", 0)), float(d["to"])
                key = f"{aid}-c{int(t * 1000)}".replace("-", "_")
                tw.append(f'const {key} = {{ v: {frm} }};')
                tw.append(f'tl.fromTo({key}, {{ v: {frm} }}, {{ v: {to}, duration: {float(d.get("dur", 1.0)):.2f}, ease: "power2.out", '
                          f'onUpdate: () => {{ document.getElementById("{aid}-cv").textContent = Math.round({key}.v).toLocaleString("en-US"); }} }}, {t:.3f});')
            elif act == "fade":
                tw.append(T.tw(X, {"opacity": 1}, {"opacity": float(d.get("to", 0))}, t, float(d.get("dur", 0.4))))
            elif act == "tilt":
                tw.append(T.tw(X, {"rotation": 0}, {"rotation": float(d.get("to", 12))}, t, float(d.get("dur", 0.5)), "back.out(2)",
                               ', transformOrigin: "50% 100%"'))
            elif act == "glow":
                tw.append(_ft(f"#{aid}-glow", "opacity: 0, scale: 0.6", 'opacity: 1, scale: 1.25, duration: 0.5, ease: "power2.out"', t))
    _, _, _, _, ink, kick = WORLDS.get(world, WORLDS["plain"])
    ink, kick = ink or L.ink, kick or L.accent
    css = f"""
    #{sid}-wrap .actor {{ position: absolute; }}
    #{sid}-wrap .fill {{ position: absolute; inset: 0; }}
    #{sid}-wrap .pic {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain;
      filter: drop-shadow(0 {L.px(0.01)}px {L.px(0.012)}px rgba(0,0,0,0.25)); }}
    #{sid}-wrap .lbl {{ position: absolute; left: 50%; transform: translateX(-50%); white-space: nowrap; padding: {L.px(0.006)}px {L.px(0.016)}px;
      border-radius: 999px; background: rgba(10,14,20,0.72); color: #FFFFFF; font-family: {L.sans}; font-weight: 700;
      font-size: {L.fs(0.026)}px; letter-spacing: 0.12em; text-transform: uppercase; }}
    #{sid}-wrap .say {{ position: absolute; white-space: nowrap; padding: {L.px(0.014)}px {L.px(0.024)}px; border-radius: {L.px(0.03)}px;
      background: #FFFFFF; color: #1A1F2B; font-family: {L.sans}; font-weight: 800; font-size: {L.fs(0.036)}px;
      box-shadow: 0 {L.px(0.006)}px {L.px(0.02)}px rgba(0,0,0,0.2); }}
    #{sid}-wrap .say-right {{ border-bottom-left-radius: {L.px(0.004)}px; }}
    #{sid}-wrap .say-left {{ border-bottom-right-radius: {L.px(0.004)}px; }}
    #{sid}-wrap .cnt {{ position: absolute; left: -50%; right: -50%; text-align: center; font-family: {L.serif}; font-weight: 600;
      font-size: {L.fs(0.06)}px; color: #FFFFFF; text-shadow: 0 2px {L.px(0.012)}px rgba(0,0,0,0.55); font-variant-numeric: tabular-nums; }}
    #{sid}-wrap .glow {{ position: absolute; inset: -30%; border-radius: 50%; background: radial-gradient(closest-side, {L.accent}66, transparent); }}
    #{sid}-cap .serif {{ color: {ink}; text-shadow: 0 2px {L.px(0.014)}px rgba(0,0,0,0.35); }}
    #{sid}-cap .kicker {{ color: {kick}; }}
    #{sid}-cap .acc {{ color: {kick if world != "plain" else L.accent}; }}
    """ + wcss
    return "".join(parts), css, [t for t in tw if t]
