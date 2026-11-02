"""Teaching scenes where the picture itself changes state.

- scenario  a worked example: labelled bars show the "before" values, a slider scrubs from before to after while the bars
            and their numbers move to the "after" values, then one line says what changed
- board     one continuous canvas for a chapter: each idea lives in its own region (a picture + a label), the camera
            glides from region to region on cue words, and can pull back to show the whole board (a recap)

Same contract as scenes.py: ids prefixed with the beat id, fromTo tweens only (later ones with immediateRender: false),
every frame a function of timeline time, deterministic layouts. Calm motion only: eased glides, no shakes or flashes.
"""

from __future__ import annotations

import copy
import math

from .metaphors import ICONS, _blur_in, _head
from .scenes import GENERATORS, E, _fade, _fmt_num, _ft, _rise

LABELS = {"en": ("Before", "After"), "vi": ("Trước", "Sau")}


def _lang(L) -> str:
    return "vi" if L.t.get("locale") == "vi-VN" else "en"


# ---------------------------------------------------------------- scenario: a worked example that changes on screen

def scenario(L, sid, v, dur, cue):
    """`bars` (1-3): [{label, before, after, cue?, delta?, color?|concept?}] drawn as horizontal bars with their values.
    On `cue` the slider scrubs from `before_label` to `after_label` and every bar and number moves to its after value;
    `takeaway` (one line) lands on `takeaway_cue`. `prefix`/`suffix`/`decimals` format the numbers, `max` fixes the scale."""
    bars = v["bars"][:3]
    n = len(bars)
    dec = int(v.get("decimals", 0))
    pre, suf = E(v.get("prefix", "")), E(v.get("suffix", ""))
    loc = L.t["locale"]
    vmax = float(v.get("max") or max(max(float(b["before"]), float(b["after"])) for b in bars) * 1.05 or 1.0)
    bl, al = LABELS[_lang(L)]
    head, tw = _head(L, sid, v, 0.1)
    x0, x1 = L.w * 0.1, L.w * 0.9
    tx1 = L.w * 0.7  # bars end here; the numbers sit in the column to the right
    # the slider: before ... after, with a knob that travels as the example changes state
    ys = L.h * (0.33 if v.get("heading") else 0.27)
    ty = ys + L.px(0.06)
    kr = L.px(0.018)
    slider = f"""<div id="{sid}-bl" style="position:absolute;left:{x0:.0f}px;top:{ys:.0f}px;font-size:{L.fs(L.READ)}px;font-weight:600;">{E(v.get('before_label', bl))}</div>
      <div id="{sid}-al" class="acc" style="position:absolute;right:{L.w - x1:.0f}px;top:{ys:.0f}px;font-size:{L.fs(L.READ)}px;font-weight:600;text-align:right;">{E(v.get('after_label', al))}</div>
      <div id="{sid}-tr" style="position:absolute;left:{x0:.0f}px;top:{ty:.0f}px;width:{x1 - x0:.0f}px;height:6px;border-radius:3px;background:rgba(255,255,255,0.14);"></div>
      <div id="{sid}-tf" style="position:absolute;left:{x0:.0f}px;top:{ty:.0f}px;width:{x1 - x0:.0f}px;height:6px;border-radius:3px;background:{L.accent};transform-origin:0 50%;"></div>
      <div id="{sid}-kn" style="position:absolute;left:{x0 - kr:.0f}px;top:{ty + 3 - kr:.0f}px;width:{2 * kr}px;height:{2 * kr}px;border-radius:50%;background:{L.ink};
        box-shadow:0 0 0 {L.px(0.008)}px {L.accent}55;"></div>"""
    # rows: label (and the change, once it happened) above, the bar, its number on the right
    take_h = L.px(0.11) if v.get("takeaway") else 0
    top, bottom = ty + L.px(0.07), L.h * 0.82 - take_h
    pitch = min(L.px(0.16), (bottom - top) / n)
    bh = max(L.px(0.03), min(L.px(0.05), pitch * 0.3))
    rows = ""
    t_bars = []
    for i, b in enumerate(bars):
        ry = top + i * pitch
        c = L.color(b, L.accent)
        rb, ra = (max(0.004, min(1.0, float(b[k]) / vmax)) for k in ("before", "after"))
        by = ry + L.fs(0.036) * 1.3 + L.px(0.008)
        rows += (f'<div id="{sid}-r{i}" style="position:absolute;left:{x0:.0f}px;width:{x1 - x0:.0f}px;top:{ry:.0f}px;">'
                 f'<div style="font-size:{L.fs(0.036)}px;line-height:1.3;max-width:{tx1 - x0 - L.px(0.02):.0f}px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{E(b["label"])}</div></div>'
                 f'<div style="position:absolute;left:{x0:.0f}px;top:{by:.0f}px;width:{tx1 - x0:.0f}px;height:{bh:.0f}px;border-radius:{bh / 2:.0f}px;background:rgba(255,255,255,0.06);"></div>'
                 f'<div id="{sid}-b{i}" style="position:absolute;left:{x0:.0f}px;top:{by:.0f}px;width:{tx1 - x0:.0f}px;height:{bh:.0f}px;border-radius:{bh / 2:.0f}px;'
                 f'background:{c};transform-origin:0 50%;"></div>'
                 f'<div id="{sid}-v{i}" class="serif" style="position:absolute;left:{tx1 + L.px(0.02):.0f}px;right:{L.w - x1:.0f}px;top:{by + bh / 2 - L.fs(0.06) * 0.6:.0f}px;'
                 f'text-align:right;font-size:{L.fs(0.06)}px;line-height:1.2;color:{c};font-variant-numeric:tabular-nums;white-space:nowrap;">'
                 f'{pre}<span id="{sid}-n{i}">{_fmt_num(float(b["before"]), dec, loc)}</span>{suf}</div>')
        if b.get("delta"):
            rows += (f'<div id="{sid}-d{i}" style="position:absolute;right:{L.w - x1:.0f}px;top:{ry:.0f}px;font-size:{L.fs(L.READ)}px;line-height:1.3;'
                     f'font-weight:800;color:{c};">{E(b["delta"])}</div>')
        at = max(0.45 + 0.3 * i, cue(b["cue"], 0.6 + 0.4 * i)) if b.get("cue") else 0.6 + 0.4 * i
        t_bars.append(at)
        tw += [_rise(f"#{sid}-r{i}", at, 0.45, 12),
               _ft(f"#{sid}-b{i}", "scaleX: 0", f'scaleX: {rb:.4f}, duration: 0.7, ease: "expo.out"', at + 0.1),
               _fade(f"#{sid}-v{i}", at + 0.2, 0.4)]
    scrub = 1.4
    t_c = cue(v["cue"], max(1.8, dur * 0.4)) if v.get("cue") else max(1.8, dur * 0.4)
    t_c = min(max(t_c, max(t_bars) + 1.0), max(max(t_bars) + 1.0, dur - scrub - 0.6))
    tw += [_fade(f"#{sid}-bl", 0.2, 0.4),
           _ft(f"#{sid}-al", "opacity: 0", 'opacity: 0.45, duration: 0.4, ease: "power2.out"', 0.3),
           _fade(f"#{sid}-tr", 0.3, 0.4),
           _ft(f"#{sid}-tf", "scaleX: 0", f'scaleX: 1, duration: {scrub}, ease: "power2.inOut"', t_c),
           _ft(f"#{sid}-kn", "opacity: 0, x: 0", 'opacity: 1, x: 0, duration: 0.4, ease: "power2.out"', 0.35),
           _ft(f"#{sid}-kn", "x: 0", f'x: {x1 - x0:.0f}, duration: {scrub}, ease: "power2.inOut"', t_c, later=True),
           _ft(f"#{sid}-bl", "opacity: 1", 'opacity: 0.45, duration: 0.5, ease: "power2.out"', t_c, later=True),
           _ft(f"#{sid}-al", "opacity: 0.45", 'opacity: 1, duration: 0.5, ease: "power2.out"', t_c + scrub - 0.4, later=True)]
    for i, b in enumerate(bars):
        rb, ra = (max(0.004, min(1.0, float(b[k]) / vmax)) for k in ("before", "after"))
        fv, tv = float(b["before"]), float(b["after"])
        tw += [_ft(f"#{sid}-b{i}", f"scaleX: {rb:.4f}", f'scaleX: {ra:.4f}, duration: {scrub}, ease: "power2.inOut"', t_c, later=True),
               f"const {sid}P{i} = {{ v: {fv} }};",
               f'tl.fromTo({sid}P{i}, {{ v: {fv} }}, {{ v: {tv}, duration: {scrub}, ease: "power2.inOut", onUpdate: () => '
               f'{{ document.getElementById("{sid}-n{i}").textContent = {sid}P{i}.v.toLocaleString("{loc}", '
               f'{{minimumFractionDigits: {dec}, maximumFractionDigits: {dec}}}); }} }}, {t_c:.3f});']
        if b.get("delta"):
            tw.append(_blur_in(f"#{sid}-d{i}", t_c + scrub + 0.1 + 0.15 * i, 0.4))
    take = ""
    if v.get("takeaway"):
        take = (f'<div id="{sid}-tk" class="serif" style="position:absolute;left:{x0:.0f}px;right:{L.w - x1:.0f}px;top:{bottom + L.px(0.02):.0f}px;'
                f'font-size:{L.fs(0.05)}px;line-height:1.15;">{E(v["takeaway"])}</div>')
        tw.append(_blur_in(f"#{sid}-tk", max(t_c + scrub + 0.4, cue(v.get("takeaway_cue", ""), t_c + scrub + 0.6)), 0.45))
    return f'<div id="{sid}-c" style="position:absolute;inset:0;">{head}{slider}{rows}{take}</div>', "", tw


