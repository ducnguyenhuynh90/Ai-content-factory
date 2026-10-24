"""Brand identity, stable preferences and the taste log.

- Brand: discovered from the project and skill folders when it exists; otherwise left EMPTY
  and the person is asked once. Never invented.
- Preferences: stable defaults (platform, CTA, style, caption size, pace...). Only things the
  person said should apply going forward are saved here.
- Taste log (from GhostEditor): every correction in the person's own words, kept apart from
  rules the editor learned itself, so "you said" is never confused with a guess.
All files are plain JSON next to the video-editor skill, easy to edit by hand.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

BRAND_KEYS = ("primary_color", "secondary_color", "font")
DEFAULT_PREFS = {
    "platform": None,          # asked per edit unless saved
    "cta": None,
    "style": None,             # clean | captions | captions+graphics | branded
    "pace": "natural",         # tight | natural | relaxed
    "caption_words": 3,
    "caption_size": 1.0,       # multiplier on the platform default
    "caption_case": "as-is",   # as-is | upper
    "emphasis": "keywords",    # none | keywords
    "jump_cuts": "auto",       # auto (punch-in when resolution allows) | none
    "emojis": False,
    "workspace": None,         # default ~/VideoEditor
}
BRAND_FILE_PATTERNS = re.compile(r"(^|/)(DESIGN\.md|visual[-_ ]style\.md|brand[-_ ]?(guide|book|kit)?\.(md|json|ya?ml|txt)|"
                                 r"brand\.json|style[-_ ]guide\.md)$", re.I)
BROLL_DIR_NAMES = ("b-roll kit", "b-roll", "broll", "b_roll", "brand-assets", "brand assets", "video-assets", "video assets")


def config_dir() -> Path:
    env = os.environ.get("VIDEO_EDITOR_CONFIG")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".claude" / "skills" / "video-editor" / "config"


def _read(name: str, default):
    p = config_dir() / name
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return default
    return default


def _write(name: str, data) -> Path:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return p


# ---------------------------------------------------------------- brand

def load_brand() -> dict:
    return _read("brand.json", {})


def brand_complete(b: dict | None = None) -> bool:
    b = load_brand() if b is None else b
    return all(b.get(k) for k in BRAND_KEYS)


def save_brand(primary_color: str, secondary_color: str, font: str, source: str = "person", **optional) -> Path:
    for c in (primary_color, secondary_color):
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", c):
            raise ValueError(f"colour must be #RRGGBB, got {c!r}")
    b = load_brand()
    b.update({"primary_color": primary_color.upper(), "secondary_color": secondary_color.upper(), "font": font,
              "source": source, "updated": datetime.now().isoformat(timespec="seconds")})
    b.update({k: v for k, v in optional.items() if v is not None})
    return _write("brand.json", b)


def discover_brand(search_roots: list[str | Path]) -> list[dict]:
    """Find brand guidance files, logos and fonts. Returns candidates; the caller decides if they are reliable."""
    found = []
    for root in search_roots:
        root = Path(root).expanduser()
        if not root.exists():
            continue
        for p in _walk(root, max_depth=4):
            rel = str(p)
            if BRAND_FILE_PATTERNS.search(rel):
                found.append({"kind": "guide", "path": rel, "colors": _colors_in(p)})
            elif re.search(r"(^|/)logo[^/]*\.(svg|png|jpe?g|webp)$", rel, re.I):
                found.append({"kind": "logo", "path": rel})
            elif p.suffix.lower() in (".ttf", ".otf", ".woff", ".woff2") and "node_modules" not in rel:
                found.append({"kind": "font", "path": rel})
    return found


def _colors_in(p: Path) -> list[str]:
    try:
        text = p.read_text(errors="ignore")[:200_000]
    except OSError:
        return []
    return list(dict.fromkeys(m.upper() for m in re.findall(r"#[0-9A-Fa-f]{6}\b", text)))[:12]


def _walk(root: Path, max_depth: int):
    skip = {".git", "node_modules", "__pycache__", ".cache", "Library", ".Trash"}
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            continue
        for e in entries:
            if e.name in skip or e.name.startswith(".") and e.is_dir():
                continue
            if e.is_dir() and depth < max_depth:
                stack.append((e, depth + 1))
            elif e.is_file():
                yield e


def find_broll_kit(search_roots: list[str | Path]) -> Path | None:
    for root in search_roots:
        root = Path(root).expanduser()
        if not root.exists():
            continue
        for p in [root, *[x for x in _dirs(root, 3)]]:
            if p.name.lower().replace("_", "-") in BROLL_DIR_NAMES or p.name.lower() in BROLL_DIR_NAMES:
                return p
    return None


def _dirs(root: Path, depth: int):
    if depth < 0:
        return
    try:
        for e in root.iterdir():
            if e.is_dir() and not e.name.startswith(".") and e.name != "node_modules":
                yield e
                yield from _dirs(e, depth - 1)
    except (PermissionError, OSError):
        return


def index_broll(kit: Path) -> dict:
    kinds = {"video": (".mp4", ".mov", ".m4v", ".webm"), "image": (".png", ".jpg", ".jpeg", ".webp", ".svg"),
             "audio": (".wav", ".mp3", ".m4a", ".aac"), "font": (".ttf", ".otf", ".woff2")}
    idx: dict[str, list[str]] = {k: [] for k in kinds}
    for p in _walk(kit, 4):
        for k, exts in kinds.items():
            if p.suffix.lower() in exts:
                idx[k].append(str(p))
    idx["logos"] = [p for p in idx["image"] if "logo" in Path(p).name.lower()]
    return idx


# ---------------------------------------------------------------- preferences + taste

def load_prefs() -> dict:
    return {**DEFAULT_PREFS, **_read("preferences.json", {})}


def save_pref(key: str, value) -> Path:
    if key not in DEFAULT_PREFS:
        raise KeyError(f"unknown preference '{key}' (known: {', '.join(DEFAULT_PREFS)})")
    p = _read("preferences.json", {})
    p[key] = value
    return _write("preferences.json", p)


def load_taste() -> dict:
    return _read("taste.json", {"rules": []})


def add_taste(said: str, source: str = "user", sets: dict | None = None, scope: str = "global") -> Path:
    """Record feedback verbatim. `sets` optionally maps it onto a preference (applied only for global scope)."""
    t = load_taste()
    t["rules"].append({"said": said, "from": source, "scope": scope, "sets": sets or {},
                       "at": datetime.now().isoformat(timespec="seconds")})
    if scope == "global" and sets:
        for k, v in sets.items():
            save_pref(k, v)
    return _write("taste.json", t)
