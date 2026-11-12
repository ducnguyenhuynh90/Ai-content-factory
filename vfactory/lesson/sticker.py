"""The "sticker" look (`meta.style: "sticker"`): light warm paper, everything drawn as a die-cut sticker.

Tokens (PALETTE) are the single source for the light look; `Look(style="sticker")` reads them. What changes against the
default dark "Ledger" look:
- background: cream paper with a faint fibre texture (paper_png), no dust motes;
- text: ink on cream, Inter only (weights 600 and 800; never 700), with a white sticker rim (text-shadow ring) and a
  soft drop shadow, so any word reads on paper, on a set or on a picture;
- pictures: every <svg> gets a white die-cut outline and a soft shadow (css_filter); translucent line-art fills become
  solid pastel tints (stickerize) so the outline follows a filled shape;
- concept colours: gold A and coral B, darkened enough to read on cream (>= 3:1 at the 36 px floor);
- 4-5 pastel accents for sets and props.
The dark look stays the default; nothing here runs unless the lesson asks for the sticker style.
"""

from __future__ import annotations

import math
import re

PALETTE = {
    "bg": "#FBF3E3",       # cream paper
    "ink": "#2E2A35",      # text and outlines
    "line": "#3B302C",     # drawing outline (warm ink)
    "muted": "#6F6559",    # secondary text (5.2:1 on cream)
    "gold": "#B7791F",     # concept A (3.3:1 on cream; large text only, i.e. everything >= 36 px)
    "coral": "#D2643F",    # concept B (3.4:1)
    "white": "#FFFFFF",
    # pastel accents (sets, props, badges)
    "mint": "#BFE6D3",
    "sky": "#CFE7F3",
    "pink": "#F7CAD0",
    "butter": "#FBE3A1",
    "lilac": "#DCD0F2",
    "peach": "#F9D2B4",
}
PASTELS = ["butter", "mint", "pink", "sky", "lilac", "peach"]
STYLES = ("dark", "sticker")
SHADOW = "rgba(84,62,38,0.22)"


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    """a blended toward b by t (0 = a, 1 = b)."""
    (r1, g1, b1), (r2, g2, b2) = hex_rgb(a), hex_rgb(b)
    return "#{:02X}{:02X}{:02X}".format(*(round(x + (y - x) * t) for x, y in ((r1, r2), (g1, g2), (b1, b2))))


def shade(h: str, k: float) -> str:
    """Darken (k > 0) toward warm ink or lighten (k < 0) toward white."""
    return mix(h, "#2A2018", k) if k >= 0 else mix(h, "#FFFFFF", -k)


def text_rim(px: float = 0.075, unit: str = "em", shadow: bool = True) -> str:
    """A white sticker rim around text: a ring of zero-blur text-shadows (scales with the font), then a soft shadow.
    text-shadow survives the blur/opacity tweens the scenes put on `filter`."""
    ring = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        ring.append(f"{px * math.cos(a):.3f}{unit} {px * math.sin(a):.3f}{unit} 0 #fff")
    if shadow:
        ring.append(f"0 {px * 1.6:.3f}{unit} {px * 2.2:.3f}{unit} {SHADOW}")
    return ", ".join(ring)


def css_filter(r: int = 5, drop: int = 8) -> str:
    """A die-cut white outline (four zero-blur drop-shadows build a ring of ~r px) and a soft shadow, for <svg> elements."""
    h = max(1, round(r * 0.72))
    return (f"drop-shadow({r}px 0 0 #fff) drop-shadow(-{r}px 0 0 #fff) drop-shadow(0 {r}px 0 #fff) drop-shadow(0 -{r}px 0 #fff) "
            f"drop-shadow({h}px {h}px 0 #fff) drop-shadow(-{h}px -{h}px 0 #fff) "
            f"drop-shadow(0 {drop}px {round(drop * 1.2)}px {SHADOW})")