# ---------------------------------------------------------------- board: one canvas, the camera travels

def board_layout(L, n: int) -> dict:
    """Cells for n regions, in reading order along a serpentine (row 2 runs right to left), so consecutive regions
    are always neighbours; canvas size; the camera's zoom on one region and on the whole board."""
    cw, ch, gap = L.px(0.52), L.px(0.42), L.px(0.1)
    cols = n if n <= 3 else math.ceil(n / 2)
    rows = 1 if n <= 3 else 2
    cells = []
    for i in range(n):
        r, c = divmod(i, cols)
        if r % 2:
            c = cols - 1 - c
        cells.append((c * (cw + gap), r * (ch + gap)))
    bw, bh = cols * cw + (cols - 1) * gap, rows * ch + (rows - 1) * gap
    return {"cells": cells, "cw": cw, "ch": ch, "bw": bw, "bh": bh,
            "zoom": min(L.w * 0.84 / cw, L.h * 0.62 / ch, 1.6)}


def _overview_scale(L, lay: dict, line: bool) -> float:
    vh = L.h * ((0.68 if line else 0.82) - 0.18)
    return min(L.w * 0.9 / lay["bw"], vh / lay["bh"], 1.2)


def board(L, sid, v, dur, cue):
    """`regions`: [{icon, label, note?, cue?, concept?, color?}] laid out on one canvas. The camera visits `focus` (region
    indices, or {"region", "cue"}; default every region not yet drawn) in order, each region drawing itself as the
    camera arrives, then `overview: true` pulls back to the whole board (`overview_cue`, `line` + `line_cue`).
    `board_id` continues the same board over several beats (resolve_boards fills `_drawn` and `_cam0`)."""
    regions = v["regions"][:6]
    n = len(regions)
    lay = board_layout(L, n)
    cw, ch, zf = lay["cw"], lay["ch"], lay["zoom"]
    so = _overview_scale(L, lay, bool(v.get("line")))
    vcx, vcy = L.w * 0.5, L.h * 0.5  # the focus viewport's centre (0.18h-0.82h)
    ocy = L.h * ((0.18 + (0.68 if v.get("line") else 0.82)) / 2)
    drawn = set(v.get("_drawn") or [])
    focus = []
    for f in v.get("focus") or [i for i in range(n) if i not in drawn]:
        idx, w = (f, "") if isinstance(f, int) else (int(f["region"]), f.get("cue", ""))
        if 0 <= idx < n:
            focus.append((idx, w or regions[idx].get("cue", "")))

    def state(key) -> tuple[float, float, float]:
        if key == "overview":
            return (L.w * 0.5 - so * lay["bw"] / 2, ocy - so * lay["bh"] / 2, so)
        x, y = lay["cells"][key]
        return (vcx - zf * (x + cw / 2), vcy - zf * (y + ch / 2), zf)

    def push(st, k=1.025):  # a slow push-in toward the frame centre while the camera holds
        x, y, s = st
        cx, cy = (vcx, vcy) if s == zf else (L.w * 0.5, ocy)
        return (cx - (cx - x) * k, cy - (cy - y) * k, s * k)

    # label sizes in canvas pixels: still >= 36 px on screen when the whole board is shown
    fl = max(L.fs(0.045), math.ceil(L.fs(L.READ) / so) + 1)
    ic = int(ch * 0.42)
    cells, tw = "", []
    head, htw = _head(L, sid, v, 0.1)
    tw += htw
    cam0 = v.get("_cam0")
    if cam0 is None:
        cam0 = "overview" if v.get("start") == "overview" or not focus else focus[0][0]
    # region brightness now: drawn regions behind the camera rest at half; empty cells (only their faint frame) at full
    op = {i: (1.0 if cam0 == "overview" or i == cam0 or i not in drawn else 0.5) for i in range(n)}
    for i, rg in enumerate(regions):
        x, y = lay["cells"][i]
        c = L.color(rg, L.accent)
        art = ICONS.get(L.icon_of(rg), lambda s, c: "")(ic, c)
        hide = "" if i in drawn else "opacity:0;"
        note = (f'<div id="{sid}-rn{i}" class="muted" style="font-size:{fl}px;line-height:1.15;margin-top:{L.px(0.01)}px;{hide}">{E(rg["note"])}</div>'
                if rg.get("note") else "")
        cells += (f'<div id="{sid}-rw{i}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{cw}px;height:{ch}px;opacity:{op[i]};">'
                  f'<div style="position:absolute;inset:0;border:2px solid {L.muted}33;border-radius:{L.px(0.03)}px;"></div>'
                  f'<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 {L.px(0.02)}px;">'
                  f'<svg id="{sid}-ri{i}" width="{ic}" height="{ic}" style="overflow:visible;{hide}">{art}</svg>'
                  f'<div id="{sid}-rl{i}" style="font-size:{fl}px;line-height:1.15;font-weight:600;margin-top:{L.px(0.015)}px;color:{L.ink};{hide}">{E(rg["label"])}</div>'
                  f'{note}</div></div>')
    # connectors along the serpentine: drawn as the camera travels from one region to the next
    links, lens, linked = "", {}, set()
    for i in range(n - 1):
        (xa, ya), (xb, yb) = lay["cells"][i], lay["cells"][i + 1]
        ax, ay, bx, by = xa + cw / 2, ya + ch / 2, xb + cw / 2, yb + ch / 2
        d = math.hypot(bx - ax, by - ay) or 1
        ux, uy = (bx - ax) / d, (by - ay) / d
        trim = (cw if abs(ux) > abs(uy) else ch) / 2 + L.px(0.015)
        p0, p1 = (ax + ux * trim, ay + uy * trim), (bx - ux * trim, by - uy * trim)
        ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        both = i in drawn and i + 1 in drawn
        lens[i] = ln
        if both:
            linked.add(i)
        links += (f'<path id="{sid}-ln{i}" d="M{p0[0]:.0f} {p0[1]:.0f} L{p1[0]:.0f} {p1[1]:.0f}" fill="none" stroke="{L.accent}" stroke-opacity="0.6" '
                  f'stroke-width="{max(3, L.px(0.004))}" stroke-linecap="round" stroke-dasharray="{ln:.0f}" stroke-dashoffset="{0 if both else ln:.0f}"/>')
    # the camera path: (time, state) keyframes, then one tween per segment so every frame is a function of time
    o_end = dur - 0.2
    t_over = None
    if v.get("overview"):
        t_over = cue(v.get("overview_cue", ""), dur - 2.6) if v.get("overview_cue") else dur - 2.6
    span_end = (t_over if t_over is not None else dur - 1.2)
    times, prev_t = [], 0.0
    for k, (idx, w) in enumerate(focus):
        default = 0.3 + (span_end - 0.3) * k / max(1, len(focus))
        t = cue(w, default) if w else default
        t = max(t, prev_t + (1.9 if k else 0.0))
        times.append(t)
        prev_t = t
    if t_over is not None:
        t_over = max(t_over, (times[-1] + 2.2) if times else 0.4)
    glide = 1.2
    cur, cur_key, t_cur = state(cam0), cam0, 0.0
    cam = []

    def go(t_to: float, to_state, dur_: float, ease: str):
        nonlocal cur, t_cur
        cam.append((t_to, cur, to_state, dur_, ease))
        cur, t_cur = to_state, t_to + dur_

    def hold_until(t: float, settle: bool = False):
        if t - t_cur > 0.25:
            go(t_cur, cur if settle else push(cur), t - t_cur, "sine.inOut")

    for k, ((idx, _), t) in enumerate(zip(focus, times)):
        move = idx != cur_key
        if move:
            hold_until(t)
            go(t, state(idx), glide, "power2.inOut")
            # the connector from the region just left (or the one before, when coming from the overview) draws itself
            a = min(idx, cur_key) if isinstance(cur_key, int) and abs(idx - cur_key) == 1 else (idx - 1 if idx - 1 in drawn else None)
            if a is not None and a >= 0 and a not in linked:
                tw.append(_ft(f"#{sid}-ln{a}", f"strokeDashoffset: {lens[a]:.0f}", 'strokeDashoffset: 0, duration: 0.9, ease: "power2.inOut"', t + 0.2))
                linked.add(a)
        arrive = t + (glide - 0.4 if move else 0.15)
        if idx not in drawn:
            tw += [_ft(f"#{sid}-ri{idx}", "opacity: 0, y: 24", 'opacity: 1, y: 0, duration: 0.6, ease: "expo.out"', arrive),
                   _blur_in(f"#{sid}-rl{idx}", arrive + 0.3, 0.4)]
            if regions[idx].get("note"):
                tw.append(_blur_in(f"#{sid}-rn{idx}", max(arrive + 0.8, cue(regions[idx].get("note_cue", ""), arrive + 1.0)), 0.4))
            drawn.add(idx)
        # brightness: the region in view is lit, the ones behind the camera rest at half
        for j in range(n):
            want = 1.0 if j == idx else 0.5
            if op[j] != want and (j in drawn or j == idx):
                tw.append(_ft(f"#{sid}-rw{j}", f"opacity: {op[j]}", f'opacity: {want}, duration: 0.6, ease: "power2.out"', t, later=True))
                op[j] = want
        cur_key = idx
    if t_over is not None:
        hold_until(t_over)
        go(t_over, state("overview"), 1.6, "power2.inOut")
        for j in range(n):
            if j in drawn and op[j] != 1.0:
                tw.append(_ft(f"#{sid}-rw{j}", f"opacity: {op[j]}", 'opacity: 1, duration: 0.8, ease: "power2.out"', t_over + 0.4, later=True))
                op[j] = 1.0
        cur_key = "overview"
    # the last hold: a slow push, unless the next beat continues this board from exactly here
    hold_until(o_end, settle=bool(v.get("_cont_next")))
    for i, (t, a, b, d_, ease) in enumerate(cam):
        tw.append(_ft(f"#{sid}-cv", f"x: {a[0]:.1f}, y: {a[1]:.1f}, scale: {a[2]:.4f}",
                      f'x: {b[0]:.1f}, y: {b[1]:.1f}, scale: {b[2]:.4f}, duration: {d_:.2f}, ease: "{ease}"', t, later=i > 0))
    if not cam:
        s0 = state(cam0)
        tw.append(_ft(f"#{sid}-cv", f"x: {s0[0]:.1f}, y: {s0[1]:.1f}, scale: {s0[2]:.4f}",
                      f'x: {s0[0]:.1f}, y: {s0[1]:.1f}, scale: {s0[2]:.4f}, duration: 0.1, ease: "none"', 0))
    line = ""
    if v.get("line"):
        line = (f'<div id="{sid}-ln" class="serif" style="position:absolute;left:{L.px(0.08)}px;right:{L.px(0.08)}px;top:{L.h * 0.7:.0f}px;'
                f'text-align:center;font-size:{L.fs(0.055)}px;line-height:1.15;opacity:0;">{E(v["line"])}</div>')
        t_line = (t_over + 0.8) if t_over is not None else dur * 0.7
        tw.append(_blur_in(f"#{sid}-ln", max(t_line, cue(v.get("line_cue", ""), t_line)), 0.45))
    canvas = (f'<div id="{sid}-cv" style="position:absolute;left:0;top:0;width:{lay["bw"]:.0f}px;height:{lay["bh"]:.0f}px;transform-origin:0 0;">'
              f'<svg width="{lay["bw"]:.0f}" height="{lay["bh"]:.0f}" style="position:absolute;left:0;top:0;overflow:visible">{links}</svg>{cells}</div>')
    m = f'<div id="{sid}-c" style="position:absolute;inset:0;overflow:hidden;">{canvas}{head}{line}</div>'
    return m, "", tw


