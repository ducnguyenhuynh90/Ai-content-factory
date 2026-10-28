"""The gate: objective checks on a built lesson video, and the evidence a reviewer needs to judge the rest.

python -m vfactory.lesson gate LESSON.json --out BUILD_DIR   (BUILD_DIR is what `build --out` wrote)

Writes BUILD_DIR/gate/report.json and pictures to look at:
  gate/hook.jpg      the first 6 s, one frame every 0.5 s (does frame 0 sell the video? does something move at once?)
  gate/scenes.jpg    middle and end frame of every beat (is every picture the image of its line? any glitch?)
  gate/thumb.jpg     the thumbnail as YouTube shows it (small: is the text readable at 320 px?)
  gate/opening.txt   the first 30 s as spoken, sentence by sentence with timestamps (rubric D)
Hard fails (verdict "block") are technical defects no viewer should meet: dropped words, glyphs the fonts cannot draw,
a broken layout or contrast. Everything else is evidence for the reviewer's judgment (video-gatekeeper rubric), tagged
with the rubric category it informs: [D] opening, [E] structure, [I] presentation, [K] sharing, [L] conversion…
Pacing findings (frozen screens, unread lines) inform [E]/[I]; they are not verdicts by themselves.
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


VI_NEVER_DOUBLED = {"là", "của", "và", "một", "những", "các", "cho", "với", "thì", "mà", "được", "không", "này", "đó"}
# English names inside Vietnamese text: ASCII words not glued to Vietnamese letters ("Chu" in "Chuỗi" is not a name)
NAME_RE = re.compile(r"(?<![^\W\d_])[A-Z][a-zA-Z]+(?:[- ][A-Z][a-zA-Z]+)*(?![^\W\d_])")
REHOOK_RE = re.compile(r"(^|[.!?…]\s+)(Nhưng|Hóa ra|Thế nhưng|Vậy mà|But|Yet|Turns out)\b")


def _name_heard(name: str, heard: str) -> bool:
    ht = [voice._norm(x) for x in heard.replace("-", " ").split()]
    for part in name.replace("-", " ").split():
        p = voice._norm(part)
        if p in ht or difflib.get_close_matches(p, ht, n=1, cutoff=0.75):
            return True
    return False


VI_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
VI_MAGNITUDE = {"mươi", "mười", "trăm", "nghìn", "triệu", "tỷ"}
VI_NUMWORDS = set(VI_DIGITS) | VI_MAGNITUDE | {"lẻ", "linh", "mốt", "tư", "lăm", "ngàn", "tỉ", "phẩy", "rưỡi"}
VI_SYNONYM = {"ngàn": "nghìn", "linh": "lẻ", "mốt": "một", "tư": "bốn", "lăm": "năm", "tỉ": "tỷ"}


def _vi_three(n: int, full: bool) -> list[str]:
    h, t, u = n // 100, n // 10 % 10, n % 10
    out = [VI_DIGITS[h], "trăm"] if h or full else []
    if t == 0 and u:
        out += (["lẻ"] if out else []) + [VI_DIGITS[u]]
    elif t == 1:
        out += ["mười"] + ([{5: "lăm"}.get(u, VI_DIGITS[u])] if u else [])
    elif t > 1:
        out += [VI_DIGITS[t], "mươi"] + ([{1: "mốt", 5: "lăm"}.get(u, VI_DIGITS[u])] if u else [])
    return out


def vi_number(n: int) -> str:
    """1435 -> 'một nghìn bốn trăm ba mươi lăm', 2001 -> 'hai nghìn lẻ một' (how a Vietnamese narrator reads it)."""
    if n == 0:
        return "không"
    out, groups = [], []
    while n:
        groups.append(n % 1000)
        n //= 1000
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g:
            out += _vi_three(g, full=bool(out)) + ([["", "nghìn", "triệu", "tỷ"][i]] if i else [])
    return " ".join(out)


def _vi_digits_to_words(text: str) -> str:
    """Whisper writes numbers as digits ('1.435', '6,9', '55.000'); spell them out so they compare with the script."""
    def one(m):
        whole, frac = m.group(1), m.group(2)
        w = vi_number(int(re.sub(r"\D", "", whole)))
        return w + (" phẩy " + " ".join(VI_DIGITS[int(c)] for c in frac) if frac else "")
    text = text.replace("%", " phần trăm")
    text = re.sub(r"\b(\d{1,2})\s?[-/]\s?(\d{4})\b", r"\1 năm \2", text)  # "6-1986" = tháng sáu năm 1986
    text = re.sub(r"(?<=\d)\s?[-–]\s?(?=\d)", " ", text)  # "50-50"
    return re.sub(r"(\d{1,3}(?: ?[. ]\d{3})+(?!\d)|\d+)(?:\s?,(\d+))?", one, text)


def _vi_canon(tokens: list[str]) -> list[str]:
    out = [VI_SYNONYM.get(t, t) for t in tokens]
    out = ["bốn" if t == "từ" and i and out[i - 1] == "mươi" else t for i, t in enumerate(out)]  # "hai mươi tư" heard "20, từ"
    return [t for i, t in enumerate(out) if not (t == "không" and i + 1 < len(out) and out[i + 1] == "trăm")
            and not (t == "trăm" and i and out[i - 1] == "không")]


def misread_numbers(narration: str, heard: str) -> list[str]:
    """Spoken numbers in the script that the listener did not hear as said ('một nghìn bốn trăm…' heard as '1, 4, 35')."""
    raw = narration.split()
    nt = _vi_canon([voice._norm(x) for x in raw])
    stops = {i for i, x in enumerate(raw) if re.search(r"[,.;:!?…]$", x)}
    ht = _vi_canon([t for t in (voice._norm(x) for x in _vi_digits_to_words(heard).split()) if t])
    hs = " " + " ".join(ht) + " "
    runs, cur = [], []
    for i, t in enumerate(nt + [""]):
        if t in VI_NUMWORDS:
            cur.append(t)
        if t not in VI_NUMWORDS or i in stops:
            if any(x in VI_MAGNITUDE for x in cur):
                runs.append(" ".join(cur))
            cur = []
    return [r for r in runs if f" {r} " not in hs]


def copy_lint(lesson: dict) -> list[str]:
    """Typos a proofreader would circle: doubled words, stray spaces, digits in narration, unbalanced quotes."""
    issues = []
    for b in lesson["beats"]:
        n = b["narration"]
        vi = lesson["meta"].get("lang") == "vi"
        for m in re.finditer(r"\b(\w+) \1\b", n):
            # Vietnamese reduplication ("mãi mãi", "năm năm", "từ từ") is grammar, not a typo: flag only particles
            if not vi or m.group(1).lower() in VI_NEVER_DOUBLED:
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
        warns.append(f"[D] hook takes {t0['narr']:.1f}s to say (aim ≤ {HOOK_MAX_S}s): does every word earn its place?")
    if t0["lead"] > FIRST_WORD_MAX_S:
        warns.append(f"[D] first word at {t0['lead']:.2f}s: start speaking at once")
    title_at = next((tm["start"] for tm in timing["beats"] if beats[tm["id"]]["visual"]["type"] == "title"), None)
    metrics["title_sting_at"] = title_at
    if title_at is not None and title_at > 22:
        warns.append(f"[D] title sting at {title_at:.0f}s: keep it inside the first ~20 s")

    # --- voice: pace per line, pauses after questions, words heard
    rates, pauses, missing, names, misread = {}, [], [], [], []
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
                bad = misread_numbers(b["narration"], heard) if lang == "vi" else []
                if bad:
                    misread.append({"id": tm["id"], "said_as_written": bad, "heard": heard[:160]})
                if gone:
                    missing.append({"id": tm["id"], "missing": gone, "heard": heard})
                for nm in set(NAME_RE.findall(b["narration"])):
                    if not _name_heard(nm, heard):
                        names.append({"id": tm["id"], "name": nm, "heard": heard[:120]})
            except ImportError:
                listen = False
    metrics["syllables_per_min"] = rates
    slow = {k: v for k, v in rates.items() if v < RATE_RANGE[0]}
    fast = {k: v for k, v in rates.items() if v > RATE_RANGE[1]}
    if fast:
        warns.append(f"[I] lines read fast (> {RATE_RANGE[1]}/min): {fast}")
    if slow:
        warns.append(f"[I] lines read slowly (< {RATE_RANGE[0]}/min): {slow}")
    short = [p for p in pauses if p["pause"] < QUESTION_PAUSE_MIN]
    metrics["question_pauses"] = pauses
    if short:
        warns.append(f"[I] little silence after a question: {short}")
    if missing:
        fails.append(f"words the voice dropped (re-take those lines with 'take'): {missing}")
    if misread:
        fails.append(f"numbers not read as written (re-take those lines with 'take'): {misread}")
    if names:
        warns.append(f"[I] names not recognisable by ear: {names}")

    # --- fonts and copy
    fc = font_coverage(L)
    metrics["fonts"] = fc
    if fc.get("missing"):
        fails.append(f"characters the fonts cannot draw: {fc['missing']}")
    cl = copy_lint(L)
    if cl:
        warns += [f"[I] {x}" for x in cl]

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
                    if not excused and float(m.group(1)) > DEAD_MAX_S:
                        warns.append(f"[E] screen still: {msg[:110]}")
                elif f.get("code") == "line_unread":
                    warns.append(f"[I] line too short to read: {msg[:120]}")
        except json.JSONDecodeError:
            warns.append("hyperframes check did not return JSON")

    # --- sound and length
    bj = json.loads((out / "build.json").read_text()) if (out / "build.json").exists() else {}
    loud = bj.get("loudness", {})
    metrics["loudness"] = loud
    if loud and abs(loud.get("integrated_lufs", -16) + 16) > 1.5:
        warns.append(f"[I] loudness {loud.get('integrated_lufs')} LUFS (target -16 ±1)")
    if loud and loud.get("true_peak_dbfs", -2) > -1.0:
        warns.append(f"[I] true peak {loud.get('true_peak_dbfs')} dBFS (keep under -1)")
    metrics["duration_s"] = timing["total"]
    lo, hi = L["meta"].get("target_minutes", [3, 5])
    if not lo * 60 * 0.9 <= timing["total"] <= hi * 60 * 1.1:
        warns.append(f"[E] duration {timing['total'] / 60:.1f} min outside {lo}-{hi} min")

    # --- re-hooks: a question, a twist or a myth broken at least every ~60 s
    turns = [tm["start"] for tm in timing["beats"] if beats[tm["id"]]["act"] in ("misconception", "complication", "turn", "question")
             or "?" in beats[tm["id"]]["narration"] or REHOOK_RE.search(beats[tm["id"]]["narration"])
             or beats[tm["id"]]["visual"]["type"] in ("swap", "question")]
    gaps = np.diff([0.0] + turns + [timing["total"]]) if turns else [timing["total"]]
    metrics["longest_without_rehook_s"] = round(float(max(gaps)), 1)
    if max(gaps) > 75:
        warns.append(f"[E] {max(gaps):.0f}s without a question, twist or broken myth: does attention hold here?")

    # --- the opening as spoken (rubric D: mark every sentence that is neither value nor necessary setup)
    lines = []
    for tm in timing["beats"]:
        if tm["start"] > 30:
            break
        b = beats[tm["id"]]
        for sent in voice.sentences(b["narration"]):
            lines.append(f"{tm['start'] + tm['lead']:6.1f}s  [{tm['id']}]  {sent}")
    (g / "opening.txt").write_text("\n".join(lines) + "\n")

    # --- the brief and the one primary next step (rubric §1, L)
    brief = L["meta"].get("brief") or {}
    need = ("target_viewer", "central_question", "transformation", "discovery_goal", "primary_conversion", "share_recipient")
    missing_brief = [k for k in need if not brief.get(k)]
    if missing_brief:
        warns.append(f"[A] meta.brief missing {missing_brief}: state the assumptions and write them in")
    endv = next((b["visual"] for b in reversed(L["beats"]) if b["visual"]["type"] == "end"), {})
    ctas = ([endv["ask"]] if endv.get("ask") else []) + ([endv["next"]] if endv.get("next") else []) + \
        [c.strip() for c in endv.get("cta", "").split("·") if c.strip()]
    metrics["end_card_ctas"] = ctas
    if len(ctas) > 2:
        warns.append(f"[L] {len(ctas)} calls to action on the end card {ctas}: keep one primary next step")
    metrics["coverage"] = {"script": True, "render": bool(video), "audio": True, "analytics": "not assessable",
                           "real_shares": "not assessable"}

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
            warns.append(f"[C] YouTube title is {len(yt['title'])} chars (keep ≤ 60-70)")
    else:
        warns.append("[C] no meta.youtube packaging (title, thumbnail_text, description, tags)")
    verdict = "block" if fails else ("revise" if warns else "pass")
    rep = {"lesson": str(lesson_path), "video": str(video) if video else None, "verdict": verdict, "fails": fails,
           "warnings": warns, "metrics": metrics,
           "evidence": {k: str(g / f"{k}.jpg") for k in ("hook", "scenes", "thumb") if (g / f"{k}.jpg").exists()}}
    (g / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep
