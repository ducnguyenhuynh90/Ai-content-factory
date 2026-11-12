"""9:16 frame renderer for shorts: Pillow draws every frame, ffmpeg encodes. No browser, no network.

Layout follows the TikTok UI: the right 15 % (like/comment/share rail) and the bottom 28 % (caption, sound,
nav bar) are covered on the phone, so pictures and key text live in the stage band (11-58 % of the height),
karaoke captions sit just above the UI (≈ 65 %), and nothing important goes right of 85 % of the width.
"""

from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .. import easing as E
from .. import fonts
from ..ffmpeg import FFMPEG
from ..motion.core import hex_rgb, transform

THEMES = {
    "night": {"bg": "#0D0D10", "bg2": "#1E1914", "ink": "#F6F1E7", "accent": "#FF4F00", "hl": "#FFD23F",
              "muted": "#A29A8E", "on_accent": "#0D0D10", "stroke": "#000000", "glow": "#FF4F00", "grain": 0.03},
    "paper": {"bg": "#F4ECDD", "bg2": "#E6D7BE", "ink": "#1B1A17", "accent": "#D7263D", "hl": "#D7263D",
              "muted": "#6E6658", "on_accent": "#FFF8EC", "stroke": "#FFF8EC", "glow": "#FFFFFF", "grain": 0.04},
    "neon": {"bg": "#050507", "bg2": "#0B1020", "ink": "#FFFFFF", "accent": "#C6FF00", "hl": "#00E5FF",
             "muted": "#8C95A8", "on_accent": "#050507", "stroke": "#000000", "glow": "#00E5FF", "grain": 0.025},
}
DISPLAY = "anton"      # condensed caps for hooks, numbers, titles (has full Vietnamese)
BODY = "montserrat"    # variable; 800-900 for statements and captions (has full Vietnamese)
SAFE_L, SAFE_R = 0.07, 0.85
STAGE_TOP, STAGE_BOTTOM = 0.11, 0.58
CAPTION_Y = 0.655


def theme(name: str, overrides: dict | None = None) -> dict:
    return {**THEMES.get(name, THEMES["night"]), **(overrides or {})}


def rgba(c: str, a: float = 1.0) -> tuple:
    return (*hex_rgb(c), int(255 * max(0.0, min(1.0, a))))


@dataclass
class Ctx:
    W: int
    H: int
    fps: int
    th: dict
    lang: str = "vi"

    @property
    def s(self) -> float:
        return self.W / 1080.0

    def px(self, v: float) -> int:
        return int(round(v * self.s))

    def font(self, name: str, size: float, weight: int | None = None):
        return fonts.get(name, max(8, int(size * self.s)), weight)

    @property
    def safe_w(self) -> int:
        return int(self.W * (SAFE_R - SAFE_L))

    @property
    def cx(self) -> int:  # visual centre of the safe area, a little left of the frame centre
        return int(self.W * (SAFE_L + SAFE_R) / 2)


# ---------------------------------------------------------------- text

def norm(w: str) -> str:
    return re.sub(r"[^\w%$£€]", "", w.lower())


def hl_set(highlight) -> set[str]:
    if isinstance(highlight, str):
        highlight = [highlight]
    return {norm(w) for h in (highlight or []) for w in str(h).split() if norm(w)}


