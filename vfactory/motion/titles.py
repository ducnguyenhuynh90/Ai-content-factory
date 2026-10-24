"""Title sequences. Each animation has an intro, a hold, and an outro, and reports
`hits` — the frames where something lands — so sound design can hit on the frame."""

from __future__ import annotations

import math
from dataclasses import replace

from PIL import Image, ImageDraw

from .. import easing as E
from ..styles import Look, hex_rgb
from .core import Animation, Glyphs, TextStyle, apply_case, clip_rect, fit_text, paste, radial_bg, rgba, transform


def _luma(hexcol: str) -> float:
    r, g, b = hex_rgb(hexcol)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class TitleBase(Animation):
    intro = 2.0
    outro = 0.8

    def __init__(self, look: Look, width: int, height: int, fps: int, duration: float,
                 title: str, kicker: str = "", subtitle: str = "", card: bool = False, scrim: bool = True,
                 scale: float = 1.0, keep_ink: bool = False):
        self.look, self.width, self.height, self.fps, self.duration = look, width, height, fps, duration
        self.title, self.kicker, self.subtitle = title, kicker, subtitle
        self.opaque, self.scrim = card, scrim and not card
        self.u = min(width, height) * scale
        self.max_w = width * 0.84
        self.pal, self.ty = look.palette, look.type
        if not card and not keep_ink and _luma(self.pal.fg) < 128:
            # Dark ink is for the look's light cards; over footage, type must be light.
            self.pal = replace(self.pal, fg="#FFFFFF", muted="#D9D9D6")
        self.hits: list[float] = []
        self._bg = radial_bg((width, height), self.pal.bg) if card else None
        self._scrim = self._make_scrim() if self.scrim else None
        self.setup()

    # -- helpers ---------------------------------------------------------
    def setup(self) -> None:
        pass

    def canvas(self, t: float) -> Image.Image:
        if self._bg is not None:
            return self._bg.copy()
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        if self._scrim is not None:
            a = E.out_cubic(E.progress(t, 0, 0.6)) * (1 - E.in_cubic(E.progress(t, self.duration - self.outro, self.outro)))
            img.alpha_composite(self._with_alpha(self._scrim, a))
        return img

    def _with_alpha(self, img, a):
        from .core import with_alpha
        return with_alpha(img, a)

    def _make_scrim(self) -> Image.Image:
        # Soft radial darkening behind the type: legibility over any footage without a visible box.
        import numpy as np

        w, h = self.width, self.height
        yy, xx = np.mgrid[0:h, 0:w].astype("float32")
        d = np.sqrt(((xx - w / 2) / (w * 0.55)) ** 2 + ((yy - h / 2) / (h * 0.42)) ** 2)
        a = (np.clip(1 - d, 0, 1) ** 1.2 * 150).astype("uint8")
        arr = np.zeros((h, w, 4), dtype="uint8")
        arr[..., 3] = a
        return Image.fromarray(arr, "RGBA")

    def _ink_top(self, line_center: float) -> float:
        """Screen y of the cap tops for a line pasted centred ('mm') at line_center."""
        f = self.ts.pil()
        asc, desc = f.getmetrics()
        return line_center - (asc + desc) / 2 + f.getbbox("H")[1]

    def _ink_bottom(self, line_center: float) -> float:
        f = self.ts.pil()
        asc, desc = f.getmetrics()
        return line_center - (asc + desc) / 2 + f.getbbox("H")[3]

    def out_p(self, t: float) -> float:
        """0 during intro/hold, ramps 0->1 over the outro."""
        return E.progress(t, self.duration - self.outro, self.outro)

    def style(self, role: str, size: float) -> TextStyle:
        ty = self.ty
        if role == "display":
            return TextStyle(ty.display, int(size), ty.display_weight, ty.display_tracking, self.pal.fg)
        if role == "kicker":
            return TextStyle(ty.kicker, int(size), ty.kicker_weight, ty.kicker_tracking, self.pal.muted)
        return TextStyle(ty.body, int(size), ty.body_weight, 0.02, self.pal.muted)


