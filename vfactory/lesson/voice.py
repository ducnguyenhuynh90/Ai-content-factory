"""Narration with local TTS (Kokoro-82M, Apache-2.0, offline). One clip per beat, cached by content.

Model files are fetched once from the kokoro-onnx GitHub release into ~/.cache/vfactory/kokoro;
no text or audio ever leaves the machine.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np

MODEL_DIR = Path.home() / ".cache" / "vfactory" / "kokoro"
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
SR = 24000
_ENGINE = None


class VoiceUnavailable(RuntimeError):
    pass


def ensure_model() -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        p = MODEL_DIR / f
        if not p.exists() or p.stat().st_size < 1_000_000:
            r = subprocess.run(["curl", "-sSfL", "-o", str(p), f"{RELEASE}/{f}"], capture_output=True, text=True)
            if r.returncode != 0:
                raise VoiceUnavailable(f"could not download {f}: {r.stderr.strip()[:200]}")
    return MODEL_DIR


def engine():
    global _ENGINE
    if _ENGINE is None:
        try:
            from kokoro_onnx import Kokoro  # type: ignore
        except ImportError as e:
            raise VoiceUnavailable("pip install kokoro-onnx soundfile") from e
        d = ensure_model()
        _ENGINE = Kokoro(str(d / FILES[0]), str(d / FILES[1]))
    return _ENGINE


def apply_pronunciations(text: str, pronounce: dict[str, str]) -> str:
    for k, v in (pronounce or {}).items():
        text = re.sub(rf"\b{re.escape(k)}\b", v, text)
    return text


def _trim(y: np.ndarray, th: float = 0.008, pad: int = 1200) -> np.ndarray:
    idx = np.where(np.abs(y) > th)[0]
    if not idx.size:
        return y
    return y[max(0, idx[0] - pad): idx[-1] + pad]


def synth(text: str, out: Path, voice: str = "bm_george", speed: float = 0.95, lang: str = "en-us",
          pronounce: dict | None = None) -> float:
    """Write a 24 kHz mono WAV; returns its duration in seconds. Cached by (text, voice, speed)."""
    import soundfile as sf

    spoken = apply_pronunciations(text, pronounce or {})
    key = hashlib.sha1(json.dumps([spoken, voice, speed, lang]).encode()).hexdigest()[:12]
    meta = out.with_suffix(".json")
    if out.exists() and meta.exists() and json.loads(meta.read_text()).get("key") == key:
        return json.loads(meta.read_text())["duration"]
    if voice.startswith(("bf_", "bm_")) and lang == "en-us":
        lang = "en-gb"
    samples, sr = engine().create(spoken, voice=voice, speed=speed, lang=lang)
    y = _trim(np.asarray(samples, dtype="float32"))
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), y, sr)
    dur = len(y) / sr
    meta.write_text(json.dumps({"key": key, "duration": dur, "voice": voice, "speed": speed}))
    return dur


def word_times(text: str, duration: float) -> list[dict]:
    """Estimate word start/end inside a clip: time ~ characters spoken, plus pauses at punctuation.
    Good to ~0.2 s, which is enough to land a visual on its word."""
    toks = re.findall(r"\S+", text)
    weights = []
    for t in toks:
        w = len(re.sub(r"[^\w]", "", t)) + 2.0
        if t[-1:] in ",;:":
            w += 4
        elif t[-1:] in ".?!":
            w += 7
        weights.append(w)
    total = sum(weights) or 1
    out, t = [], 0.0
    for tok, w in zip(toks, weights):
        d = duration * w / total
        out.append({"word": tok, "start": round(t, 3), "end": round(t + d * 0.8, 3)})
        t += d
    return out


def find_word(times: list[dict], needle: str, default: float = 0.0) -> float:
    n = needle.lower().strip()
    parts = n.split()
    for i in range(len(times)):
        seg = " ".join(re.sub(r"[^\w£$%'-]", "", times[j]["word"].lower()) for j in range(i, min(len(times), i + len(parts))))
        if seg.startswith(re.sub(r"[^\w£$%' -]", "", n)):
            return times[i]["start"]
    return default
