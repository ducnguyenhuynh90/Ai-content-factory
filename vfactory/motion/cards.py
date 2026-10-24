"""Lower thirds, end cards and light leaks."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
from PIL import Image, ImageDraw

from .. import easing as E
from ..styles import Look, hex_rgb
from .core import Animation, Glyphs, TextStyle, apply_case, clip_rect, paste, radial_bg, rgba, transform, vertical_gradient, with_alpha
from .titles import make_title


class LowerThird(Animation):
    """Name + role identity card in the lower-left safe area."""

    def __init__(self, look: Look, width: int, height: int, fps: int, duration: float, name: str, role: str = "",
                 anim: str | None = None):
        self.look, self.width, self.height, self.fps, self.duration = look, width, height, fps, max(duration, 2.5)
        self.anim = anim or look.lower_third_anim
        self.opaque = False
        u = min(width, height)
        self.u = u
        ty, pal = look.type, look.palette
        if _is_dark(pal.fg):  # dark ink belongs on the look's light cards, not over footage
            pal = replace(pal, fg="#FFFFFF", muted="#D9D9D6")
        if self.anim == "hairline":
            self.name = Glyphs(apply_case(name, "upper"), TextStyle(ty.kicker, int(u * 0.03), 600 if ty.kicker_weight else None, 0.22, pal.fg))
            self.role = Glyphs(role, TextStyle(ty.display, int(u * 0.03), ty.display_weight, 0.0, pal.muted)) if role else None
        else:
            self.name = Glyphs(name, TextStyle(ty.body, int(u * 0.042), 700, -0.01, pal.fg))
            self.role = Glyphs(apply_case(role, "upper"), TextStyle(ty.kicker, int(u * 0.022), ty.kicker_weight, 0.25, pal.accent)) if role else None
        self.x = width * 0.065
        self.y = height * (0.80 if look.letterbox is None or width < height else 0.74)
        self.hits = [0.0]
        g = vertical_gradient((width, int(height * 0.38)), (0, 0, 0, 0), (0, 0, 0, 120))
        self._shade = g

    def frame(self, t):
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        pin = E.progress(t, 0, 0.9)
        pout = E.progress(t, self.duration - 0.6, 0.6)
        a_out = 1 - E.in_cubic(pout)
        img.alpha_composite(with_alpha(self._shade, E.out_cubic(pin) * a_out), (0, self.height - self._shade.height))
        d = ImageDraw.Draw(img)
        if self.anim == "hairline":
            p = E.in_out_cubic(E.progress(t, 0.0, 0.8))
            line_w = (max(self.name.width, self.role.width if self.role else 0) + self.u * 0.02) * p
            y = self.y
            d.line([(self.x, y), (self.x + line_w * (1 - E.in_cubic(pout)), y)], fill=rgba(self.look.palette.accent, 0.9),
                   width=max(1, int(self.u * 0.002)))
            pn = E.out_cubic(E.progress(t, 0.3, 0.7))
            paste(img, self.name.render(alpha=pn * a_out, tracking=0.22 + 0.2 * (1 - pn)), self.x - self.name.style.size * 0.25,
                  y - self.u * 0.012, "lb")
            if self.role:
                pr = E.out_cubic(E.progress(t, 0.55, 0.7))
                paste(img, self.role.render(alpha=pr * a_out), self.x - self.role.style.size * 0.25, y + self.u * 0.004 + 8 * (1 - pr), "lt")
            return img
        # bar_wipe: accent block sweeps right, name revealed behind its trailing edge
        bar_h = self.name.height + self.u * 0.012
        p_bar = E.out_expo(E.progress(t, 0.0, 0.45))
        p_back = E.in_out_cubic(E.progress(t, 0.25, 0.45))
        width = self.name.width + self.u * 0.05
        x0 = self.x + width * p_back
        x1 = self.x + width * p_bar
        if pout > 0:
            x0, x1 = self.x, self.x + width * (1 - E.in_expo(pout))
        top = self.y - bar_h
        pad = int(self.name.style.size * 0.25)
        name_img = self.name.render()
        reveal = int((x0 - self.x) + pad) if pout == 0 else int(x1 - self.x + pad)
        name_img = clip_rect(name_img, (0, 0, max(0, reveal), name_img.height))
        paste(img, name_img, self.x + self.u * 0.004 - pad, top + self.u * 0.006 - pad, "lt")
        if x1 > x0 + 1 and pout == 0:
            d.rectangle([x0, top, x1, top + bar_h], fill=rgba(self.look.palette.accent))
        if self.role:
            pr = E.out_cubic(E.progress(t, 0.55, 0.5))
            paste(img, self.role.render(alpha=pr * a_out), self.x - self.role.style.size * 0.25 + 12 * (1 - pr),
                  self.y + self.u * 0.012, "lt")
        return img


class EndCard(Animation):
    """The last thing people see. Title lock-up + CTA (+ credits), on the look's background."""

    def __init__(self, look: Look, width: int, height: int, fps: int, duration: float, title: str,
                 tagline: str = "", cta: str = "", handle: str = "", credits: list | None = None,
                 logo: str | None = None, layout: str | None = None):
        self.look, self.width, self.height, self.fps, self.duration = look, width, height, fps, duration
        self.layout = layout or look.endcard_layout
        self.opaque = True
        self.u = min(width, height)
        pal, ty = look.palette, look.type
        self.bg = radial_bg((width, height), pal.bg, lift=0.06)
        self.credits = credits or []
        self.cta = cta
        self.hits = []
        self.logo = None
        if logo:
            try:
                im = Image.open(logo).convert("RGBA")
                s = (self.u * 0.16) / max(im.size)
                self.logo = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
            except OSError:
                self.logo = None
        credit_time = 0.0
        if self.layout == "credits" and self.credits:
            credit_time = min(len(self.credits) * 1.0, duration * 0.5)
        self.credit_time = credit_time
        lockup_dur = max(2.5, duration - credit_time)
        self.lockup = make_title(look, width, height, fps, lockup_dur + 0.05, title, kicker=handle if self.layout != "monogram" else "",
                                 subtitle=tagline, card=False, scale=0.8, keep_ink=True)
        self.lockup.scrim = False
        self.lockup._scrim = None
        self.lockup.outro = 0.001
        self.hits = [credit_time + h for h in self.lockup.hits]
        self.cta_g = Glyphs(apply_case(cta, "upper"), TextStyle(ty.kicker, int(self.u * 0.024), 600 if ty.kicker_weight else None,
                                                                  0.24, pal.bg if _is_dark(pal.bg) is False else pal.fg)) if cta else None
        self.mono = None
        if self.layout == "monogram":
            letter = (title.strip()[:1] or "•")
            self.mono = Glyphs(letter, TextStyle(ty.display, int(self.u * 0.34), ty.display_weight, 0, pal.accent))
        self.cred = [(Glyphs(apply_case(r, "upper"), TextStyle(ty.kicker, int(self.u * 0.018), ty.kicker_weight, 0.35, pal.muted)),
                      Glyphs(n, TextStyle(ty.display, int(self.u * 0.046), ty.display_weight, 0.02, pal.fg))) for r, n in self.credits]

    def frame(self, t):
        img = self.bg.copy()
        fade_out = 1 - E.in_out_cubic(E.progress(t, self.duration - 0.8, 0.8))
        if self.credit_time and t < self.credit_time:
            per = self.credit_time / len(self.cred)
            i = min(len(self.cred) - 1, int(t / per))
            lt = t - i * per
            a = E.out_cubic(E.progress(lt, 0, 0.35)) * (1 - E.in_cubic(E.progress(lt, per - 0.3, 0.3)))
            role, name = self.cred[i]
            paste(img, role.render(alpha=a), self.width / 2, self.height / 2 - self.u * 0.04, "mm")
            paste(img, name.render(alpha=a), self.width / 2, self.height / 2 + self.u * 0.025 + 6 * (1 - a), "mm")
            return img
        lt = t - self.credit_time
        y_shift = 0
        if self.mono is not None:
            p = E.out_cubic(E.progress(lt, 0.0, 1.6))
            m = transform(self.mono.render(alpha=0.9 * p * fade_out), blur=10 * (1 - p))
            paste(img, m, self.width / 2, self.height * 0.36, "mm")
            y_shift = self.u * 0.12
        if self.logo is not None:
            p = E.out_cubic(E.progress(lt, 0.0, 0.8))
            paste(img, with_alpha(self.logo, p * fade_out), self.width / 2, self.height * 0.28, "mm")
            y_shift = self.u * 0.08
        lock = self.lockup.frame(min(lt, self.lockup.duration - 0.01))
        img.alpha_composite(with_alpha(lock, fade_out), (0, int(y_shift)))
        if self.cta_g is not None:
            p = E.out_back(E.progress(lt, self.lockup.intro + 0.2, 0.6))
            a = E.progress(lt, self.lockup.intro + 0.2, 0.3) * fade_out
            if a > 0:
                pad_x, pad_y = self.u * 0.035, self.u * 0.018
                w = self.cta_g.width + 2 * pad_x
                h = self.cta_g.height + 2 * pad_y * 0.6
                cx, cy = self.width / 2, self.height * 0.80 if self.height > self.width else self.height * 0.78
                pill = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0))
                ImageDraw.Draw(pill).rounded_rectangle([1, 1, w + 1, h + 1], radius=h / 2, fill=rgba(self.look.palette.accent))
                pill.alpha_composite(self.cta_g.render(color=_ink_on(self.look.palette.accent)), (int(pad_x - self.cta_g.style.size * 0.25),
                                                                                                    int((h - self.cta_g.height) / 2 - self.cta_g.style.size * 0.25 + 2)))
                paste(img, transform(pill, scale=0.85 + 0.15 * p, alpha=a), cx, cy, "mm")
        return img