class TrackingReveal(TitleBase):
    """Prestige: letters converge from wide tracking, blur-to-sharp; hairline draws from centre."""

    intro, outro = 2.4, 1.0

    def setup(self):
        title = apply_case(self.title, self.ty.display_case)
        self.lines, self.ts = fit_text(title, self.style("display", self.u * 0.105), self.max_w * 0.86, max_lines=2)
        self.glyphs = [Glyphs(line, self.ts) for line in self.lines]
        self.kick = Glyphs(apply_case(self.kicker, "upper"), self.style("kicker", self.u * 0.026)) if self.kicker else None
        self.sub = Glyphs(self.subtitle, self.style("body", self.u * 0.03)) if self.subtitle else None
        self.hits = [0.45]

    def frame(self, t):
        img = self.canvas(t)
        cx, cy = self.width / 2, self.height / 2
        o = self.out_p(t)
        out_a = 1 - E.in_out_cubic(o)
        lh = self.ts.size * 1.08
        block_h = lh * len(self.glyphs)
        top = cy - block_h / 2
        # kicker
        if self.kick:
            p = E.progress(t, 0.0, 1.0)
            k = self.kick.render(tracking=self.ty.kicker_tracking + 0.35 * (1 - E.out_expo(p)), alpha=E.out_cubic(p) * out_a)
            paste(img, k, cx, top - self.u * 0.075, "mm")
        # hairline
        p = E.in_out_cubic(E.progress(t, 0.3, 1.2))
        if p > 0:
            d = ImageDraw.Draw(img)
            half = self.max_w * 0.11 * p
            y = top - self.u * 0.035
            d.line([(cx - half, y), (cx + half, y)], fill=rgba(self.pal.accent, 0.9 * out_a), width=max(1, int(self.u * 0.0022)))
        # title
        p = E.progress(t, 0.45, self.intro - 0.45)
        for i, g in enumerate(self.glyphs):
            pi = E.progress(t, 0.45 + i * 0.18, self.intro - 0.45)
            track = self.ts.tracking + 0.45 * (1 - E.out_expo(pi)) + 0.08 * E.in_cubic(o)
            a = E.out_cubic(E.progress(t, 0.45 + i * 0.18, 1.1)) * out_a
            im = g.render(tracking=track, alpha=a)
            blur = 10 * (1 - E.out_cubic(E.progress(t, 0.45 + i * 0.18, 1.2))) + 6 * E.in_cubic(o)
            paste(img, transform(im, blur=blur, scale=1 + 0.03 * (1 - E.out_expo(pi))), cx, top + lh * (i + 0.5), "mm")
        # subtitle
        if self.sub:
            p = E.out_cubic(E.progress(t, self.intro - 0.5, 0.9))
            im = self.sub.render(alpha=p * out_a)
            paste(img, im, cx, top + block_h + self.u * 0.05 + 14 * (1 - p), "mt")
        return img


