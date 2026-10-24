"""Narration with local TTS. One clip per beat, cached by content.

English: Kokoro-82M (Apache-2.0), fetched once from the kokoro-onnx GitHub release into ~/.cache/vfactory/kokoro.
Other languages: Piper VITS voices named "piper:<voice>" (e.g. "piper:vi_VN-vais1000-medium", which speaks all six
Vietnamese tones), fetched once from the sherpa-onnx `tts-models` GitHub release into ~/.cache/vfactory/piper.
No text or audio ever leaves the machine.
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
PIPER_DIR = Path.home() / ".cache" / "vfactory" / "piper"
PIPER_RELEASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"
SR = 24000
SENTENCE_GAP = 0.32  # seconds of air between Piper sentences
_ENGINE = None
_PIPER: dict = {}


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


def piper_engine(name: str):
    """A Piper voice by name; the model is downloaded once (sherpa-onnx packs it with its config)."""
    if name not in _PIPER:
        try:
            from piper import PiperVoice  # type: ignore
        except ImportError as e:
            raise VoiceUnavailable("pip install piper-tts soundfile") from e
        d = PIPER_DIR / f"vits-piper-{name}"
        model = d / f"{name}.onnx"
        if not model.exists():
            PIPER_DIR.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(f'curl -sSfL "{PIPER_RELEASE}/vits-piper-{name}.tar.bz2" | tar xj -C "{PIPER_DIR}"',
                               shell=True, capture_output=True, text=True)
            if r.returncode != 0 or not model.exists():
                raise VoiceUnavailable(f"could not download Piper voice {name}: {r.stderr.strip()[:200]}")
        _PIPER[name] = PiperVoice.load(str(model))
    return _PIPER[name]


def _resample(y: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return y
    n = int(round(len(y) * sr_out / sr_in))
    return np.interp(np.arange(n) * sr_in / sr_out, np.arange(len(y)), y).astype("float32")


def piper_create(text: str, name: str, speed: float) -> tuple[np.ndarray, int]:
    from piper import SynthesisConfig  # type: ignore

    pv = piper_engine(name)
    sr = pv.config.sample_rate
    gap = np.zeros(int(SENTENCE_GAP * sr), dtype="float32")
    parts = []
    for chunk in pv.synthesize(text, syn_config=SynthesisConfig(length_scale=1.0 / speed)):
        parts += [_trim(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16).astype("float32") / 32768.0, pad=600), gap]
    y = np.concatenate(parts[:-1]) if parts else np.zeros(1, dtype="float32")
    return _resample(y, sr, SR), SR


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
    if voice.startswith("piper:"):
        samples, sr = piper_create(spoken, voice.split(":", 1)[1], speed)
    else:
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