def word_img(text: str, font, color: str, stroke: int = 0, stroke_color: str = "#000000",
             box: str | None = None, pad: int = 0) -> Image.Image:
    asc, desc = font.getmetrics()
    w = int(font.getlength(text)) + 2 * stroke
    bx = int(font.size * 0.18) if box else 0
    by = int(font.size * 0.10) if box else 0
    img = Image.new("RGBA", (w + 2 * bx + 2 * pad, asc + desc + 2 * stroke + 2 * by + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if box:
        d.rounded_rectangle([pad, pad, img.width - pad - 1, img.height - pad - 1], radius=int(font.size * 0.16), fill=rgba(box))
    d.text((bx + pad + stroke, by + pad + stroke), text, font=font, fill=rgba(color), anchor="la",
           stroke_width=stroke, stroke_fill=rgba(stroke_color) if stroke else None)
    return img


def wrap(words: list[str], font, max_w: float, max_lines: int = 3) -> list[list[str]]:
    """Balanced wrap: the fewest lines that fit, then the split with the most even line widths."""
    sp = font.getlength(" ")
    lens = [font.getlength(w) for w in words]

    def width(a: int, b: int) -> float:
        return sum(lens[a:b]) + sp * max(0, b - a - 1)

    n = len(words)
    for k in range(1, max_lines + 1):
        best, best_score = None, None
        def splits(start: int, left: int):
            if left == 1:
                yield [(start, n)]
                return
            for e in range(start + 1, n - left + 2):
                for rest in splits(e, left - 1):
                    yield [(start, e)] + rest
        if k > n:
            break
        for sp_ in splits(0, k):
            ws = [width(a, b) for a, b in sp_]
            if max(ws) <= max_w:
                score = max(ws) - min(ws)
                if best_score is None or score < best_score:
                    best, best_score = sp_, score
        if best:
            return [words[a:b] for a, b in best]
    return [words]  # caller shrinks the font


def fit(text: str, name: str, weight: int | None, size: float, max_w: float, max_lines: int, ctx: Ctx, min_size: float = 34):
    words = text.split()
    while True:
        f = ctx.font(name, size, weight)
        lines = wrap(words, f, max_w, max_lines)
        if (len(lines) <= max_lines and all(f.getlength(" ".join(l)) <= max_w for l in lines)) or size <= min_size:
            return f, lines
        size *= 0.93


@dataclass
class WordSprite:
    word: str
    img: Image.Image
    x: float  # centre
    y: float
    hl: bool = False
    idx: int = 0


def block(ctx: Ctx, text: str, name: str, weight: int | None, size: float, cx: float, cy: float, *,
          max_w: float | None = None, max_lines: int = 3, color: str | None = None, highlight=None,
          hl_color: str | None = None, hl_box: bool = False, stroke: int = 0, upper: bool = False,
          line_gap: float = 1.08, stroke_color: str | None = None) -> list[WordSprite]:
    """Lay out text as one sprite per word, centred on (cx, cy)."""
    th = ctx.th
    text = text.upper() if upper else text
    f, lines = fit(text, name, weight, size, max_w or ctx.safe_w, max_lines, ctx)
    hs = hl_set(highlight)
    asc, desc = f.getmetrics()
    lh = (asc + desc) * line_gap
    sp = f.getlength(" ")
    out, idx = [], 0
    y0 = cy - lh * len(lines) / 2 + lh / 2
    for li, line in enumerate(lines):
        imgs = []
        for w in line:
            h = norm(w) in hs
            c = (hl_color or th["hl"]) if h and not hl_box else (color or th["ink"])
            imgs.append((w, word_img(w, f, th["on_accent"] if (h and hl_box) else c, stroke, stroke_color or th["stroke"],
                                     box=(hl_color or th["accent"]) if (h and hl_box) else None), h))
        total = sum(i.width for _, i, _ in imgs) + sp * (len(imgs) - 1)
        x = cx - total / 2
        for w, im, h in imgs:
            out.append(WordSprite(w, im, x + im.width / 2, y0 + li * lh, h, idx))
            x += im.width + sp
            idx += 1
    return out


def put(canvas: Image.Image, img: Image.Image, x: float, y: float, scale: float = 1.0, alpha: float = 1.0,
        angle: float = 0.0) -> None:
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3 or alpha < 0.999:
        img = transform(img, scale=scale, alpha=alpha)
    if abs(angle) > 0.2:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    x0, y0 = int(round(x - img.width / 2)), int(round(y - img.height / 2))
    if x0 >= 0 and y0 >= 0 and x0 + img.width <= canvas.width and y0 + img.height <= canvas.height:
        canvas.alpha_composite(img, (x0, y0))
    else:
        l, t = max(0, x0), max(0, y0)
        r, b = min(canvas.width, x0 + img.width), min(canvas.height, y0 + img.height)
        if r > l and b > t:
            canvas.alpha_composite(img.crop((l - x0, t - y0, r - x0, b - y0)), (l, t))


def pop(t: float, t0: float, dur: float = 0.24, start: float = 0.55) -> tuple[float, float]:
    """(scale, alpha) for an element that pops in at t0 with a small overshoot."""
    if t < t0:
        return 0.0, 0.0
    p = E.clamp((t - t0) / dur)
    return start + (1 - start) * E.out_back(p, 2.2), E.clamp((t - t0) / 0.07)


def slam(t: float, t0: float, dur: float = 0.2) -> tuple[float, float]:
    if t < t0:
        return 0.0, 0.0
    p = E.clamp((t - t0) / dur)
    return 1.0 + 0.7 * (1 - E.out_expo(p)), E.clamp((t - t0) / 0.05)


def draw_words(canvas, sprites: list[WordSprite], t: float, starts: list[float] | None = None, *, dim_before: float | None = None):
    for i, sp in enumerate(sprites):
        t0 = starts[i] if starts else -1
        sc, a = pop(t, t0) if starts else (1.0, 1.0)
        if sp.hl and starts and t >= t0:
            sc *= 1 + 0.06 * math.exp(-max(0, t - t0 - 0.2) * 4)
        put(canvas, sp.img, sp.x, sp.y, sc, a)


def pill(ctx: Ctx, text: str, size: float = 34, fill: str | None = None, color: str | None = None, weight: int = 800,
         fill_alpha: float = 1.0, min_w: int = 0) -> Image.Image:
    th = ctx.th
    f = ctx.font(BODY, size, weight)
    asc, desc = f.getmetrics()
    tw = f.getlength(text)
    px, py = int(f.size * 0.75), int(f.size * 0.38)
    img = Image.new("RGBA", (max(min_w, int(tw) + 2 * px), asc + desc + 2 * py), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=img.height // 2,
                        fill=rgba(fill or th["accent"], fill_alpha))
    d.text((px, py), text, font=f, fill=rgba(color or th["on_accent"]), anchor="la")
    return img


# ---------------------------------------------------------------- pictures

@lru_cache(maxsize=64)
def _picture_src(name: str) -> str:
    p = Path(name).expanduser()
    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and p.exists():
        return str(p)
    from ..lesson import assets
    return str(assets.fetch(name))


@lru_cache(maxsize=128)
def picture(name: str, box: int) -> Image.Image:
    img = Image.open(_picture_src(name)).convert("RGBA")
    r = box / max(img.width, img.height)
    img = img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)
    # soft contact shadow so the object sits in the world instead of floating on it
    sh = Image.new("RGBA", (img.width, int(img.height * 1.12)), (0, 0, 0, 0))
    ell = Image.new("L", sh.size, 0)
    ImageDraw.Draw(ell).ellipse([img.width * 0.18, img.height * 0.98, img.width * 0.82, img.height * 1.1], fill=80)
    ell = ell.filter(ImageFilter.GaussianBlur(max(2, box // 40)))
    sh.putalpha(ell)
    sh.alpha_composite(img, (0, 0))
    return sh


def cover_crop(img: Image.Image, W: int, H: int) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((max(W, int(img.width * r + 0.5)), max(H, int(img.height * r + 0.5))), Image.LANCZOS)
    l, t = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((l, t, l + W, t + H))


def scrim(W: int, H: int, strength: float = 0.75) -> Image.Image:
    """Dark at the top and bottom where text and the TikTok UI sit, clear in the middle."""
    y = np.linspace(0, 1, H)[:, None]
    a = np.clip(np.maximum((0.32 - y) / 0.32 * 0.65, (y - 0.45) / 0.55), 0, 1) * strength
    a = np.repeat((a * 255).astype("uint8"), W, axis=1)
    z = np.zeros((H, W), dtype="uint8")
    return Image.fromarray(np.stack([z, z, z, a], axis=-1), "RGBA")


class ClipReader:
    """Decode a video clip sequentially, cover-cropped to the frame, at the output fps."""

    def __init__(self, src: str, start: float, dur: float, W: int, H: int, fps: int):
        self.W, self.H = W, H
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},format=rgb24"
        self.proc = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur + 0.5:.3f}",
                                      "-i", str(Path(src).expanduser()), "-vf", vf, "-f", "rawvideo", "-"],
                                     stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.last = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        self.n = 0

    def frame(self, i: int) -> Image.Image:
        size = self.W * self.H * 3
        while self.n <= i:
            buf = self.proc.stdout.read(size) if self.proc.stdout else b""
            if len(buf) < size:
                break
            self.last = Image.frombuffer("RGB", (self.W, self.H), buf).convert("RGBA")
            self.n += 1
        return self.last

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()


# ---------------------------------------------------------------- scenes

@dataclass
class Scene:
    ctx: Ctx
    beat: dict
    start: float
    dur: float
    lead: float
    narr: float
    times: list[dict]          # word timings relative to narration start
    prep: dict = field(default_factory=dict)

    @property
    def v(self) -> dict:
        return self.beat["visual"]

    def cue(self, word: str | None, default: float) -> float:
        from .voice import find_word
        if not word or not self.times:
            return default
        return self.lead + find_word(self.times, word, default - self.lead)

    def word_starts(self, n: int, span: tuple[float, float] | None = None) -> list[float]:
        a, b = span or (self.lead, self.lead + max(0.3, min(self.narr, 1.2)))
        return [a + (b - a) * i / max(1, n) for i in range(n)]

    def events(self) -> list[dict]:
        """Sound effects this scene asks for (local time)."""
        return []

    def is_media(self) -> bool:
        return self.v["type"] in ("image", "clip") or bool(self.v.get("image"))

    def draw(self, canvas: Image.Image, t: float, i: int) -> None:  # t local seconds, i local frame
        getattr(self, "draw_" + self.v["type"])(canvas, t, i)

    # ---- hook: frame 0 already says the claim
    def _hook_prep(self):
        ctx, v, th = self.ctx, self.v, self.ctx.th
        p = self.prep
        has_pic = bool(v.get("picture"))
        lines = v["lines"]
        gap = ctx.px(26)
        if v.get("kicker"):
            p["kicker"] = pill(ctx, v["kicker"].upper(), 32, fill=th["ink"], color=th["bg"])
        if has_pic:
            p["pic"] = picture(v["picture"], int(ctx.W * 0.32))
        media = self.is_media()
        if media:  # a photo / AI image behind the hook: full bleed, darkened where the text sits
            p["bg"] = cover_crop(Image.open(Path(v["image"]).expanduser()).convert("RGBA"), ctx.W, ctx.H)
            p["bg"].alpha_composite(scrim(ctx.W, ctx.H, 0.85))
        l1 = block(ctx, lines[0], DISPLAY, None, 150, ctx.cx, 0, max_lines=2, highlight=v.get("highlight"),
                   upper=True, stroke=ctx.px(5) if media else 0, line_gap=0.98,
                   color="#FFFFFF" if media else None, stroke_color="#000000")
        l1_h = max(s.y + s.img.height / 2 for s in l1) - min(s.y - s.img.height / 2 for s in l1)
        l2 = None
        if len(lines) > 1:
            f, ls = fit(lines[1].upper(), DISPLAY, None, 132, ctx.safe_w * 0.94, 1, ctx)
            l2 = word_img(" ".join(ls[0]), f, th["on_accent"], box=th["accent"])
        parts = [h for h in (p.get("kicker") and p["kicker"].height, has_pic and p["pic"].height, l1_h,
                             l2 is not None and l2.height) if h]
        y = ctx.H * 0.35 - (sum(parts) + gap * (len(parts) - 1)) / 2
        y = max(y, ctx.H * STAGE_TOP)
        if "kicker" in p:
            p["kicker_y"] = y + p["kicker"].height / 2
            y += p["kicker"].height + gap
        if has_pic:
            p["pic_y"] = y + p["pic"].height / 2
            y += p["pic"].height + gap * 0.5
        top1 = min(s.y - s.img.height / 2 for s in l1)
        for s in l1:
            s.y += y - top1
        p["l1"] = l1
        y += l1_h + gap * 0.6
        if l2 is not None:
            p["l2"] = (l2, ctx.cx, y + l2.height / 2)
        p["punch"] = self.cue(v.get("punch_cue"), self.lead + max(0.35, self.narr * 0.5))

    def draw_hook(self, canvas, t, i):
        if "l1" not in self.prep:
            self._hook_prep()
        ctx, p = self.ctx, self.prep
        drift = 1.0 + 0.025 * E.clamp(t / max(1, self.dur))
        if "bg" in p:
            canvas.alpha_composite(p["bg"])
        if "pic" in p:
            bob = math.sin(t * 2.2) * ctx.px(8)
            put(canvas, p["pic"], ctx.cx, p["pic_y"] + bob, drift)
        if "kicker" in p:
            put(canvas, p["kicker"], ctx.cx, p["kicker_y"])
        for sp in p["l1"]:  # visible on frame 0, no fade-in: frame 0 is the thumbnail and the scroll-stop
            put(canvas, sp.img, ctx.cx + (sp.x - ctx.cx) * drift, ctx.H * 0.35 + (sp.y - ctx.H * 0.35) * drift, drift)
        if "l2" in p:
            img, x, y = p["l2"]
            sc, a = slam(t, p["punch"])
            shake = math.exp(-max(0.0, t - p["punch"]) * 18) * ctx.px(14) if t >= p["punch"] else 0
            put(canvas, img, x + shake * math.sin(t * 90), y + shake * math.cos(t * 70), sc * drift, a, angle=-2.0)

    def events_hook(self):
        if "l1" not in self.prep:
            self._hook_prep()
        return [{"kind": "hit", "at": self.prep["punch"], "gain_db": -3}] if "l2" in self.prep else []

    # ---- text
    def draw_text(self, canvas, t, i):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        if "w" not in p:
            has_pic = bool(v.get("picture"))
            p["w"] = block(ctx, v["text"], BODY, 900, 96, ctx.cx, ctx.H * (0.44 if has_pic else 0.37), max_lines=4,
                           highlight=v.get("highlight"), stroke=ctx.px(4) if self.is_media() else 0)
            p["starts"] = self.word_starts(len(p["w"]))
            if v.get("kicker"):
                p["k"] = pill(ctx, v["kicker"].upper(), 30, fill=th["ink"], color=th["bg"])
            if has_pic:
                p["pic"] = picture(v["picture"], int(ctx.W * 0.3))
        if "pic" in p:
            sc, a = pop(t, 0.0)
            put(canvas, p["pic"], ctx.cx, ctx.H * 0.25 + math.sin(t * 2.4) * ctx.px(8), sc, a)
        if "k" in p:
            put(canvas, p["k"], ctx.cx, ctx.H * (0.135 if "pic" in p else 0.22))
        draw_words(canvas, p["w"], t, p["starts"])

    # ---- stat: a number that counts on its cue
    def draw_stat(self, canvas, t, i):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        if "t0" not in p:
            p["t0"] = self.cue(v.get("cue"), self.lead)
            p["label"] = block(ctx, v["label"], BODY, 800, 62, ctx.cx, ctx.H * 0.49, max_lines=2, color=th["muted"],
                               highlight=v.get("highlight"))
            if v.get("picture"):
                p["pic"] = picture(v["picture"], int(ctx.W * 0.24))
        t_land = max(0.7, p["t0"] + 0.1)  # the number lands on the word that says it
        t_go = max(0.0, min(0.1, t_land - 0.7))
        val = float(v["value"])
        frm = float(v.get("from", 0))
        k = E.in_out_cubic(E.clamp((t - t_go) / (t_land - t_go)))
        cur = frm + (val - frm) * k
        txt = f"{v.get('prefix', '')}{fmt_num(cur, v['value'], ctx.lang)}{v.get('suffix', '')}"
        f = ctx.font(DISPLAY, 270)
        while f.getlength(txt) > ctx.safe_w and f.size > 60:
            f = fonts.get(DISPLAY, int(f.size * 0.92))
        col = th["accent"] if k >= 0.999 else th["ink"]
        img = word_img(txt, f, col)
        sc = 1.0 + 0.12 * math.exp(-(t - t_land) * 7) if t >= t_land else 1.0
        put(canvas, img, ctx.cx, ctx.H * 0.36, sc)
        if "pic" in p:
            sc2, a2 = pop(t, 0.0)
            put(canvas, p["pic"], ctx.cx, ctx.H * 0.2, sc2, a2)
        draw_words(canvas, p["label"], t, [0.12 + 0.04 * j for j in range(len(p["label"]))])

    def events_stat(self):
        t0 = self.cue(self.v.get("cue"), self.lead)
        return [{"kind": "pop", "at": max(0.7, t0 + 0.1), "gain_db": -6}]

    # ---- picture: familiar objects act the idea out
    def draw_picture(self, canvas, t, i):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        n = max(1, min(6, int(v.get("count", 1))))
        if "img" not in p:
            box = int(ctx.W * (0.5 if n == 1 else 0.27 if n <= 3 else 0.2))
            p["img"] = picture(v["asset"], box)
            cols = n if n <= 3 else math.ceil(n / 2)
            rows = 1 if n <= 3 else 2
            gap = box * 1.05
            p["pos"] = []
            for j in range(n):
                r, c = divmod(j, cols)
                in_row = cols if r < rows - 1 else n - cols * (rows - 1)
                x = ctx.cx + (c - (in_row - 1) / 2) * gap
                y = ctx.H * 0.33 + (r - (rows - 1) / 2) * gap * 0.95
                p["pos"].append((x, y))
            p["t_act"] = self.cue(v.get("cue"), self.lead + self.narr * 0.45)
            if v.get("caption"):
                p["cap"] = block(ctx, v["caption"], BODY, 900, 74, ctx.cx, ctx.H * 0.53, max_lines=2,
                                 highlight=v.get("highlight"))
        act, ta = v.get("act", "pop"), p["t_act"]
        for j, (x, y) in enumerate(p["pos"]):
            sc, a = pop(t, j * 0.12, 0.3, 0.3)
            ang, dy = 0.0, 0.0
            after = max(0.0, t - ta) if t >= ta else None
            if act == "float":
                dy = math.sin(t * 2.0 + j) * ctx.px(14)
            elif act == "shake" and after is not None:
                ang = math.sin(after * 40) * 10 * math.exp(-after * 2.5)
            elif act == "grow" and after is not None:
                sc *= 1 + 0.4 * E.out_back(E.clamp(after / 0.5))
            elif act == "shrink" and after is not None:
                sc *= 1 - 0.45 * E.out_cubic(E.clamp(after / 0.5))
            elif act == "fall" and after is not None:
                k = E.out_back(E.clamp(after / 0.6), 1.2)
                dy, ang, sc, a = k * ctx.H * 0.07, k * 80, sc * (1 - 0.3 * k), a * (1 - 0.35 * k)
            elif act == "bounce" and after is not None:
                dy = -abs(math.sin(after * 7)) * ctx.px(60) * math.exp(-after * 2)
            else:
                dy = math.sin(t * 1.6 + j) * ctx.px(6)
            put(canvas, p["img"], x, y + dy, sc, a, ang)
        if "cap" in p:
            draw_words(canvas, p["cap"], t, [0.25 + 0.05 * j for j in range(len(p["cap"]))])

    def events_picture(self):
        act = self.v.get("act", "pop")
        out = [{"kind": "pop", "at": 0.05, "gain_db": -8}]
        if act in ("fall", "shake", "grow", "shrink", "bounce"):
            out.append({"kind": "hit" if act == "fall" else "whoosh", "at": self.cue(self.v.get("cue"), self.lead + self.narr * 0.45), "gain_db": -7})
        return out

    # ---- image / clip: full-bleed media with a slow move
    def draw_image(self, canvas, t, i):
        ctx, v, p = self.ctx, self.v, self.prep
        if "src" not in p:
            img = Image.open(Path(v["src"]).expanduser()).convert("RGBA")
            p["src"] = cover_crop(img, int(ctx.W * 1.14), int(ctx.H * 1.14))
            p["scrim"] = scrim(ctx.W, ctx.H)
            self._media_text()
        k = E.in_out_sine(E.clamp(t / max(0.1, self.dur)))
        src = p["src"]
        mv = v.get("move", "in")
        z = {"in": 1.0 + 0.12 * k, "out": 1.12 - 0.12 * k}.get(mv, 1.06)
        cw = src.width / z  # src is 1.14x the frame: z=1 shows all of it, z=1.12 a tighter window
        ch = cw * ctx.H / ctx.W
        ox = {"left": (src.width - cw) * (1 - k), "right": (src.width - cw) * k}.get(mv, (src.width - cw) / 2)
        oy = {"up": (src.height - ch) * (1 - k), "down": (src.height - ch) * k}.get(mv, (src.height - ch) / 2)
        frame = src.resize((ctx.W, ctx.H), Image.BILINEAR, box=(ox, oy, ox + cw, oy + ch))
        canvas.alpha_composite(frame)
        canvas.alpha_composite(p["scrim"])
        self._draw_media_text(canvas, t)

    def draw_clip(self, canvas, t, i):
        ctx, v, p = self.ctx, self.v, self.prep
        if "reader" not in p:
            p["reader"] = ClipReader(v["src"], float(v.get("start", 0)), self.dur, ctx.W, ctx.H, ctx.fps)
            p["scrim"] = scrim(ctx.W, ctx.H)
            self._media_text()
        canvas.alpha_composite(p["reader"].frame(i))
        canvas.alpha_composite(p["scrim"])
        self._draw_media_text(canvas, t)

    def _media_text(self):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        if v.get("caption"):
            p["cap"] = block(ctx, v["caption"], BODY, 900, 80, ctx.cx, ctx.H * 0.2, max_lines=2, color="#FFFFFF",
                             highlight=v.get("highlight"), stroke=ctx.px(5), stroke_color="#000000", hl_color="#FFD23F")
        if v.get("credit"):
            f = ctx.font(BODY, 24, 600)
            p["credit"] = word_img(v["credit"], f, "#FFFFFF", stroke=ctx.px(2), stroke_color="#000000")

    def _draw_media_text(self, canvas, t):
        p, ctx = self.prep, self.ctx
        if "cap" in p:
            draw_words(canvas, p["cap"], t, [0.15 + 0.05 * j for j in range(len(p["cap"]))])
        if "credit" in p:
            put(canvas, p["credit"], ctx.W * SAFE_L + p["credit"].width / 2, ctx.H * 0.585, 1.0, 0.8)

    # ---- list: items land on their cue words
    def _list_prep(self):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        items = [it if isinstance(it, str) else it.get("text", "") for it in v["items"]]
        n = len(items)
        top = ctx.H * (0.25 if v.get("title") else 0.2)
        gap = min(ctx.H * 0.085, (ctx.H * 0.56 - top) / max(1, n))
        if v.get("title"):
            p["title"] = block(ctx, v["title"], DISPLAY, None, 104, ctx.cx, ctx.H * 0.155, max_lines=2, upper=True)
        cues = v.get("cues") or []
        default = self.word_starts(n, (self.lead, self.lead + self.narr * 0.85))
        p["t"] = [self.cue(cues[j] if j < len(cues) else None, default[j]) for j in range(n)]
        p["rows"] = []
        x_text = ctx.W * SAFE_L + ctx.px(112)
        fb = ctx.font(DISPLAY, 56)
        for j, it in enumerate(items):
            y = top + gap * (j + 0.5)
            r = ctx.px(40)
            badge = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
            d = ImageDraw.Draw(badge)
            d.ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=rgba(th["accent"]))
            d.text((r, r), str(j + 1), font=fb, fill=rgba(th["on_accent"]), anchor="mm")
            f, ls = fit(it, BODY, 800, 58, ctx.W * SAFE_R - x_text, 2, ctx)
            txt = word_img(" ".join(ls[0]), f, th["ink"])
            if len(ls) > 1:
                l2 = word_img(" ".join(ls[1]), f, th["ink"])
                both = Image.new("RGBA", (max(txt.width, l2.width), txt.height + l2.height), (0, 0, 0, 0))
                both.alpha_composite(txt, (0, 0))
                both.alpha_composite(l2, (0, txt.height))
                txt = both
            p["rows"].append((badge, ctx.W * SAFE_L + r, y, txt, x_text + txt.width / 2, y))

    def draw_list(self, canvas, t, i):
        if "rows" not in self.prep:
            self._list_prep()
        p = self.prep
        if "title" in p:
            draw_words(canvas, p["title"], t)
        cur = max([j for j, tj in enumerate(p["t"]) if t >= tj] or [-1])
        for j, (badge, bx, by, txt, tx, ty) in enumerate(p["rows"]):
            sc, a = pop(t, p["t"][j])
            if a <= 0:
                continue
            dimmed = 0.55 if j < cur else 1.0
            put(canvas, badge, bx, by, sc, a)
            slide = (1 - E.out_cubic(E.clamp((t - p["t"][j]) / 0.25))) * self.ctx.px(40)
            put(canvas, txt, tx + slide, ty, 1.0, a * dimmed)

    def events_list(self):
        if "rows" not in self.prep:
            self._list_prep()
        return [{"kind": "pop", "at": tj, "gain_db": -9} for tj in self.prep["t"]]

    # ---- compare: two pictures side by side, VS
    def draw_compare(self, canvas, t, i):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        if "cols" not in p:
            p["t_right"] = self.cue(v.get("cue"), self.lead + self.narr * 0.45)
            if v.get("title"):
                p["title"] = block(ctx, v["title"], DISPLAY, None, 96, ctx.cx, ctx.H * 0.15, max_lines=2, upper=True)
            cols = []
            for side, x in (("left", ctx.W * 0.28), ("right", ctx.W * 0.64)):
                c = v[side]
                el = {"x": x}
                if c.get("picture"):
                    el["pic"] = picture(c["picture"], int(ctx.W * 0.27))
                el["label"] = block(ctx, str(c.get("label", "")), BODY, 800, 50, x, ctx.H * 0.43, max_w=ctx.W * 0.32, max_lines=2)
                if c.get("value") is not None:
                    el["value"] = word_img(str(c["value"]), ctx.font(DISPLAY, 112),
                                           th["accent"] if side == "right" else th["ink"])
                cols.append(el)
            p["cols"] = cols
            r = ctx.px(52)
            vs = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
            d = ImageDraw.Draw(vs)
            d.ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=rgba(th["ink"]))
            d.text((r, r), "VS", font=ctx.font(DISPLAY, 48), fill=rgba(th["bg"]), anchor="mm")
            p["vs"] = vs
        if "title" in p:
            draw_words(canvas, p["title"], t)
        for j, el in enumerate(p["cols"]):
            t0 = 0.05 if j == 0 else p["t_right"]
            sc, a = pop(t, t0, 0.3, 0.4)
            if "pic" in el:
                put(canvas, el["pic"], el["x"], ctx.H * 0.3, sc, a)
            draw_words(canvas, el["label"], t, [t0 + 0.1] * len(el["label"]))
            if "value" in el:
                s2, a2 = pop(t, t0 + 0.15)
                put(canvas, el["value"], el["x"], ctx.H * 0.5, s2, a2)
        sc, a = pop(t, p["t_right"] - 0.1)
        put(canvas, p["vs"], ctx.W * 0.46, ctx.H * 0.3, sc, a)

    def events_compare(self):
        return [{"kind": "whoosh", "at": self.cue(self.v.get("cue"), self.lead + self.narr * 0.45), "gain_db": -9}]

    # ---- question: pause and think (drives comments)
    def _q_times(self):
        v = self.v
        t_end = self.lead + self.narr
        think = float(v.get("think_seconds", 3.0))
        return t_end, t_end + think

    def draw_question(self, canvas, t, i):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        if "q" not in p:
            p["k"] = pill(ctx, "ĐỐ BẠN" if ctx.lang == "vi" else "QUICK QUIZ", 32)
            p["q"] = block(ctx, v["question"], BODY, 900, 76, ctx.cx, ctx.H * 0.25, max_lines=3)
            p["ch"] = []
            for j, c in enumerate(v.get("choices", [])):
                label = f"{'ABCD'[j]}. {c}"
                mw = int(ctx.safe_w * 0.96)
                p["ch"].append((c, pill(ctx, label, 44, fill=th["ink"], color=th["ink"], weight=700, fill_alpha=0.13, min_w=mw),
                                pill(ctx, label, 44, fill=th["hl"], color=th["on_accent"], weight=800, min_w=mw)))
            p["ans_alone"] = None
            if v.get("answer") and v["answer"] not in v.get("choices", []):
                p["ans_alone"] = pill(ctx, v["answer"], 46, fill=th["hl"], color=th["on_accent"])
        t_end, t_ans = self._q_times()
        put(canvas, p["k"], ctx.cx, ctx.H * 0.135)
        draw_words(canvas, p["q"], t)
        for j, (c, off, on) in enumerate(p["ch"]):
            y = ctx.H * (0.37 + 0.068 * j)
            sc, a = pop(t, self.lead + 0.25 + 0.12 * j)
            right = t >= t_ans and c == v.get("answer")
            wrong = t >= t_ans and not right
            put(canvas, on if right else off, ctx.cx, y, sc * (1.04 if right else 1.0), a * (0.45 if wrong else 1.0))
        if t_end <= t < t_ans:  # countdown ring
            left = t_ans - t
            r = ctx.px(62)
            ring = Image.new("RGBA", (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
            d = ImageDraw.Draw(ring)
            d.ellipse([4, 4, 2 * r + 4, 2 * r + 4], outline=rgba(th["muted"], 0.5), width=ctx.px(8))
            frac = left / max(0.1, t_ans - t_end)
            d.arc([4, 4, 2 * r + 4, 2 * r + 4], -90, -90 + 360 * frac, fill=rgba(th["accent"]), width=ctx.px(8))
            d.text((r + 4, r + 4), str(int(math.ceil(left))), font=ctx.font(DISPLAY, 70), fill=rgba(th["ink"]), anchor="mm")
            put(canvas, ring, ctx.cx, ctx.H * 0.62)
        if p["ans_alone"] is not None:
            sc, a = pop(t, t_ans)
            put(canvas, p["ans_alone"], ctx.cx, ctx.H * 0.6, sc, a)

    def events_question(self):
        t_end, t_ans = self._q_times()
        ev = [{"kind": "tick", "at": t_end + k, "gain_db": -10} for k in range(int(t_ans - t_end))]
        return ev + [{"kind": "hit", "at": t_ans, "gain_db": -6}]

    # ---- end: close the loop, one CTA
    def draw_end(self, canvas, t, i):
        ctx, v, p, th = self.ctx, self.v, self.prep, self.ctx.th
        if "w" not in p:
            p["w"] = block(ctx, v["text"], BODY, 900, 88, ctx.cx, ctx.H * 0.33, max_lines=4, highlight=v.get("highlight"))
            p["starts"] = self.word_starts(len(p["w"]))
            if v.get("cta"):
                p["cta"] = pill(ctx, v["cta"], 46)
            if v.get("handle"):
                p["handle"] = word_img(v["handle"], ctx.font(BODY, 40, 700), th["muted"])
            if v.get("next"):
                p["next"] = pill(ctx, v["next"], 32, fill=th["ink"], color=th["bg"])
            p["t_cta"] = max(0.5, self.lead + self.narr * 0.5)
            if v.get("disclaimer"):
                p["disc"] = block(ctx, v["disclaimer"], BODY, 500, 26, ctx.cx, ctx.H * 0.6, max_lines=3, color=th["muted"])
        if "next" in p:
            sc, a = pop(t, 0.1)
            put(canvas, p["next"], ctx.cx, ctx.H * 0.18, sc, a)
        draw_words(canvas, p["w"], t, p["starts"])
        if "cta" in p:
            sc, a = pop(t, p["t_cta"], 0.3)
            pulse = 1 + 0.03 * math.sin(max(0, t - p["t_cta"] - 0.4) * 6) if t > p["t_cta"] + 0.4 else 1
            put(canvas, p["cta"], ctx.cx, ctx.H * 0.49, sc * pulse, a)
        if "handle" in p:
            sc, a = pop(t, p["t_cta"] + 0.2)
            put(canvas, p["handle"], ctx.cx, ctx.H * 0.545, 1.0, a)
        if "disc" in p:
            draw_words(canvas, p["disc"], t)

    def events_end(self):
        return [{"kind": "pop", "at": max(0.5, self.lead + self.narr * 0.5), "gain_db": -8}]

    def scene_events(self) -> list[dict]:
        fn = getattr(self, "events_" + self.v["type"], None)
        return fn() if fn else []

    def close(self):
        if "reader" in self.prep:
            self.prep["reader"].close()


def fmt_num(x: float, like, lang: str) -> str:
    s = str(like)
    dec = len(s.split(".")[1]) if "." in s and isinstance(like, float) else 0
    txt = f"{x:,.{dec}f}"
    if lang == "vi":  # 1.000.000,5
        txt = txt.replace(",", "§").replace(".", ",").replace("§", ".")
    return txt


# ---------------------------------------------------------------- background, captions, chrome

class Background:
    def __init__(self, ctx: Ctx, seed: int = 3):
        th = ctx.th
        W, H = ctx.W, ctx.H
        y = np.linspace(0, 1, H)[:, None, None]
        a, b = np.array(hex_rgb(th["bg"]), "float32"), np.array(hex_rgb(th["bg2"]), "float32")
        grad = a + (b - a) * (0.5 - 0.5 * np.cos(np.pi * y))
        self.base = np.repeat(grad, W, axis=1)
        gw, gh = int(W * 1.2), int(W * 1.2)
        yy, xx = np.mgrid[0:gh, 0:gw]
        r = np.sqrt((xx - gw / 2) ** 2 + (yy - gh / 2) ** 2) / (gw / 2)
        g = np.clip(1 - r, 0, 1) ** 2 * (0.16 if th["bg"] != THEMES["paper"]["bg"] else 0.35)
        self.glow = g[..., None] * np.array(hex_rgb(th["glow"]), "float32")[None, None, :]
        self.glow_a = g[..., None]
        rng = np.random.default_rng(seed)
        self.grain = [rng.normal(0, 255 * th["grain"], (H // 2, W // 2, 1)).astype("float32") for _ in range(4)]
        self.ctx = ctx

    def frame(self, t: float) -> Image.Image:
        ctx = self.ctx
        img = self.base.copy()
        gh, gw = self.glow.shape[:2]
        cx = int(ctx.W * (0.5 + 0.18 * math.sin(t * 0.35)) - gw / 2)
        cy = int(ctx.H * (0.36 + 0.06 * math.cos(t * 0.27)) - gh / 2)
        x0, y0, x1, y1 = max(0, cx), max(0, cy), min(ctx.W, cx + gw), min(ctx.H, cy + gh)
        if x1 > x0 and y1 > y0:
            sl = (slice(y0 - cy, y1 - cy), slice(x0 - cx, x1 - cx))
            region = img[y0:y1, x0:x1]
            img[y0:y1, x0:x1] = region * (1 - self.glow_a[sl]) + self.glow[sl]
        gr = self.grain[int(t * 12) % len(self.grain)]
        img += np.repeat(np.repeat(gr, 2, axis=0), 2, axis=1)[: ctx.H, : ctx.W]
        arr = np.clip(img, 0, 255).astype("uint8")
        return Image.fromarray(np.concatenate([arr, np.full((ctx.H, ctx.W, 1), 255, "uint8")], axis=-1), "RGBA")


def chunk_words(words: list[dict], max_words: int) -> list[list[dict]]:
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > 0.3):
            out.append(cur)
            cur = []
        cur.append(w)
        if w["word"][-1:] in ".,!?;:…":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


class Captions:
    """Karaoke captions: 2-4 words at a time, the spoken word lit in the highlight colour."""

    def __init__(self, ctx: Ctx, words: list[dict], max_words: int):
        self.ctx = ctx
        self.chunks = chunk_words(words, max_words)
        self.spans = []
        for k, c in enumerate(self.chunks):
            end = self.chunks[k + 1][0]["start"] if k + 1 < len(self.chunks) else c[-1]["end"] + 0.4
            end = min(end, c[-1]["end"] + 0.6)
            self.spans.append((c[0]["start"], end))
        self.cache: dict[int, tuple] = {}

    def _prep(self, k: int):
        if k in self.cache:
            return self.cache[k]
        ctx, th = self.ctx, self.ctx.th
        c = self.chunks[k]
        f, lines = fit(" ".join(w["word"] for w in c), BODY, 800, 66, ctx.safe_w * 0.95, 2, ctx)
        sw = ctx.px(7)
        sp = f.getlength(" ")
        asc, desc = f.getmetrics()
        lh = (asc + desc) * 1.05
        items, idx = [], 0
        y0 = ctx.H * CAPTION_Y - lh * (len(lines) - 1) / 2
        for li, line in enumerate(lines):
            imgs = []
            for w in line:
                imgs.append((word_img(w, f, th["ink"], sw, th["stroke"]),
                             word_img(w, f, th["hl"], sw, th["stroke"]), c[idx]))
                idx += 1
            total = sum(a.width for a, _, _ in imgs) + (sp - sw) * (len(imgs) - 1)
            x = ctx.cx - total / 2
            for a, b, wd in imgs:
                items.append((a, b, x + a.width / 2, y0 + li * lh, wd))
                x += a.width + sp - sw
        self.cache[k] = items
        return items

    def draw(self, canvas: Image.Image, t: float, hidden: list[tuple[float, float]]) -> None:
        if any(a <= t < b for a, b in hidden):
            return
        for k, (a, b) in enumerate(self.spans):
            if a <= t < b:
                sc = 0.85 + 0.15 * E.out_back(E.clamp((t - a) / 0.12), 2.0)
                for off, on, x, y, wd in self._prep(k):
                    active = wd["start"] <= t < max(wd["end"], wd["start"] + 0.12)
                    put(canvas, on if active else off, self.ctx.cx + (x - self.ctx.cx) * sc, y, sc * (1.06 if active else 1.0))
                return


def progress_bar(canvas: Image.Image, t: float, total: float, ctx: Ctx) -> None:
    d = ImageDraw.Draw(canvas)
    h = max(3, ctx.px(7))
    d.rectangle([0, 0, int(ctx.W * min(1, t / total)), h], fill=rgba(ctx.th["accent"]))