class MaskRise(TitleBase):
    """Editorial: an accent bar wipes, then words rise from behind an invisible line, staggered."""

    intro, outro = 1.4, 0.6

    def setup(self):
        title = apply_case(self.title, self.ty.display_case)
        self.lines, self.ts = fit_text(title, self.style("display", self.u * 0.11), self.max_w, max_lines=2)
        self.words = [[Glyphs(w, self.ts) for w in line.split()] for line in self.lines]
        self.space = Glyphs("n", self.ts).width * 0.55
        self.kick = Glyphs(apply_case(self.kicker, "upper"), self.style("kicker", self.u * 0.024)) if self.kicker else None
        self.sub = Glyphs(self.subtitle, self.style("body", self.u * 0.032)) if self.subtitle else None
        self.hits = [0.25]

    def frame(self, t):
        img = self.canvas(t)
        o = self.out_p(t)
        lh = self.ts.size * 1.05
        line_ws = [sum(w.width for w in ws) + self.space * (len(ws) - 1) for ws in self.words]
        block_w = max(line_ws)
        left = (self.width - block_w) / 2
        top = self.height / 2 - lh * len(self.words) / 2
        # accent bar
        p_in = E.out_expo(E.progress(t, 0.0, 0.55))
        p_out = E.in_expo(E.progress(t, self.duration - self.outro, self.outro * 0.8))
        bar_h = max(3, int(self.u * 0.008))
        x0 = left + block_w * p_out
        x1 = left + block_w * min(0.18, p_in * 0.18) if self.kick is None else left + self.u * 0.08 * p_in
        if x1 > x0:
            ImageDraw.Draw(img).rectangle([x0, top - self.u * 0.05, x1, top - self.u * 0.05 + bar_h], fill=rgba(self.pal.accent))
        if self.kick:
            p = E.out_cubic(E.progress(t, 0.2, 0.6))
            k = self.kick.render(alpha=p * (1 - E.in_cubic(o)), color=self.pal.accent)
            paste(img, k, left + self.u * 0.1 - (1 - p) * 20, top - self.u * 0.05 + bar_h / 2, "lm")
        n = 0
        for li, ws in enumerate(self.words):
            x = left  # editorial titles are flush-left on a shared edge
            y = top + lh * li
            for w in ws:
                start = 0.25 + n * 0.07
                pin = E.out_quint(E.progress(t, start, 0.75))
                pout = E.in_cubic(E.progress(t, self.duration - self.outro + n * 0.03, self.outro * 0.7))
                dy = lh * (1 - pin) - lh * pout
                im = w.render()
                pad = int(self.ts.size * 0.25)
                im = clip_rect(im.transform(im.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy)), (0, pad - int(self.ts.size * 0.12), im.width, pad + w.height))
                paste(img, im, x - pad, y - pad, "lt")
                x += w.width + self.space
                n += 1
        if self.sub:
            p = E.out_cubic(E.progress(t, 0.7, 0.6))
            paste(img, self.sub.render(alpha=p * (1 - E.in_cubic(o))), left, top + lh * len(self.words) + self.u * 0.035 + 10 * (1 - p), "lt")
        return img


class Slam(TitleBase):
    """Trailer: each word slams in on a beat with overshoot, camera shake and a flash."""

    intro, outro = 1.6, 0.35

    def setup(self):
        title = apply_case(self.title, self.ty.display_case)
        self.lines, self.ts = fit_text(title, self.style("display", self.u * 0.2), self.max_w, max_lines=3)
        self.words = [[Glyphs(w, self.ts) for w in line.split()] for line in self.lines]
        self.space = Glyphs("n", self.ts).width * 0.35
        count = sum(len(ws) for ws in self.words)
        self.step = min(0.38, (self.intro - 0.3) / max(1, count))
        self.hits = [0.15 + i * self.step for i in range(count)]
        self.kick = Glyphs(apply_case(self.kicker, "upper"), self.style("kicker", self.u * 0.03)) if self.kicker else None
        self.sub = Glyphs(apply_case(self.subtitle, "upper"), self.style("kicker", self.u * 0.03)) if self.subtitle else None

    def frame(self, t):
        img = self.canvas(t)
        o = self.out_p(t)
        lh = self.ts.size * 0.98
        shake = 0.0
        for h in self.hits:
            if t >= h:
                k = math.exp(-(t - h) * 22)
                shake += k * self.u * 0.012 * math.sin((t - h) * 95)
        line_ws = [sum(w.width for w in ws) + self.space * (len(ws) - 1) for ws in self.words]
        top = self.height / 2 - lh * len(self.words) / 2
        n = 0
        for li, ws in enumerate(self.words):
            x = (self.width - line_ws[li]) / 2
            for w in ws:
                h = self.hits[n]
                if t >= h - 1e-6:
                    p = E.out_expo(E.progress(t, h, 0.28))
                    scale = 1.55 - 0.55 * p + 0.06 * E.out_cubic(o)
                    blur = 8 * (1 - p) + 10 * E.in_cubic(o)
                    im = transform(w.render(), scale=scale, blur=blur, alpha=(1 - E.in_cubic(o)))
                    col_center = x + w.width / 2
                    paste(img, im, col_center + shake, top + lh * (li + 0.5) + shake * 0.6, "mm")
                x += w.width + self.space
                n += 1
        last = self.hits[-1] + 0.2
        for g, dy, delay in ((self.kick, -1, 0.0), (self.sub, 1, 0.1)):
            if g:
                p = E.out_expo(E.progress(t, last + delay, 0.5))
                im = g.render(alpha=p * (1 - E.in_cubic(o)), color=self.pal.accent if dy < 0 else self.pal.fg,
                              tracking=self.ty.kicker_tracking + 0.3 * (1 - p))
                y = (self._ink_top(top + lh * 0.5) - self.u * 0.035 if dy < 0
                     else self._ink_bottom(top + lh * (len(self.words) - 0.5)) + self.u * 0.04)
                paste(img, im, self.width / 2, y, "mm")
        if self.look.flash_on_hits and not self.opaque:
            fa = max((math.exp(-(t - h) * 18) for h in self.hits if t >= h), default=0) * 0.35
            if fa > 0.01:
                img.alpha_composite(Image.new("RGBA", img.size, rgba("#FFFFFF", fa)))
        return img


