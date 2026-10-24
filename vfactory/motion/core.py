"""Frame-accurate 2D motion engine on Pillow.

Animations are pure functions of time: `frame(t) -> RGBA Image`. Nothing is
stateful, so any frame can be rendered (and checked) in isolation.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .. import fonts
from ..styles import hex_rgb


def rgba(color: str | tuple, alpha: float = 1.0) -> tuple[int, int, int, int]:
    rgb = hex_rgb(color) if isinstance(color, str) else tuple(color[:3])
    return (*rgb, int(round(255 * max(0.0, min(1.0, alpha)))))


def apply_case(text: str, case: str) -> str:
    if case == "upper":
        return text.upper()
    if case == "title":
        return text.title()
    return text


@dataclass
class TextStyle:
    font: str
    size: int
    weight: int | None = None
    tracking: float = 0.0     # em
    color: str = "#FFFFFF"

    def pil(self):
        return fonts.get(self.font, self.size, self.weight)


@dataclass
class Glyphs:
    """A single line of text, laid out with tracking, kerning preserved."""

    text: str
    style: TextStyle
    xs: list[float] = field(default_factory=list)
    width: float = 0.0
    ascent: int = 0
    descent: int = 0

    def __post_init__(self):
        self.layout(self.style.tracking)

    def layout(self, tracking_em: float) -> None:
        f = self.style.pil()
        track = tracking_em * self.style.size
        self.xs = [f.getlength(self.text[:i]) + track * i for i in range(len(self.text))]
        self.width = f.getlength(self.text) + track * max(0, len(self.text) - 1)
        self.ascent, self.descent = f.getmetrics()

    @property
    def height(self) -> int:
        return self.ascent + self.descent

    def render(self, *, tracking: float | None = None, color: str | None = None, alpha: float = 1.0,
               char_alpha=None, char_dy=None, pad: int = 0) -> Image.Image:
        """Render the line to a tight RGBA image. `char_alpha`/`char_dy` are per-character callables(i)->value."""
        if tracking is not None and abs(tracking - self.style.tracking) > 1e-6:
            g = Glyphs(self.text, TextStyle(self.style.font, self.style.size, self.style.weight, tracking, self.style.color))
        else:
            g = self
        f = self.style.pil()
        pad = pad or int(self.style.size * 0.25)
        img = Image.new("RGBA", (int(g.width) + 2 * pad + 2, g.height + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        col = color or self.style.color
        if char_alpha is None and char_dy is None and tracking is None and self.style.tracking == 0:
            d.text((pad, pad), self.text, font=f, fill=rgba(col, alpha))
            return img
        for i, ch in enumerate(self.text):
            if ch == " ":
                continue
            a = alpha * (char_alpha(i) if char_alpha else 1.0)
            if a <= 0.002:
                continue
            dy = char_dy(i) if char_dy else 0.0
            d.text((pad + g.xs[i], pad + dy), ch, font=f, fill=rgba(col, a))
        return img


def fit_text(text: str, style: TextStyle, max_width: float, max_lines: int = 2, min_size: int = 12) -> tuple[list[str], TextStyle]:
    """Find the largest size <= style.size where text fits in max_width using <= max_lines balanced lines."""
    words = text.split()
    size = style.size
    while size >= min_size:
        st = TextStyle(style.font, size, style.weight, style.tracking, style.color)
        for n in range(1, min(max_lines, len(words)) + 1):
            lines = _balance(words, n, st)
            if all(Glyphs(line, st).width <= max_width for line in lines):
                return lines, st
        size = int(size * 0.94)
    st = TextStyle(style.font, min_size, style.weight, style.tracking, style.color)
    return _balance(words, max_lines, st), st


def _balance(words: list[str], n: int, st: TextStyle) -> list[str]:
    if n <= 1 or len(words) <= 1:
        return [" ".join(words)]
    best, best_cost = None, float("inf")

    def splits(ws, k):
        if k == 1:
            yield [ws]
            return
        for i in range(1, len(ws) - k + 2):
            for rest in splits(ws[i:], k - 1):
                yield [ws[:i], *rest]

    for parts in splits(words, n):
        lines = [" ".join(p) for p in parts]
        widths = [Glyphs(line, st).width for line in lines]
        cost = max(widths) - min(widths) * 0.5
        if cost < best_cost:
            best, best_cost = lines, cost
    return best or [" ".join(words)]


# ---------------------------------------------------------------- compositing

def with_alpha(img: Image.Image, alpha: float) -> Image.Image:
    if alpha >= 0.999:
        return img
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * max(0.0, alpha)))
    return Image.merge("RGBA", (r, g, b, a))


def transform(img: Image.Image, *, scale: float = 1.0, blur: float = 0.0, alpha: float = 1.0) -> Image.Image:
    if abs(scale - 1.0) > 1e-3:
        w, h = img.size
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BICUBIC)
    if blur > 0.3:
        pad = int(blur * 2.5)
        big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
        big.paste(img, (pad, pad))
        img = _blur_premultiplied(big, blur)
    return with_alpha(img, alpha)


def _blur_premultiplied(img: Image.Image, radius: float) -> Image.Image:
    # Blur colour and alpha together without dark fringes: premultiply, blur, un-premultiply.
    import numpy as np

    arr = np.asarray(img).astype("float32")
    a = arr[..., 3:4] / 255.0
    pm = np.concatenate([arr[..., :3] * a, arr[..., 3:4]], axis=-1).astype("uint8")
    pm = np.asarray(Image.fromarray(pm, "RGBA").filter(ImageFilter.GaussianBlur(radius))).astype("float32")
    a2 = pm[..., 3:4] / 255.0
    rgb = np.where(a2 > 1e-4, pm[..., :3] / np.maximum(a2, 1e-4), 0)
    out = np.concatenate([np.clip(rgb, 0, 255), pm[..., 3:4]], axis=-1).astype("uint8")
    return Image.fromarray(out, "RGBA")


def paste(canvas: Image.Image, img: Image.Image, x: float, y: float, anchor: str = "mm") -> None:
    """Alpha-composite img onto canvas. anchor: [l|m|r][t|m|b]."""
    ax, ay = anchor
    ox = {"l": 0, "m": img.width / 2, "r": img.width}[ax]
    oy = {"t": 0, "m": img.height / 2, "b": img.height}[ay]
    canvas.alpha_composite(img, (int(round(x - ox)), int(round(y - oy)))) if _inside(canvas, img, x - ox, y - oy) \
        else _paste_clipped(canvas, img, int(round(x - ox)), int(round(y - oy)))


def _inside(canvas, img, x, y) -> bool:
    return x >= 0 and y >= 0 and x + img.width <= canvas.width and y + img.height <= canvas.height


def _paste_clipped(canvas: Image.Image, img: Image.Image, x: int, y: int) -> None:
    left, top = max(0, -x), max(0, -y)
    right, bottom = min(img.width, canvas.width - x), min(img.height, canvas.height - y)
    if right <= left or bottom <= top:
        return
    canvas.alpha_composite(img.crop((left, top, right, bottom)), (x + left, y + top))


def clip_rect(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Zero alpha outside box (in img coordinates) — a hard mask for reveal-from-behind-a-line moves."""
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    r, g, b, a = img.split()
    return Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mask)))


