"""Captions: word timings (source time) -> output timeline -> styled ASS.

Rules carried over from production editors:
- word-level timings only (phrase SRTs lose the gaps that tell you where to break);
- output_time = word.start - piece.src_start (scaled by speed) + piece.out_start;
- captions are burned LAST, after every overlay, so nothing covers them.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import fonts
from .styles import Look, hex_rgb


def load_words(spec) -> list[dict]:
    """Accept a list of dicts or a JSON path. Each word: {source, word, start, end}."""
    if not spec:
        return []
    if isinstance(spec, (str, Path)):
        data = json.loads(Path(spec).read_text())
    else:
        data = spec
    if isinstance(data, dict):  # {"A": [words...]}
        out = []
        for src, ws in data.items():
            out += [{**w, "source": w.get("source", src)} for w in ws]
        return out
    return list(data)


def map_words(words: list[dict], pieces: list[dict]) -> list[dict]:
    """Place source-time words on the output timeline. A word is kept only if it is fully inside a piece."""
    out = []
    for p in pieces:
        if p.get("kind") != "footage":
            continue
        for w in words:
            if w.get("source") != p["source"]:
                continue
            if w["start"] >= p["src_start"] - 0.02 and w["end"] <= p["src_end"] + 0.05:
                sp = p.get("speed", 1.0)
                s = (w["start"] - p["src_start"]) / sp + p["out_start"]
                e = (min(w["end"], p["src_end"]) - p["src_start"]) / sp + p["out_start"]
                out.append({"word": w["word"].strip(), "start": max(p["out_start"], s), "end": max(s + 0.05, e)})
    return sorted(out, key=lambda w: w["start"])


def chunk(words: list[dict], max_words: int, min_dur: float = 0.35, gap_break: float = 0.3) -> list[list[dict]]:
    """Break on sentence ends and pauses; never leave a 1-2 word orphan at the end of a sentence;
    grow a cue rather than flash it for less than min_dur."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur:
            pause = w["start"] - cur[-1]["end"] > gap_break
            full = len(cur) >= max_words
            if full and not pause:
                rest = 0  # words left in this sentence, including w
                for x in words[i:]:
                    rest += 1
                    if x["word"][-1:] in ".?!" or rest > 2:
                        break
                if rest <= 2 and words[i + rest - 1]["word"][-1:] in ".?!":
                    full = False  # absorb the orphan
            short = cur[-1]["end"] - cur[0]["start"] < min_dur and not pause
            if (pause or full) and not short:
                chunks.append(cur)
                cur = []
        cur.append(w)
        if w["word"][-1:] in ".?!" and cur[-1]["end"] - cur[0]["start"] >= min_dur:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _ass_color(hexcol: str, alpha: int = 0) -> str:
    r, g, b = hex_rgb(hexcol)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def _ts(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def build_ass(words: list[dict], look: Look, width: int, height: int, out: str | Path,
              blackout: list[tuple[float, float]] | None = None) -> Path | None:
    if not words:
        return None
    ty, pal = look.type, look.palette
    size = int(height * look.caption_size) if height <= width else int(width * look.caption_size * 1.25)
    family = fonts.ass_family(ty.caption)
    bold = -1 if ty.caption in ("inter", "inter-display") else 0
    if height > width:
        margin_v = int(height * 0.30)  # vertical social: lower-middle, clear of UI chrome
    elif look.letterbox:
        bar = max(0, (height - width / look.letterbox) / 2)
        margin_v = int(bar + height * 0.04)
    else:
        margin_v = int(height * 0.07)
    outline = max(1, round(size * 0.06))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{family},{size},{_ass_color('#FFFFFF')},{_ass_color(pal.caption_hi)},{_ass_color('#000000', 0x40)},{_ass_color('#000000', 0x80)},{bold},0,0,0,100,100,{size * 0.01:.1f},0,1,{outline},{max(1, outline // 2)},2,{int(width * 0.08)},{int(width * 0.08)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    hi = _ass_color(pal.caption_hi)
    lines = []
    blackout = blackout or []

    def blocked(t0, t1):
        return any(a < t1 and t0 < b for a, b in blackout)

    for ch in chunk(words, look.caption_words):
        start, end = ch[0]["start"], ch[-1]["end"] + 0.12
        if blocked(start, end):
            continue
        texts = [w["word"].upper() if look.caption_case == "upper" else w["word"] for w in ch]
        if not look.caption_karaoke:
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{{\\blur0.6\\fad(80,80)}}{_esc(' '.join(texts))}")
            continue
        # One event per active word: the active word is highlighted and pops slightly.
        for i, w in enumerate(ch):
            s = w["start"] if i else start
            e = ch[i + 1]["start"] if i + 1 < len(ch) else end
            parts = []
            for j, tx in enumerate(texts):
                if j == i:
                    parts.append(f"{{\\c{hi}\\fscx100\\fscy100\\t(0,90,\\fscx108\\fscy108)\\t(90,180,\\fscx104\\fscy104)}}{_esc(tx)}{{\\c&HFFFFFF&\\fscx100\\fscy100}}")
                else:
                    parts.append(_esc(tx))
            intro = "\\fad(60,0)" if i == 0 else ""
            lines.append(f"Dialogue: 0,{_ts(s)},{_ts(e)},Cap,,0,0,0,,{{\\blur0.6{intro}}}{' '.join(parts)}")
    Path(out).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return Path(out)


def transcribe(path: str, cache_dir: str | Path, model: str = "small") -> list[dict]:
    """Word-level transcription with faster-whisper if installed. Cached per source."""
    cache = Path(cache_dir) / (Path(path).stem + ".words.json")
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise RuntimeError("faster-whisper is not installed; pip install faster-whisper, or pass captions.words "
                           "as a word-timing JSON from any ASR (ElevenLabs Scribe, Deepgram, WhisperX...)") from e
    m = WhisperModel(model, device="auto", compute_type="auto")
    segments, _ = m.transcribe(path, word_timestamps=True, vad_filter=True)
    words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for seg in segments for w in seg.words]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(words))
    return words