class TypeOn(TitleBase):
    """Documentary: a mono kicker and a grotesk title type on with a block cursor."""

    intro, outro = 2.2, 0.7

    def setup(self):
        title = apply_case(self.title, self.ty.display_case)
        self.lines, self.ts = fit_text(title, self.style("display", self.u * 0.085), self.max_w, max_lines=2)
        self.glyphs = [Glyphs(line, self.ts) for line in self.lines]
        self.kick = Glyphs(apply_case(self.kicker, "upper"), self.style("kicker", self.u * 0.024)) if self.kicker else None
        self.sub = Glyphs(self.subtitle, self.style("body", self.u * 0.026)) if self.subtitle else None
        total = sum(len(line) for line in self.lines)
        self.cps = max(14.0, total / 1.4)
        self.k_cps = 40.0
        self.t0 = (len(self.kicker) / self.k_cps + 0.2) if self.kicker else 0.1
        self.hits = [self.t0]

    def frame(self, t):
        img = self.canvas(t)
        o = self.out_p(t)
        a_out = 1 - E.in_cubic(o)
        lh = self.ts.size * 1.12
        block_w = max(g.width for g in self.glyphs)
        left = (self.width - block_w) / 2  # anchor on the FULL text width: no sliding while typing
        top = self.height / 2 - lh * len(self.glyphs) / 2
        if self.kick:
            n = int(t * self.k_cps)
            im = self.kick.render(char_alpha=lambda i: 1.0 if i < n else 0.0, alpha=a_out, color=self.pal.accent)
            paste(img, im, left, top - self.u * 0.05, "lm")
        typed = max(0, int((t - self.t0) * self.cps))
        cursor_at = None
        for li, g in enumerate(self.glyphs):
            before = sum(len(x.text) for x in self.glyphs[:li])
            vis = typed - before
            if vis <= 0:
                break
            im = g.render(char_alpha=lambda i, vis=vis: 1.0 if i < vis else 0.0, alpha=a_out)
            pad = int(self.ts.size * 0.25)
            paste(img, im, left - pad, top + lh * li - pad, "lt")
            if vis < len(g.text) or li == len(self.glyphs) - 1:
                cx = left + (g.xs[vis] if vis < len(g.text) else g.width + self.ts.size * 0.08)
                cursor_at = (cx, top + lh * li)
        if cursor_at and (int(t * 2.2) % 2 == 0 or typed < sum(len(g.text) for g in self.glyphs)):
            cx, cy = cursor_at
            ImageDraw.Draw(img).rectangle([cx, cy + self.ts.size * 0.12, cx + self.ts.size * 0.42, cy + self.ts.size * 1.0],
                                          fill=rgba(self.pal.accent, 0.9 * a_out))
        if self.sub:
            p = E.out_cubic(E.progress(t, self.t0 + len(self.title) / self.cps + 0.2, 0.6))
            paste(img, self.sub.render(alpha=p * a_out), left, top + lh * len(self.glyphs) + self.u * 0.03, "lt")
        return img


