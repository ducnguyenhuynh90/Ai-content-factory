"""Font registry. Every font is loaded from an explicit path — fonts fail silently
when you rely on a name, and a title set in a fallback face looks amateur."""

from __future__ import annotations

import functools
import subprocess
from pathlib import Path

from PIL import ImageFont

FONT_DIR = Path(__file__).parent / "assets" / "fonts"

# name -> (file, ASS/libass family name or None for variable fonts)
BUNDLED = {
    "anton": ("Anton-Regular.ttf", "Anton"),
    "bebas": ("BebasNeue-Regular.ttf", "Bebas Neue"),
    "archivo-black": ("ArchivoBlack-Regular.ttf", "Archivo Black"),
    "dm-serif": ("DMSerifDisplay-Regular.ttf", "DM Serif Display"),
    "instrument-serif": ("InstrumentSerif-Regular.ttf", "Instrument Serif"),
    "instrument-serif-italic": ("InstrumentSerif-Italic.ttf", "Instrument Serif"),
    "playfair": ("PlayfairDisplay-VF.ttf", None),
    "playfair-italic": ("PlayfairDisplay-Italic-VF.ttf", None),
    "montserrat": ("Montserrat-VF.ttf", None),
    "space-grotesk": ("SpaceGrotesk-VF.ttf", None),
    "syne": ("Syne-VF.ttf", None),
    "oswald": ("Oswald-VF.ttf", None),
}

# System fonts we use when present (fontconfig family, style).
SYSTEM = {
    "inter": ("Inter", "Regular"),
    "inter-display": ("Inter Display", "Regular"),
    "jetbrains-mono": ("JetBrains Mono", "Regular"),
    "dejavu": ("DejaVu Sans", "Book"),
}
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


@functools.lru_cache(maxsize=None)
def _fc_match(family: str, style: str) -> str | None:
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}|%{family}", f"{family}:style={style}"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return None
    path, _, fam = out.stdout.partition("|")
    return path if path and family.lower() in fam.lower() else None


def font_path(name: str, weight: int | None = None) -> str:
    if name in BUNDLED:
        return str(FONT_DIR / BUNDLED[name][0])
    if name in SYSTEM:
        family, _ = SYSTEM[name]
        style = _weight_style(weight)
        found = _fc_match(family, style) or _fc_match(family, "Regular")
        if found:
            return found
    p = Path(name)
    if p.exists():
        return str(p)
    return FALLBACK


def _weight_style(weight: int | None) -> str:
    return {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
            600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}.get(int(round((weight or 400) / 100) * 100), "Regular")


@functools.lru_cache(maxsize=256)
def get(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    path = font_path(name, weight)
    font = ImageFont.truetype(path, max(1, int(size)))
    if weight is not None:
        try:
            axes = font.get_variation_axes()
        except (OSError, AttributeError):
            axes = []
        if axes:
            values = []
            for ax in axes:
                tag = ax.get("name", b"")
                tag = tag.decode() if isinstance(tag, bytes) else str(tag)
                if tag.lower().startswith("weight") or tag == "wght":
                    values.append(max(ax["minimum"], min(ax["maximum"], weight)))
                else:
                    values.append(ax["default"])
            font.set_variation_by_axes(values)
    return font


def ass_family(name: str) -> str:
    """Family name usable by libass (captions). Variable fonts fall back to Inter."""
    if name in BUNDLED and BUNDLED[name][1]:
        return BUNDLED[name][1]
    if name in SYSTEM:
        return SYSTEM[name][0]
    return "Inter"


def available() -> dict[str, str]:
    return {name: font_path(name) for name in [*BUNDLED, *SYSTEM]}