def _is_dark(hexcol: str) -> bool:
    r, g, b = hex_rgb(hexcol)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 128


def _ink_on(hexcol: str) -> str:
    return "#FFFFFF" if _is_dark(hexcol) else "#0B0B0B"


class LightLeak(Animation):
    """Procedural film light leak: warm blobs drifting across, additive-looking via alpha = luminance."""

    def __init__(self, width: int, height: int, fps: int, duration: float = 1.4, seed: int = 0,
                 colors=("#FF7A1A", "#FF3D6E", "#FFD27A"), strength: float = 0.75):
        self.width, self.height, self.fps, self.duration = width, height, fps, duration
        self.opaque = False
        self.hits = []
        rng = np.random.default_rng(seed)
        self.blobs = []
        for i in range(3):
            c = np.array(hex_rgb(colors[i % len(colors)]), dtype="float32") / 255
            x0, y0 = rng.uniform(-0.3, 0.4), rng.uniform(-0.2, 1.2)
            vx, vy = rng.uniform(0.5, 1.0), rng.uniform(-0.3, 0.3)
            r = rng.uniform(0.35, 0.7)
            self.blobs.append((c, x0, y0, vx, vy, r))
        self.strength = strength
        self.sw, self.sh = max(16, width // 8), max(16, height // 8)
        yy, xx = np.mgrid[0:self.sh, 0:self.sw].astype("float32")
        self.xx, self.yy = xx / self.sw, yy / self.sh * (height / width)

    def frame(self, t):
        p = t / self.duration
        env = math.sin(math.pi * min(1, max(0, p))) ** 1.5 * self.strength
        acc = np.zeros((self.sh, self.sw, 3), dtype="float32")
        for c, x0, y0, vx, vy, r in self.blobs:
            cx, cy = x0 + vx * p, (y0 + vy * p) * (self.height / self.width)
            d2 = (self.xx - cx) ** 2 + (self.yy - cy) ** 2
            acc += c[None, None, :] * np.exp(-d2 / (r * r * 0.35))[..., None]
        acc = np.clip(acc * env, 0, 1)
        lum = acc.max(axis=-1, keepdims=True)
        rgb = np.where(lum > 1e-4, acc / np.maximum(lum, 1e-4), 0)
        arr = np.concatenate([rgb * 255, lum * 255], axis=-1).astype("uint8")
        return Image.fromarray(arr, "RGBA").resize((self.width, self.height), Image.BILINEAR)


class Chapter(Animation):
    """Section card overlay: number + name, quiet, in the look's title grammar."""

    def __init__(self, look: Look, width: int, height: int, fps: int, duration: float, text: str, number: str = ""):
        self.inner = make_title(look, width, height, fps, duration, text, kicker=number, card=False, scale=0.6)
        self.width, self.height, self.fps, self.duration = width, height, fps, self.inner.duration
        self.opaque = False
        self.hits = self.inner.hits

    def frame(self, t):
        return self.inner.frame(t)
