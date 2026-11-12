"""Narration for shorts, with word timings for karaoke captions.

Providers (meta.voice):
- Microsoft neural voices via `edge-tts` (pip install edge-tts): "vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural",
  "en-US-AndrewMultilingualNeural", ... Real word boundaries come back with the audio. Needs internet: the TEXT is
  sent to Microsoft's speech service, nothing else.
- Kokoro (offline, English only): "kokoro:bm_george" (pip install -e .[lesson]).
- The person's own recording: beat "audio": "path/to/b03.wav" (any format ffmpeg reads); timings are estimated.
- "none": no voice (text-on-screen story over music); timings come from reading speed.

Every clip is a 48 kHz mono WAV; results are cached by content so rebuilding after a visual edit is instant.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np

from .. import audio as A
from .. import ffmpeg as ff
from . import schema

CACHE = Path.home() / ".cache" / "vfactory" / "shorts_tts"
SR = A.SR
VOICES = {
    "vi": {"male": "vi-VN-NamMinhNeural", "female": "vi-VN-HoaiMyNeural"},
    "en": {"male": "en-US-AndrewMultilingualNeural", "female": "en-US-AvaMultilingualNeural"},
}


class VoiceUnavailable(RuntimeError):
    pass


def provider(voice: str | None) -> str:
    v = (voice or "").strip()
    if not v or v == "none":
        return "none"
    if v.startswith("kokoro:"):
        return "kokoro"
    if re.match(r"^[a-z]{2}-[A-Z]{2}-\w+Neural$", v):
        return "edge"
    raise VoiceUnavailable(f"unknown voice {v!r}: use an edge-tts name like {VOICES['vi']['male']}, kokoro:<name>, or none")


def apply_pronunciations(text: str, pronounce: dict | None) -> str:
    for k, v in (pronounce or {}).items():
        text = re.sub(rf"(?<!\w){re.escape(k)}(?!\w)", v, text)
    return text


def estimate_times(text: str, duration: float, start: float = 0.0) -> list[dict]:
    """Word start/end spread by characters, with pauses at punctuation (good to ~0.2 s)."""
    toks = re.findall(r"\S+", text)
    weights = []
    for t in toks:
        w = len(re.sub(r"[^\w]", "", t)) + 2.0
        w += 4 if t[-1:] in ",;:" else 7 if t[-1:] in ".?!…" else 0
        weights.append(w)
    total = sum(weights) or 1.0
    out, t = [], start
    for tok, w in zip(toks, weights):
        d = (duration - start) * w / total
        out.append({"word": tok, "start": round(t, 3), "end": round(t + d * 0.85, 3)})
        t += d
    return out


def _to_wav(src: Path, dst: Path) -> float:
    ff.run(["-i", str(src), "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)])
    return ff.probe(dst).duration


def _edge(text: str, voice: str, rate: str, mp3: Path) -> list[dict]:
    try:
        import edge_tts  # type: ignore
    except ImportError as e:
        raise VoiceUnavailable("pip install edge-tts  (or set meta.voice to 'none' / record the beats yourself)") from e

    async def run() -> list[dict]:
        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        marks = []
        with open(mp3, "wb") as f:
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    s = chunk["offset"] / 1e7
                    marks.append({"word": chunk["text"], "start": round(s, 3), "end": round(s + chunk["duration"] / 1e7, 3)})
        return marks

    try:
        return asyncio.run(run())
    except Exception as e:  # network refused, service changed, voice unknown
        raise VoiceUnavailable(f"edge-tts failed for voice {voice}: {e}") from e


def synth(text: str, out_wav: Path, voice: str, rate: str = "+0%", pronounce: dict | None = None,
          lang: str = "vi") -> tuple[float, list[dict]]:
    """Speak `text` into out_wav. Returns (duration, [{word, start, end}]) with the ORIGINAL words (for captions)."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    kind = provider(voice)
    if kind == "none":
        d = schema.est_seconds(text, lang, rate) + 0.15
        A.write_wav(out_wav, np.zeros((int(SR * d), 2), dtype="float32"))
        return d, estimate_times(text, d)
    spoken = apply_pronunciations(text, pronounce)
    key = hashlib.sha1(json.dumps([spoken, voice, rate]).encode()).hexdigest()[:16]
    CACHE.mkdir(parents=True, exist_ok=True)
    cached_wav, cached_meta = CACHE / f"{key}.wav", CACHE / f"{key}.json"
    if not (cached_wav.exists() and cached_meta.exists()):
        if kind == "edge":
            mp3 = CACHE / f"{key}.mp3"
            marks = _edge(spoken, voice, rate, mp3)
            dur = _to_wav(mp3, cached_wav)
            mp3.unlink(missing_ok=True)
        else:
            from ..lesson import voice as K
            tmp = CACHE / f"{key}_k.wav"
            K.synth(spoken, tmp, voice.split(":", 1)[1], schema.rate_factor(rate))
            dur = _to_wav(tmp, cached_wav)
            tmp.unlink(missing_ok=True)
            tmp.with_suffix(".json").unlink(missing_ok=True)
            marks = []
        cached_meta.write_text(json.dumps({"duration": dur, "marks": marks}))
    meta = json.loads(cached_meta.read_text())
    shutil.copy2(cached_wav, out_wav)
    dur, marks = meta["duration"], meta["marks"]
    orig = re.findall(r"\S+", text)
    if marks and len(marks) == len(orig):  # same words: keep real timings, show the written form
        return dur, [{**m, "word": w} for m, w in zip(marks, orig)]
    if marks:  # pronunciation hints changed the word count: stretch estimates between first and last real marks
        times = estimate_times(text, marks[-1]["end"], marks[0]["start"])
        return dur, times
    return dur, estimate_times(text, dur)


def from_file(src: str | Path, text: str, out_wav: Path) -> tuple[float, list[dict]]:
    """The person's own recording for one beat."""
    src = Path(src).expanduser()
    if not src.exists():
        raise VoiceUnavailable(f"recording not found: {src}")
    dur = _to_wav(src, out_wav)
    return dur, estimate_times(text, dur)


def find_word(times: list[dict], needle: str, default: float = 0.0) -> float:
    """Start time of the first occurrence of `needle` (one or more words) in the timings."""
    def norm(s: str) -> str:
        return re.sub(r"[^\w%$£€-]", "", s.lower())
    parts = [norm(p) for p in needle.split() if norm(p)]
    if not parts:
        return default
    for i in range(len(times) - len(parts) + 1):
        if all(norm(times[i + j]["word"]) == parts[j] for j in range(len(parts))):
            return times[i]["start"]
    for i, t in enumerate(times):  # prefix match as a fallback ("sụp" finds "sụp,")
        if norm(t["word"]).startswith(parts[0]):
            return t["start"]
    return default
