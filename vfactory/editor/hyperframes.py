"""HyperFrames compositions for captions, branded graphics and title/CTA cards.

Follows the HyperFrames render contract (skills `hyperframes`, `hyperframes-cli`):
- root `index.html` holds only media and scene hosts; captions live in ONE sub-composition with
  `data-track-kind="captions"`; every scene is a `<template>` with `#root`, ids unique, `fromTo` tweens,
  one paused timeline registered as `window.__timelines[id]`;
- one caption group visible at a time, opened at its first word, hard-killed after its exit;
- fonts by name only when bundled, otherwise `@font-face` to a file copied into `assets/fonts/`;
- GSAP vendored into `assets/vendor/` (no CDN fetch at render time: fully local and deterministic);
- gates before render: `lint`, `check --json` (0 errors), `snapshot` frames to look at, then
  `render --quality draft` while iterating and `delivery` for the final;
- privacy: `snapshot --describe false` always, so frames are never sent to a vision API.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

GSAP_VERSION = "3.14.2"
HF_BUNDLED_FONTS = {"Inter", "Montserrat", "Outfit", "Nunito", "Oswald", "League Gothic", "Archivo Black", "Space Mono",
                    "IBM Plex Mono", "JetBrains Mono", "EB Garamond", "Playfair Display", "Source Code Pro", "Noto Sans JP",
                    "Roboto", "Open Sans", "Lato", "Poppins"}
STOP = set("a an the and or but if of to in on for with at by from as is are was were be been it its this that i you he "
           "she we they my your our me him her us them so do does did have has had will would can could just not no".split())


class HFError(RuntimeError):
    pass


def npx(args: list[str], cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(["npx", "--yes", "hyperframes", *args], cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, stdin=subprocess.DEVNULL)


def ensure_gsap(dest_dir: Path) -> Path:
    cache = Path.home() / ".cache" / "vfactory" / "gsap" / GSAP_VERSION
    js = cache / "package" / "dist" / "gsap.min.js"
    if not js.exists():
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(["npm", "pack", f"gsap@{GSAP_VERSION}", "--silent"], cwd=cache, check=True,
                       capture_output=True, stdin=subprocess.DEVNULL)
        subprocess.run(["tar", "-xzf", f"gsap-{GSAP_VERSION}.tgz", "package/dist/gsap.min.js"], cwd=cache, check=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(js, dest_dir / "gsap.min.js")
    return dest_dir / "gsap.min.js"


def resolve_font(family: str, assets: Path) -> tuple[str, str]:
    """Return (css font-family, @font-face css). Bundled HF fonts resolve by name; others need a local file."""
    if family in HF_BUNDLED_FONTS:
        return f"'{family}'", ""
    p = Path(family).expanduser()
    path = str(p) if p.is_file() else None
    name = p.stem if path else family
    if not path:
        out = subprocess.run(["fc-match", "-f", "%{file}|%{family}", f"{family}:style=Bold"], capture_output=True, text=True)
        f, _, fam = out.stdout.partition("|")
        if f and family.lower() in fam.lower():
            path = f
    if not path:
        raise HFError(f"font '{family}' is not bundled with HyperFrames and no local font file was found; "
                      "add the font file (.ttf/.otf/.woff2) to the brand config or pick a bundled font")
    (assets / "fonts").mkdir(parents=True, exist_ok=True)
    dst = assets / "fonts" / Path(path).name
    shutil.copy2(path, dst)
    fmt = {"ttf": "truetype", "otf": "opentype", "woff2": "woff2", "woff": "woff"}.get(dst.suffix.lstrip(".").lower(), "truetype")
    face = f"@font-face {{ font-family: '{name}'; src: url('assets/fonts/{dst.name}') format('{fmt}'); font-weight: 100 900; }}"
    return f"'{name}'", face


def group_words(words: list[dict], max_words: int = 3, pause: float = 0.15) -> list[list[dict]]:
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] >= pause):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w["word"][-1:] in ".?!":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def emphasis_index(group: list[dict]) -> int | None:
    """One keyword per group at most: a number, else the longest content word (>= 5 letters)."""
    best, best_len = None, 0
    for i, w in enumerate(group):
        t = re.sub(r"[^\w]", "", w["word"].lower())
        if re.search(r"\d", t):
            return i
        if t not in STOP and len(t) >= 5 and len(t) > best_len:
            best, best_len = i, len(t)
    return best


def _fit_size(texts: list[str], font_path: str | None, base: int, min_size: int, max_width: int) -> int:
    if not font_path:
        return base
    try:
        from PIL import ImageFont
    except ImportError:
        return base
    size = base
    longest = max(texts, key=len) if texts else ""
    while size > min_size:
        f = ImageFont.truetype(font_path, size)
        if f.getlength(longest) <= max_width:
            break
        size -= 2
    return size


def captions_scene(words: list[dict], *, width: int, height: int, duration: float, font_css: str, font_face: str,
                   text_color: str, accent: str, plate: str | None, band: tuple[float, float], max_words: int = 3,
                   size_mult: float = 1.0, case: str = "as-is", emphasis: bool = True, font_path: str | None = None,
                   scrim: bool = True) -> str:
    vertical = height > width
    base = int((78 if vertical else 64) * size_mult)
    max_w = 900 if vertical else 1600
    groups = group_words(words, max_words)
    texts = [" ".join(w["word"] for w in g) for g in groups]
    size = _fit_size([t.upper() if case == "upper" else t for t in texts], font_path, base, 42, max_w)
    top_px = int(band[0] * height)
    band_h = int((band[1] - band[0]) * height)
    parts, tweens = [], []
    for gi, g in enumerate(groups):
        start = max(0.1, g[0]["start"] - 0.05)
        nxt = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else duration
        end = min(max(g[-1]["end"] + 0.15, start + 0.4), nxt, duration)
        if end - start < 0.12:
            continue
        emph = emphasis_index(g) if emphasis else None
        spans = []
        for wi, w in enumerate(g):
            txt = w["word"].upper() if case == "upper" else w["word"]
            cls = "w em" if wi == emph else "w"
            spans.append(f'<span id="cw{gi}-{wi}" class="{cls}">{html.escape(txt)}</span>')
        parts.append(f'<div id="cg{gi}" class="group clip" data-start="{start:.3f}" data-duration="{end - start:.3f}">'
                     f'<div id="cgi{gi}" class="inner">{"".join(spans)}</div></div>')  # spacing via CSS, not whitespace nodes
        rel_end = end - start
        tweens.append(f'tl.fromTo("#cgi{gi}", {{opacity: 0, y: 14}}, {{opacity: 1, y: 0, duration: 0.14, ease: "power3.out"}}, {start:.3f});')
        if emph is not None:
            wt = max(start, g[emph]["start"])
            tweens.append(f'tl.fromTo("#cw{gi}-{emph}", {{y: 0}}, {{y: -6, duration: 0.14, ease: "back.out(2)"}}, {wt:.3f});')  # a lift, not a scale: scaling crowds neighbours
        tweens.append(f'tl.fromTo("#cgi{gi}", {{opacity: 1}}, {{opacity: 0, duration: 0.1, ease: "power2.in", immediateRender: false}}, {start + rel_end - 0.1:.3f});')
    scrim_css = ("background: rgba(0,0,0,0.38); padding: 6px 18px; border-radius: 14px;" if scrim else "")
    return f"""<template>
  <style>
    {font_face}
    #root {{ position: absolute; inset: 0; }}
    #captions .group {{ position: absolute; left: 0; top: {top_px}px; width: {width}px; height: {band_h}px;
      display: flex; align-items: center; justify-content: center; overflow: visible; }}
    #captions .inner {{ max-width: {max_w}px; text-align: center; font-family: {font_css}; font-weight: 800;
      font-size: {size}px; line-height: 1.12; color: {text_color}; {scrim_css}
      text-shadow: 0 2px 10px rgba(0,0,0,0.45); }}
    #captions .w {{ display: inline-block; }}
    #captions .w + .w {{ margin-left: 0.27em; }}
    #captions .em {{ color: {accent}; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{width}" data-height="{height}">
    <div id="captions">
      {chr(10).join('      ' + p for p in parts)}
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + t for t in tweens)}
    window.__timelines["captions"] = tl;
  </script>