def svg_filter(fid: str, r: float = 6.0, drop: float = 9.0) -> str:
    """The same sticker treatment as an SVG <filter> (for groups inside one big stage <svg>): dilate the shape's alpha,
    make it solid white, add a soft shadow below, then the art on top."""
    return (f'<filter id="{fid}" x="-25%" y="-25%" width="150%" height="150%" color-interpolation-filters="sRGB">'
            f'<feMorphology in="SourceAlpha" operator="dilate" radius="{r:.1f}" result="d"/>'
            '<feComponentTransfer in="d" result="ds"><feFuncA type="discrete" tableValues="0 1 1 1 1 1 1 1 1 1"/></feComponentTransfer>'
            '<feFlood flood-color="#ffffff" result="w0"/><feComposite in="w0" in2="ds" operator="in" result="w"/>'
            f'<feGaussianBlur in="ds" stdDeviation="{drop * 0.7:.1f}" result="b"/><feOffset in="b" dy="{drop:.1f}" result="o"/>'
            '<feFlood flood-color="#543E26" flood-opacity="0.24" result="s0"/><feComposite in="s0" in2="o" operator="in" result="s"/>'
            '<feMerge><feMergeNode in="s"/><feMergeNode in="w"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


_FILL = re.compile(r'fill="(#[0-9A-Fa-f]{6})" fill-opacity="([0-9.]+)"')


def stickerize(svg: str) -> str:
    """Line-art fills (a colour at 6-50 % opacity) become solid pastel tints of that colour: a sticker is a filled shape,
    and the die-cut outline must follow it. Fainter fills (washes, venn rings) are left alone."""
    def one(m):
        c, op = m.group(1), float(m.group(2))
        if not 0.06 <= op <= 0.5:
            return m.group(0)
        k = min(0.62, max(0.2, op * 2.0))  # how much colour stays
        return f'fill="{mix(c, "#FFFFFF", 1 - k)}"'
    return _FILL.sub(one, svg)


def base_css(L, sid: str) -> str:
    """Extra rules for one scene in the sticker look (appended after the shared base css)."""
    rim = text_rim()
    return f"""
    #{sid}-wrap {{ font-weight: 600; }}
    #{sid}-wrap .serif {{ font-family: {L.sans}; font-weight: 800; letter-spacing: -0.01em; }}
    #{sid}-wrap .kicker {{ color: {L.colors['b']}; }}
    #{sid}-wrap div, #{sid}-wrap span {{ text-shadow: {rim}; }}
    #{sid}-wrap svg text {{ font-family: {L.sans}; font-weight: 800; }}
    #{sid}-wrap svg:not(.raw) {{ filter: {css_filter(max(4, L.px(0.005)), L.px(0.008))}; }}
    #{sid}-wrap .stk-card {{ background: #fff; border-radius: {L.px(0.03)}px; box-shadow: 0 0 0 {L.px(0.006)}px #fff,
      0 {L.px(0.01)}px {L.px(0.022)}px {SHADOW}; }}
    """


def paper_png(path, size: int = 512, seed: int = 3):
    """A seamless paper-fibre overlay (RGBA, warm brown in the alpha): periodic low-frequency mottling from filtered
    noise in the Fourier domain (so the tile has no seams) plus fine grain."""
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (size, size))
    f = np.fft.fft2(n)
    ky = np.fft.fftfreq(size)[:, None]
    kx = np.fft.fftfreq(size)[None, :]
    k = np.sqrt(kx ** 2 + ky ** 2) + 1e-6
    low = np.real(np.fft.ifft2(f * np.exp(-(k / 0.012) ** 2)))
    fib = np.real(np.fft.ifft2(f * (np.abs(kx) < 0.02) * np.exp(-(k / 0.18) ** 2)))  # faint horizontal fibres
    low = (low - low.mean()) / (low.std() + 1e-9)
    fib = (fib - fib.mean()) / (fib.std() + 1e-9)
    grain = rng.normal(0, 1, (size, size))
    a = np.clip(10 + 7 * low + 4 * fib + 6 * grain, 0, 60).astype("uint8")
    rgb = np.zeros((size, size, 3), dtype="uint8")
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = 120, 92, 60
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(path)
    return path