def resolve_boards(visuals: list[dict]) -> list[dict]:
    """A board spread over several beats (same `board_id`): later beats inherit `regions`, start with the regions
    already drawn (`_drawn`) and the camera where the previous beat left it (`_cam0`); a beat whose next beat continues
    the board ends without its exit (`_cont_next`). Returns copies; the lesson is not changed."""
    out = [copy.deepcopy(v) for v in visuals]
    boards: dict[str, dict] = {}
    for i, v in enumerate(out):
        if v.get("type") != "board" or not v.get("board_id"):
            continue
        st = boards.setdefault(v["board_id"], {"regions": v.get("regions"), "drawn": set(), "cam": None})
        if not v.get("regions"):
            v["regions"] = st["regions"]
        v["_drawn"] = sorted(st["drawn"])
        if st["cam"] is not None:
            v["_cam0"] = st["cam"]
        n = len(v["regions"] or [])
        focus = [f if isinstance(f, int) else int(f["region"]) for f in v.get("focus") or [j for j in range(n) if j not in st["drawn"]]]
        st["drawn"] |= set(focus)
        st["cam"] = "overview" if v.get("overview") else (focus[-1] if focus else st["cam"])
        nxt = out[i + 1] if i + 1 < len(out) else {}
        v["_cont_next"] = nxt.get("type") == "board" and nxt.get("board_id") == v["board_id"]
    return out


GENERATORS.update({"scenario": scenario, "board": board})