</template>
"""


def card_scene(scene_id: str, *, width: int, height: int, duration: float, lines: list[str], font_css: str, font_face: str,
               primary: str, secondary: str, text_color: str, kicker: str = "", exit: bool = True,
               enter: bool = True) -> str:
    """A branded title or CTA card: brand-colour field, staggered line reveal, clean exit.
    enter=False for a card that opens the film: frame 0 is the thumbnail, so it is already composed."""
    vertical = height > width
    size = 96 if vertical else 88
    rows = []
    tweens = []
    if enter:
        tweens += [f'tl.fromTo("#{scene_id}-bg", {{opacity: 0}}, {{opacity: 1, duration: 0.25, ease: "power2.out"}}, 0);',
                   f'tl.fromTo("#{scene_id}-bar", {{scaleX: 0}}, {{scaleX: 1, duration: 0.45, ease: "expo.out"}}, 0.15);']
    else:  # a living hold so the card isn't a static slide
        tweens.append(f'tl.fromTo("#{scene_id}-bar", {{scaleX: 0.55}}, {{scaleX: 1, duration: {max(0.6, duration - 0.4):.2f}, ease: "power1.inOut"}}, 0);')
    if kicker:
        rows.append(f'<div id="{scene_id}-k" class="kicker">{html.escape(kicker)}</div>')
        if enter:
            tweens.append(f'tl.fromTo("#{scene_id}-k", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.3, ease: "power3.out"}}, 0.2);')
    for i, line in enumerate(lines):
        rows.append(f'<div class="mask"><div id="{scene_id}-l{i}" class="line">{html.escape(line)}</div></div>')
        if enter:
            tweens.append(f'tl.fromTo("#{scene_id}-l{i}", {{yPercent: 110}}, {{yPercent: 0, duration: 0.6, ease: "expo.out"}}, {0.3 + i * 0.12:.2f});')
    if exit:  # the film's last card holds instead: a closing line needs time to be read
        tweens.append(f'tl.fromTo("#{scene_id}-wrap", {{opacity: 1}}, {{opacity: 0, duration: 0.25, ease: "power2.in"}}, {max(0.5, duration - 0.3):.2f});')
    return f"""<template>
  <style>
    {font_face}
    #root {{ position: absolute; inset: 0; }}
    #{scene_id}-bg {{ position: absolute; inset: 0; background: linear-gradient(160deg, {primary} 0%, {secondary} 100%); }}
    #{scene_id}-wrap {{ position: absolute; left: 0; top: 0; width: {width}px; height: {height}px; display: flex;
      flex-direction: column; align-items: center; justify-content: center; font-family: {font_css}; color: {text_color}; }}
    #{scene_id}-wrap .mask {{ overflow: hidden; padding: 0 40px; }}
    #{scene_id}-wrap .line {{ font-size: {size}px; font-weight: 800; line-height: 1.05; letter-spacing: -0.02em; text-align: center; }}
    #{scene_id}-wrap .kicker {{ font-size: {int(size * 0.34)}px; font-weight: 600; letter-spacing: 0.25em; text-transform: uppercase;
      margin-bottom: 28px; opacity: 0.9; }}
    #{scene_id}-bar {{ width: {int(width * 0.18)}px; height: 10px; background: {text_color}; margin-top: 36px; transform-origin: 0 50%; }}
  </style>
  <div id="root" data-composition-id="{scene_id}" data-width="{width}" data-height="{height}">
    <div id="{scene_id}-bg"></div>
    <div id="{scene_id}-wrap">
      {''.join(rows)}
      <div id="{scene_id}-bar"></div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + t for t in tweens)}
    window.__timelines["{scene_id}"] = tl;
  </script>