def vertical_gradient(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    import numpy as np

    w, h = size
    t = np.linspace(0, 1, h, dtype="float32")[:, None, None]
    top_a, bot_a = np.array(top, dtype="float32"), np.array(bottom, dtype="float32")
    arr = (top_a * (1 - t) + bot_a * t).repeat(w, axis=1)
    return Image.fromarray(arr.astype("uint8"), "RGBA")


def radial_bg(size: tuple[int, int], color: str, lift: float = 0.08) -> Image.Image:
    """A flat card with a soft centre lift — reads 'lit set', not 'empty slide'."""
    import numpy as np

    w, h = size
    base = np.array(hex_rgb(color), dtype="float32")
    yy, xx = np.mgrid[0:h, 0:w].astype("float32")
    d = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.75)) ** 2)
    k = np.clip(1 - d, 0, 1)[..., None] ** 1.6
    light = base + (255 - base) * lift if base.mean() < 128 else base * (1 + lift * 0.3)
    arr = base * (1 - k) + np.minimum(light, 255) * k
    a = np.full((h, w, 1), 255, dtype="float32")
    return Image.fromarray(np.concatenate([arr, a], axis=-1).clip(0, 255).astype("uint8"), "RGBA")


# ---------------------------------------------------------------- writing

class Animation:
    """Base class. Subclasses set width/height/fps/duration and implement frame(t)."""

    width: int
    height: int
    fps: int
    duration: float
    opaque: bool = False
    hits: list[float]

    def frame(self, t: float) -> Image.Image:  # pragma: no cover - interface
        raise NotImplementedError

    @property
    def n_frames(self) -> int:
        return max(1, int(round(self.duration * self.fps)))

    def render(self, out: str | Path) -> Path:
        """Render to .mov (PNG, alpha) or .mp4 when opaque."""
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if self.opaque:
            codec = ["-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p"]
        else:
            codec = ["-c:v", "png", "-pix_fmt", "rgba", "-compression_level", "1"]
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
               "-s", f"{self.width}x{self.height}", "-r", str(self.fps), "-i", "-", *codec, str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for i in range(self.n_frames):
                img = self.frame(i / self.fps)
                if img.size != (self.width, self.height):
                    img = img.resize((self.width, self.height))
                proc.stdin.write(img.convert("RGBA").tobytes())
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode(errors="replace")
            proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"render of {out} failed: {err[-2000:]}")
        return out

    def still(self, t: float, out: str | Path, bg: str | None = "#202020") -> Path:
        img = self.frame(t)
        if bg and not self.opaque:
            base = Image.new("RGBA", img.size, rgba(bg))
            base.alpha_composite(img)
            img = base
        img.convert("RGB").save(out)
        return Path(out)