class SerifFade(TitleBase):
    """Luxury: words breathe in one by one — rise, unblur, fade — over a growing gold rule."""

    intro, outro = 2.6, 1.2

    def setup(self):
        title = apply_case(self.title, self.ty.display_case)
        self.lines, self.ts = fit_text(title, self.style("display", self.u * 0.12), self.max_w * 0.9, max_lines=2)
        self.words = [[Glyphs(w, self.ts) for w in line.split()] for line in self.lines]
        self.space = Glyphs("n", self.ts).width * 0.45
        self.kick = Glyphs(apply_case(self.kicker, "upper"), self.style("kicker", self.u * 0.02)) if self.kicker else None
        self.sub = Glyphs(apply_case(self.subtitle, "upper"), self.style("kicker", self.u * 0.02)) if self.subtitle else None
        count = sum(len(ws) for ws in self.words)
        self.step = min(0.32, 1.4 / max(1, count))
        self.hits = [0.3]

    def frame(self, t):
        img = self.canvas(t)
        o = self.out_p(t)
        a_out = 1 - E.in_out_sine(o)
        lh = self.ts.size * 1.15
        line_ws = [sum(w.width for w in ws) + self.space * (len(ws) - 1) for ws in self.words]
        top = self.height / 2 - lh * len(self.words) / 2
        n = 0
        for li, ws in enumerate(self.words):
            x = (self.width - line_ws[li]) / 2
            for w in ws:
                s = 0.3 + n * self.step
                p = E.out_cubic(E.progress(t, s, 1.2))
                im = transform(w.render(), blur=7 * (1 - p) + 4 * E.in_cubic(o), alpha=p * a_out)
                paste(img, im, x + w.width / 2, top + lh * (li + 0.5) + 18 * (1 - p) - 8 * o, "mm")
                x += w.width + self.space
                n += 1
        p = E.in_out_cubic(E.progress(t, 0.9, 1.6))
        if p > 0:
            half = self.u * 0.12 * p
            y = top + lh * len(self.words) + self.u * 0.03
            ImageDraw.Draw(img).line([(self.width / 2 - half, y), (self.width / 2 + half, y)],
                                     fill=rgba(self.pal.accent, 0.85 * a_out), width=max(1, int(self.u * 0.0018)))
        for g, y, s in ((self.kick, top - self.u * 0.06, 0.1), (self.sub, top + lh * len(self.words) + self.u * 0.075, 1.4)):
            if g:
                p = E.out_cubic(E.progress(t, s, 1.0))
                paste(img, g.render(alpha=p * a_out, color=self.pal.accent if g is self.kick else self.pal.muted), self.width / 2, y, "mm")
        return img


TITLE_ANIMS = {
    "tracking_reveal": TrackingReveal,
    "mask_rise": MaskRise,
    "slam": Slam,
    "type_on": TypeOn,
    "serif_fade": SerifFade,
}


def make_title(look: Look, width: int, height: int, fps: int, duration: float, title: str,
               kicker: str = "", subtitle: str = "", card: bool = False, anim: str | None = None, scale: float = 1.0,
               keep_ink: bool = False) -> TitleBase:
    cls = TITLE_ANIMS[anim or look.title_anim]
    duration = max(duration, cls.intro + cls.outro + 0.6)
    return cls(look, width, height, fps, duration, title, kicker, subtitle, card=card, scale=scale, keep_ink=keep_ink)