</template>
"""


def build_project(project_dir: Path, *, width: int, height: int, duration: float, fps: int = 30,
                  plate: str | None = None, background: tuple[str, str] | None = None, words: list[dict] | None = None,
                  brand: dict, prefs: dict, band: tuple[float, float], cards: list[dict] | None = None,
                  scrim: bool = True) -> Path:
    """cards: [{"id": "hook", "start": 0, "duration": 2.2, "lines": [...], "kicker": "..."}]"""
    project_dir = Path(project_dir)
    assets = project_dir / "assets"
    (project_dir / "compositions").mkdir(parents=True, exist_ok=True)
    ensure_gsap(assets / "vendor")
    font_css, font_face = resolve_font(brand["font"], assets)
    font_file = None
    m = re.search(r"url\('([^']+)'\)", font_face)
    if m:
        font_file = str(project_dir / m.group(1))
    else:
        out = subprocess.run(["fc-match", "-f", "%{file}", f"{brand['font']}:style=ExtraBold"], capture_output=True, text=True)
        font_file = out.stdout or None
    text_color = brand.get("text_color", "#FFFFFF")
    hosts, z = [], 2
    root_media = ""
    if plate:
        dst = assets / "plate.mp4"
        shutil.copy2(plate, dst)
        root_media = (f'<video id="plate" class="clip" src="assets/plate.mp4" data-start="0" data-duration="{duration:.3f}" '
                      f'data-track-index="0" data-has-audio="true" playsinline '
                      f'style="position:absolute;left:0;top:0;width:{width}px;height:{height}px;object-fit:cover;z-index:0"></video>')
    elif background:
        root_media = (f'<div id="bg" class="clip" data-start="0" data-duration="{duration:.3f}" data-track-index="0" '
                      f'style="position:absolute;inset:0;z-index:0;background:radial-gradient(120% 80% at 50% 30%, '
                      f'{background[0]} 0%, {background[1]} 100%)"></div>'
                      f'<div id="bg-glow" class="clip" data-start="0" data-duration="{duration:.3f}" data-track-index="1" '
                      f'data-layout-ignore style="z-index:1"></div>')
    for c in cards or []:
        (project_dir / "compositions" / f"{c['id']}.html").write_text(card_scene(
            c["id"], width=width, height=height, duration=c["duration"], lines=c["lines"], kicker=c.get("kicker", ""),
            font_css=font_css, font_face=font_face, primary=brand["primary_color"], secondary=brand["secondary_color"],
            text_color=text_color, exit=c.get("exit", True), enter=c.get("enter", c["start"] > 0)))
        z += 1
        hosts.append(f'<div id="{c["id"]}" data-composition-id="{c["id"]}" data-composition-src="compositions/{c["id"]}.html" '
                     f'data-start="{c["start"]:.3f}" data-duration="{c["duration"]:.3f}" data-track-index="{z}" '
                     f'data-track-kind="graphics" data-width="{width}" data-height="{height}" style="z-index:{z}"></div>')
    if words:
        (project_dir / "compositions" / "captions.html").write_text(captions_scene(
            words, width=width, height=height, duration=duration, font_css=font_css, font_face=font_face,
            text_color=text_color, accent=brand.get("caption_accent", brand["primary_color"]), plate=plate, band=band,
            max_words=int(prefs.get("caption_words", 3)), size_mult=float(prefs.get("caption_size", 1.0)),
            case=prefs.get("caption_case", "as-is"), emphasis=prefs.get("emphasis", "keywords") == "keywords",
            font_path=font_file, scrim=scrim))
        z += 1
        hosts.append(f'<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" '
                     f'data-start="0" data-duration="{duration:.3f}" data-track-index="{z}" data-track-kind="captions" '
                     f'data-width="{width}" data-height="{height}" style="z-index:{z}"></div>')
    bg_motion = ""
    if background and not plate:
        bg_motion = ('tl.fromTo("#bg-glow", {opacity: 0.25}, {opacity: 0.6, duration: '
                     f'{duration:.2f}, ease: "sine.inOut"}}, 0);')
    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={width}, height={height}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; background: #000; }}
      #bg-glow {{ position: absolute; left: 10%; top: 8%; width: 80%; height: 45%; border-radius: 50%;
        background: radial-gradient(closest-side, rgba(255,255,255,0.35), rgba(255,255,255,0)); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.3f}" data-width="{width}" data-height="{height}" data-fps="{fps}">
      {root_media}
      {chr(10).join('      ' + h for h in hosts)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {bg_motion}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (project_dir / "index.html").write_text(index)
    (project_dir / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "assets": "assets"},
                                                              "media": {"autoProxy": True}}, indent=2))
    return project_dir


def gates(project_dir: Path, snapshot_at: list[float] | None = None) -> dict:
    """lint -> check (0 errors) -> snapshot. Returns a summary; raises HFError on blocking errors."""
    res: dict = {}
    lint = npx(["lint", "--json"], project_dir)
    try:
        lj = json.loads(lint.stdout)
    except json.JSONDecodeError:
        raise HFError(f"lint did not return JSON: {lint.stdout[-500:]} {lint.stderr[-500:]}")
    res["lint"] = {"ok": lj.get("ok", lj.get("errorCount", 1) == 0), "errors": lj.get("errorCount"),
                   "warnings": lj.get("warningCount"), "findings": [f.get("code") for f in lj.get("findings", [])]}
    chk = npx(["check", "--json"], project_dir)
    try:
        cj = json.loads(chk.stdout)
    except json.JSONDecodeError:
        raise HFError(f"check did not return JSON: {chk.stdout[-500:]} {chk.stderr[-500:]}")
    summary = {}
    for k, v in cj.items():
        if isinstance(v, dict) and "ok" in v:
            summary[k] = {"ok": v["ok"], "errors": v.get("errorCount", 0), "warnings": v.get("warningCount", 0),
                          "findings": [(f.get("code"), f.get("severity"), (f.get("message") or "")[:160]) for f in v.get("findings", [])]}
    res["check"] = {"ok": cj.get("ok"), "browserSkipped": cj.get("browserSkipped"), "sections": summary}
    if not cj.get("ok") or cj.get("browserSkipped"):
        raise HFError("HyperFrames check failed: " + json.dumps(summary)[:3000])
    args = ["snapshot", "--json", "--describe", "false"]
    if snapshot_at:
        args += ["--at", ",".join(f"{t:.2f}" for t in snapshot_at)]
    snap = npx(args, project_dir)
    try:
        sj = json.loads(snap.stdout)
    except json.JSONDecodeError:
        sj = {"raw": snap.stdout[-500:], "err": snap.stderr[-500:]}
    res["snapshot"] = sj
    return res


def render(project_dir: Path, out: Path, quality: str = "draft") -> Path:
    q = {"draft": "draft", "final": "delivery"}.get(quality, quality)
    r = npx(["render", "--quality", q, "--output", str(out)], project_dir, timeout=3600)
    if r.returncode != 0 or not Path(out).exists() or Path(out).stat().st_size == 0:
        raise HFError(f"render failed: {r.stdout[-800:]} {r.stderr[-800:]}")
    return Path(out)
