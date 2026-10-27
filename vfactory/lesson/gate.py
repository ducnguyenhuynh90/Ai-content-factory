"""The gate: objective checks on a built lesson video, and the evidence a reviewer needs to judge the rest.

python -m vfactory.lesson gate LESSON.json --out BUILD_DIR   (BUILD_DIR is what `build --out` wrote)

Writes BUILD_DIR/gate/report.json and pictures to look at:
  gate/hook.jpg      the first 6 s, one frame every 0.5 s (does frame 0 sell the video? does something move at once?)
  gate/scenes.jpg    middle and end frame of every beat (is every picture the image of its line? any glitch?)
  gate/thumb.jpg     the thumbnail as YouTube shows it (small: is the text readable at 320 px?)
Hard fails (verdict "block") are things no viewer should ever see or hear: missing words, glyphs a font cannot draw,
a frozen screen, a hook too slow to land. Everything else is a scored warning for the reviewer (video-gatekeeper).
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import numpy as np

from . import schema, voice

FONT_DIRS = [Path.home() / ".cache" / "hyperframes" / "fonts" / d for d in ("inter", "eb-garamond")]
SAFE = set(" \n\t")

# thresholds (seconds unless noted); see .claude/skills/video-gatekeeper/references/rubric.md for why
HOOK_MAX_S = 7.5          # the hook's spoken line must land inside ~5-7 s
FIRST_WORD_MAX_S = 0.6    # the voice starts at once
DEAD_MAX_S = 3.0          # nothing on screen may stand still longer than this (a question's countdown excepted)
RATE_RANGE = (150, 245)   # Vietnamese syllables per minute, per line: chill but never sluggish or rushed
QUESTION_PAUSE_MIN = 0.55  # silence after a spoken question


def _texts(v, out: list[str]) -> list[str]:
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in ("type", "icon", "cue", "motion", "motion_cue", "art", "ease", "line_cue", "keep_cue", "stop_cue",
                         "strike_cue", "next_cue", "cta_cue", "sources_cue", "ask_cue", "pass_cue", "why_cue", "top_cue",
                         "center_cue", "label_cue", "fast_cue", "attribution"):
                _texts(x, out)
    elif isinstance(v, list):
        for x in v:
            _texts(x, out)
    return out


def font_coverage(lesson: dict) -> dict:
    """Every character that will be drawn (on-screen text and captions) must exist in the bundled fonts; a missing
    Vietnamese glyph falls back to another font and looks broken."""
    try:
        from fontTools.ttLib import TTFont  # type: ignore
    except ImportError:
        return {"checked": False, "reason": "pip install fonttools brotli"}
    fonts = {}
    for d in FONT_DIRS:
        cmap: set[int] = set()
        for f in d.glob("*.woff2"):
            try:
                cmap |= set(TTFont(str(f)).getBestCmap())
            except Exception:  # noqa: BLE001
                continue
        if cmap:
            fonts[d.name] = cmap
    if not fonts:
        return {"checked": False, "reason": "no HyperFrames font cache yet (build once)"}
    strings = _texts([b["visual"] for b in lesson["beats"]], []) + [b["narration"] for b in lesson["beats"]]
    chars = {unicodedata.normalize("NFC", c) for s in strings for c in unicodedata.normalize("NFC", s)} - SAFE
    missing = {name: sorted(c for c in chars if ord(c) not in cmap) for name, cmap in fonts.items()}
    return {"checked": True, "missing": {k: v for k, v in missing.items() if v}}


def copy_lint(lesson: dict) -> list[str]:
    """Typos a proofreader would circle: doubled words, stray spaces, digits in narration, unbalanced quotes."""
    issues = []
    for b in lesson["beats"]:
        n = b["narration"]
        for m in re.finditer(r"\b(\w+) \1\b", n, re.I):
            issues.append(f"{b['id']}: doubled word '{m.group(0)}'")
        if "  " in n or n != n.strip():
            issues.append(f"{b['id']}: stray whitespace in narration")
        if re.search(r"\d", n) and not b.get("allow_digits"):
            issues.append(f"{b['id']}: digits in narration (say numbers as words)")
        if n.count("“") != n.count("”") or n.count('"') % 2:
            issues.append(f"{b['id']}: unbalanced quotes")
        if re.search(r"\s[,.?!:;]", n):
            issues.append(f"{b['id']}: space before punctuation")
        for s in _texts(b["visual"], []):
            if "  " in s:
                issues.append(f"{b['id']}: double space on screen: {s[:40]!r}")
            if len(s) > 60 and b["visual"]["type"] not in ("quote", "end", "question", "timeline", "compare", "list"):
                issues.append(f"{b['id']}: long on-screen text ({len(s)} chars): {s[:40]!r}…")
    return issues


def _contact(video: Path, times: list[float], out: Path, cols: int, width: int) -> None:
    tmp = out.parent / ("_" + out.stem)
    tmp.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={width}:-1,drawtext=text='{t:.1f}s':x=8:y=8:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5",
                        str(tmp / f"{i:03d}.jpg")], capture_output=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", str(tmp / "*.jpg"), "-vf",
                    f"tile={cols}x{(len(times) + cols - 1) // cols}", str(out)], capture_output=True)
    for f in tmp.glob("*.jpg"):
        f.unlink()
    tmp.rmdir()


def run(lesson_path: str | Path, out_dir: str | Path, check: bool = True, listen: bool = True) -> dict:
    lesson_path, out = Path(lesson_path), Path(out_dir)
    L = schema.load(lesson_path)
    lang = L["meta"].get("lang", "en")
    g = out / "gate"
    g.mkdir(parents=True, exist_ok=True)
    timing = json.loads((out / "timing.json").read_text())
    beats = {b["id"]: b for b in L["beats"]}
    mp4 = sorted(out.glob("*_4x3.mp4")) or sorted(out.glob("*.mp4"))
    video = next((m for m in mp4 if "draft" not in m.name), mp4[0] if mp4 else None)
    fails, warns, metrics = [], [], {}

    # --- hook and opening
    t0 = timing["beats"][0]
    metrics["hook_seconds"] = round(t0["narr"], 2)
    metrics["first_word_at"] = round(t0["lead"], 2)
    if t0["narr"] > HOOK_MAX_S:
        fails.append(f"hook takes {t0['narr']:.1f}s to say (max {HOOK_MAX_S}s): cut it to the paradox")
    if t0["lead"] > FIRST_WORD_MAX_S:
        warns.append(f"first word at {t0['lead']:.2f}s: start speaking at once")
    title_at = next((tm["start"] for tm in timing["beats"] if beats[tm["id"]]["visual"]["type"] == "title"), None)
    metrics["title_sting_at"] = title_at
    if title_at is not None and title_at > 22:
        warns.append(f"title sting at {title_at:.0f}s: keep it inside the first ~20 s")

    # --- voice: pace per line, pauses after questions, words heard
    rates, pauses, missing, names = {}, [], [], []
    for tm in timing["beats"]:
        b = beats[tm["id"]]
        if not tm["narr"]:
            continue
        n = len(schema.words(b["narration"]))
        rates[tm["id"]] = round(n / tm["narr"] * 60)
        wav = out / "vo" / f"{tm['id']}.wav"
        at = voice.align(wav, b["narration"], lang) if wav.exists() else None
        if at:
            for i, w in enumerate(at[:-1]):
                if w["word"].endswith("?"):
                    pauses.append({"id": tm["id"], "after": w["word"], "pause": round(at[i + 1]["start"] - w["end"], 2)})
        if listen and wav.exists():
            try:
                import soundfile as sf

                y, sr = sf.read(str(wav), dtype="float32")
                heard = " ".join(x[0] for x in voice._heard_words(y, sr, lang))
                nt = [voice._norm(x) for x in b["narration"].split()]
                ht = [voice._norm(x) for x in heard.split()]
                sm = difflib.SequenceMatcher(None, nt, ht, autojunk=False)
                gone = [" ".join(nt[a1:a2]) for op, a1, a2, _, _ in sm.get_opcodes() if op == "delete" and a2 - a1 >= 2]
                if gone:
                    missing.append({"id": tm["id"], "missing": gone, "heard": heard})
                for nm in set(re.findall(r"\b[A-Z][a-zA-Z]+(?:[- ][A-Z][a-zA-Z]+)*", b["narration"])):
                    if nm.split()[0].lower() not in heard.lower() and nm.split()[-1].lower() not in heard.lower():
                        names.append({"id": tm["id"], "name": nm, "heard": heard[:120]})
            except ImportError:
                listen = False
    metrics["syllables_per_min"] = rates
    slow = {k: v for k, v in rates.items() if v < RATE_RANGE[0]}
    fast = {k: v for k, v in rates.items() if v > RATE_RANGE[1]}
    if fast:
        warns.append(f"lines read too fast (> {RATE_RANGE[1]}/min): {fast}")
    if slow:
        warns.append(f"lines read too slowly (< {RATE_RANGE[0]}/min): {slow}")
    short = [p for p in pauses if p["pause"] < QUESTION_PAUSE_MIN]
    metrics["question_pauses"] = pauses
    if short:
        warns.append(f"no beat of silence after a question: {short}")
    if missing:
        fails.append(f"words the voice dropped (re-take those lines with 'take'): {missing}")
    if names:
        warns.append(f"names not recognisable by ear: {names}")

    # --- fonts and copy
    fc = font_coverage(L)
    metrics["fonts"] = fc
    if fc.get("missing"):
        fails.append(f"characters the fonts cannot draw: {fc['missing']}")
    cl = copy_lint(L)
    if cl:
        warns += cl

    # --- what HyperFrames measures on the real timeline: frozen stretches, unreadable lines, layout, contrast
    if check:
        r = subprocess.run(["npx", "--yes", "hyperframes", "check", "--json"], cwd=out / "hf", capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)
            metrics["hyperframes"] = {k: v["ok"] for k, v in d.items() if isinstance(v, dict) and "ok" in v}
            for k, ok in metrics["hyperframes"].items():
                if not ok:
                    fails.append(f"hyperframes {k} check failed: {[f.get('message', '')[:120] for f in d[k].get('findings', [])][:5]}")
            q_spans = [(tm["start"], tm["start"] + tm["dur"]) for tm in timing["beats"] if beats[tm["id"]]["visual"]["type"] in ("question", "end")]
            for f in d.get("craft", {}).get("findings", []):
                msg = f.get("message", "")
                m = re.search(r"for ([\d.]+) s \(([\d.]+)", msg)
                if f.get("code") == "dead_stretch" and m:
                    s0 = float(m.group(2))
                    excused = any(a <= s0 <= b for a, b in q_spans)
                    (warns if excused or float(m.group(1)) <= DEAD_MAX_S + 0.5 else fails).append(f"frozen screen: {msg[:110]}")
                elif f.get("code") == "line_unread":
                    warns.append(f"line too short to read: {msg[:120]}")
        except json.JSONDecodeError:
            warns.append("hyperframes check did not return JSON")

    # --- sound and length
    bj = json.loads((out / "build.json").read_text()) if (out / "build.json").exists() else {}
    loud = bj.get("loudness", {})
    metrics["loudness"] = loud
    if loud and abs(loud.get("integrated_lufs", -16) + 16) > 1.5:
        warns.append(f"loudness {loud.get('integrated_lufs')} LUFS (target -16 ±1)")
    if loud and loud.get("true_peak_dbfs", -2) > -1.0:
        warns.append(f"true peak {loud.get('true_peak_dbfs')} dBFS (keep under -1)")
    metrics["duration_s"] = timing["total"]
    lo, hi = L["meta"].get("target_minutes", [3, 5])
    if not lo * 60 * 0.9 <= timing["total"] <= hi * 60 * 1.1:
        warns.append(f"duration {timing['total'] / 60:.1f} min outside {lo}-{hi} min")

    # --- re-hooks: a question, a twist or a myth broken at least every ~60 s
    turns = [tm["start"] for tm in timing["beats"] if beats[tm["id"]]["act"] in ("misconception", "complication", "turn", "question")
             or "?" in beats[tm["id"]]["narration"]]
    gaps = np.diff([0.0] + turns + [timing["total"]]) if turns else [timing["total"]]
    metrics["longest_without_rehook_s"] = round(float(max(gaps)), 1)
    if max(gaps) > 75:
        warns.append(f"{max(gaps):.0f}s without a question, twist or broken myth: add a re-hook")

    # --- pictures for the reviewer
    if video:
        _contact(video, [i * 0.5 for i in range(12)], g / "hook.jpg", 6, 360)
        mids = []
        for tm in timing["beats"]:
            mids += [tm["start"] + tm["dur"] * 0.5, tm["start"] + tm["dur"] - 0.4]
        _contact(video, mids, g / "scenes.jpg", 8, 300)
        thumb = sorted(out.glob("*_thumbnail.png"))
        if thumb:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(thumb[0]), "-vf", "scale=320:-1", str(g / "thumb.jpg")], capture_output=True)
    else:
        fails.append("no rendered video found")

    yt = L["meta"].get("youtube")
    if yt:  # the packaging the reviewer set, ready to paste into YouTube Studio
        (g / "youtube.md").write_text(f"# {yt.get('title', '')}\n\nThumbnail: {yt.get('thumbnail_text', '')}\n\n"
                                      f"{yt.get('description', '')}\n\nTags: {', '.join(yt.get('tags', []))}\n")
        if len(yt.get("title", "")) > 70:
            warns.append(f"YouTube title is {len(yt['title'])} chars (keep ≤ 60-70)")
    else:
        warns.append("no meta.youtube packaging (title, thumbnail_text, description, tags)")
    verdict = "block" if fails else ("revise" if warns else "pass")
    rep = {"lesson": str(lesson_path), "video": str(video) if video else None, "verdict": verdict, "fails": fails,
           "warnings": warns, "metrics": metrics,
           "evidence": {k: str(g / f"{k}.jpg") for k in ("hook", "scenes", "thumb") if (g / f"{k}.jpg").exists()}}
    (g / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep
