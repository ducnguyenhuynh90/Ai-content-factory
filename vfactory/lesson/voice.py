"""Narration with local TTS. One clip per beat, cached by content.

English: Kokoro-82M (Apache-2.0), fetched once from the kokoro-onnx GitHub release into ~/.cache/vfactory/kokoro.
Studio narration: "gemini:<Voice>" (e.g. "gemini:Charon") uses Gemini TTS, which speaks Vietnamese (vi-VN) and follows a
spoken style direction (pace, warmth, storyteller tone). It needs GEMINI_API_KEY and sends the narration text to Google;
clips are cached by content, so a rebuild only pays for changed lines.
Offline studio narration: "omnivoice:<speaker attributes>" (e.g. "omnivoice:male, middle-aged, low pitch") uses OmniVoice
(k2-fsa, Apache-2.0; ~8,500 h of Vietnamese in training). The narrator is designed once from the attributes with a fixed
seed, saved, then cloned for every line so the whole video keeps one voice; or clone your own `ref` clip. Weights come
from Hugging Face (k2-fsa/OmniVoice) on first use.
Other languages offline: Piper VITS voices named "piper:<voice>" (e.g. "piper:vi_VN-vais1000-medium", which speaks all six
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


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_TTS_MODELS = ("gemini-2.5-pro-preview-tts", "gemini-2.5-pro-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts")


def _gemini_key() -> str:
    import os

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise VoiceUnavailable("Gemini TTS needs GEMINI_API_KEY in the environment")
    return key


def _http_json(url: str, body: dict | None = None, timeout: int = 180) -> dict:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": _gemini_key()})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise VoiceUnavailable(f"Gemini TTS {e.code}: {e.read()[:300].decode(errors='replace')}") from e


_GEMINI_MODEL: str | None = None


def gemini_model(preferred: str | None = None) -> str:
    """The first TTS model this key can use, in order of narration quality."""
    global _GEMINI_MODEL
    if preferred:
        return preferred
    if _GEMINI_MODEL is None:
        names = {m["name"].split("/")[-1] for m in _http_json(f"{GEMINI_API}/models?pageSize=1000").get("models", [])}
        found = [m for m in GEMINI_TTS_MODELS if m in names] or sorted(n for n in names if "tts" in n)
        if not found:
            raise VoiceUnavailable("this Gemini key lists no TTS model")
        _GEMINI_MODEL = found[0]
    return _GEMINI_MODEL


def gemini_create(text: str, voice_name: str, style: str = "", model: str | None = None) -> tuple[np.ndarray, int]:
    """Gemini TTS returns 24 kHz 16-bit mono PCM. The style direction is spoken to the model, not read aloud."""
    import base64

    prompt = f"{style.strip()}\n\n{text}" if style.strip() else text
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}}}}
    out = _http_json(f"{GEMINI_API}/models/{gemini_model(model)}:generateContent", body)
    try:
        data = out["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except (KeyError, IndexError) as e:
        raise VoiceUnavailable(f"Gemini TTS returned no audio: {json.dumps(out)[:300]}") from e
    y = np.frombuffer(base64.b64decode(data), dtype=np.int16).astype("float32") / 32768.0
    return y, 24000


OMNI_DIR = Path.home() / ".cache" / "vfactory" / "omnivoice"
OMNI_NARRATOR_TEXT = {"vi": "Có những cuốn sách đọc một lần là đủ. Và có những cuốn sách đi theo ta suốt cả cuộc đời.",
                      "en": "Some books you read once. Others stay with you for the rest of your life."}
_OMNI = None


def omni_engine():
    global _OMNI
    if _OMNI is None:
        try:
            import torch
            from omnivoice import OmniVoice  # type: ignore
        except ImportError as e:
            raise VoiceUnavailable("pip install omnivoice") from e
        dev = "cuda:0" if torch.cuda.is_available() else "cpu"
        try:
            _OMNI = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dev,
                                              dtype=torch.float16 if dev.startswith("cuda") else torch.float32)
        except Exception as e:  # noqa: BLE001  (network or hub errors surface as many types)
            raise VoiceUnavailable(f"could not load k2-fsa/OmniVoice (Hugging Face reachable?): {str(e)[:200]}") from e
    return _OMNI


def omni_narrator(instruct: str, lang: str, seed: int = 7) -> tuple[Path, str]:
    """Design the narrator once from speaker attributes and keep the clip: every line then clones it, so the voice
    never drifts between beats (voice design alone samples a new speaker each call)."""
    import soundfile as sf
    import torch

    text = OMNI_NARRATOR_TEXT.get(lang[:2], OMNI_NARRATOR_TEXT["en"])
    key = hashlib.sha1(json.dumps([instruct, lang, seed, text]).encode()).hexdigest()[:10]
    ref = OMNI_DIR / f"narrator_{key}.wav"
    if not ref.exists():
        OMNI_DIR.mkdir(parents=True, exist_ok=True)
        torch.manual_seed(seed)
        audio = omni_engine().generate(text=text, language=lang[:2], instruct=instruct)
        sf.write(str(ref), audio[0], 24000)
    return ref, text


def omni_create(text: str, instruct: str, speed: float, lang: str, ref: str | None = None, ref_text: str | None = None,
                seed: int = 7) -> tuple[np.ndarray, int]:
    import torch

    if not ref:
        ref, ref_text = omni_narrator(instruct, lang, seed)
    torch.manual_seed(seed)
    audio = omni_engine().generate(text=text, language=lang[:2], ref_audio=str(ref), ref_text=ref_text, speed=speed)
    return np.asarray(audio[0], dtype="float32"), 24000


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


def apply_fx(y: np.ndarray, sr: int, fx: dict) -> np.ndarray:
    """Re-voice a clip (ffmpeg rubberband): `formant` shifts pitch and vocal tract together (a bigger or smaller
    speaker), then `pitch` moves only the pitch (formants kept). Both scale the whole contour, so the six Vietnamese
    tones keep their shapes. formant 0.82 + pitch 0.64 turns a ~240 Hz voice into a ~125 Hz male register.
    `warm` adds body (low shelf), softens sibilance and gives a small room."""
    import soundfile as sf
    import tempfile

    chain = []
    if fx.get("formant", 1.0) != 1.0:
        chain.append(f"rubberband=pitch={fx['formant']}:formant=shifted:pitchq=quality")
    if fx.get("pitch", 1.0) != 1.0:
        chain.append(f"rubberband=pitch={fx['pitch']}:formant=preserved:pitchq=quality")
    if fx.get("warm"):
        chain.append("lowshelf=f=160:g=2.5,equalizer=f=3200:t=q:w=1:g=-1.5,highshelf=f=7500:g=-3,aecho=0.8:0.6:28:0.12")
    if not chain:
        return y
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.wav", Path(d) / "b.wav"
        sf.write(str(a), y, sr)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-af", ",".join(chain), "-ar", str(sr), str(b)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise VoiceUnavailable(f"voice fx failed: {r.stderr.strip()[:200]}")
        z, _ = sf.read(str(b), dtype="float32")
    return z


def synth(text: str, out: Path, voice: str = "bm_george", speed: float = 0.95, lang: str = "en-us",
          pronounce: dict | None = None, fx: dict | None = None, style: str = "", model: str | None = None,
          ref: str | None = None, ref_text: str | None = None, seed: int = 7) -> float:
    """Write a 24 kHz mono WAV; returns its duration in seconds. Cached by (text, voice, speed, fx)."""
    import soundfile as sf

    spoken = apply_pronunciations(text, pronounce or {})
    key = hashlib.sha1(json.dumps([spoken, voice, speed, lang] + ([fx] if fx else []) +
                                  ([style, model] if voice.startswith("gemini:") else []) +
                                  ([ref, ref_text] + ([seed] if seed != 7 else []) if voice.startswith("omnivoice:") else [])).encode()).hexdigest()[:12]
    meta = out.with_suffix(".json")
    if out.exists() and meta.exists() and json.loads(meta.read_text()).get("key") == key:
        return json.loads(meta.read_text())["duration"]
    if voice.startswith("omnivoice:"):
        samples, sr = omni_create(spoken, voice.split(":", 1)[1].strip(), speed, lang, ref, ref_text, seed)
    elif voice.startswith("gemini:"):  # pace comes from the style direction, not a speed knob
        samples, sr = gemini_create(spoken, voice.split(":", 1)[1], style, model)
    elif voice.startswith("piper:"):
        samples, sr = piper_create(spoken, voice.split(":", 1)[1], speed)
    else:
        lang = "en-us" if lang == "en" else lang
        if voice.startswith(("bf_", "bm_")) and lang == "en-us":
            lang = "en-gb"
        samples, sr = engine().create(spoken, voice=voice, speed=speed, lang=lang)
    y = _trim(np.asarray(samples, dtype="float32"))
    if fx:
        y = apply_fx(y, sr, fx)
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


_WHISPER = None


def _norm(w: str) -> str:
    import unicodedata

    return re.sub(r"[^\w]", "", unicodedata.normalize("NFC", w).lower())


def align(wav: Path, text: str, lang: str = "vi", model: str = "small") -> list[dict] | None:
    """Real word timings: Whisper listens to the clip, its words are matched to the script's words in order, and
    script words it heard differently (respelled names) are spread between the nearest matched neighbours.
    Returns the word_times() format, or None when faster-whisper is unavailable. Cached next to the clip."""
    global _WHISPER
    wav = Path(wav)
    cache = wav.with_suffix(".align.json")
    key = hashlib.sha1(json.dumps([text, wav.stat().st_size, wav.stat().st_mtime_ns, model]).encode()).hexdigest()[:12]
    if cache.exists() and json.loads(cache.read_text()).get("key") == key:
        return json.loads(cache.read_text())["times"]
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return None
    import soundfile as sf

    if _WHISPER is None:
        _WHISPER = WhisperModel(model, device="cpu", compute_type="int8")
    y, sr = sf.read(str(wav), dtype="float32")
    y = _resample(y if y.ndim == 1 else y.mean(axis=1), sr, 16000)  # handed over as samples: no decoder dependency
    segs, _ = _WHISPER.transcribe(y, language=lang[:2], word_timestamps=True, beam_size=5, vad_filter=False)
    heard = [(w.word.strip(), w.start, w.end) for sg in segs for w in (sg.words or [])]
    toks = re.findall(r"\S+", text)
    dur = sf.info(str(wav)).duration
    times: list[dict | None] = [None] * len(toks)
    import difflib

    sm = difflib.SequenceMatcher(None, [_norm(t) for t in toks], [_norm(h[0]) for h in heard], autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            _, a, b = heard[blk.b + k]
            times[blk.a + k] = {"word": toks[blk.a + k], "start": round(a, 3), "end": round(b, 3)}
    # spread unmatched runs between their matched neighbours, by length
    i = 0
    while i < len(toks):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(toks) and times[j] is None:
            j += 1
        lo = times[i - 1]["end"] if i > 0 else 0.0
        hi = times[j]["start"] if j < len(toks) else dur
        w = [len(_norm(t)) + 1 for t in toks[i:j]]
        acc = lo
        for k, t in enumerate(toks[i:j]):
            d = (hi - lo) * w[k] / sum(w)
            times[i + k] = {"word": t, "start": round(acc, 3), "end": round(acc + d * 0.85, 3)}
            acc += d
        i = j
    cache.write_text(json.dumps({"key": key, "times": times, "matched": sum(b.size for b in sm.get_matching_blocks())}))
    return times


def find_word(times: list[dict], needle: str, default: float = 0.0) -> float:
    n = needle.lower().strip()
    parts = n.split()
    for i in range(len(times)):
        seg = " ".join(re.sub(r"[^\w£$%'-]", "", times[j]["word"].lower()) for j in range(i, min(len(times), i + len(parts))))
        if seg.startswith(re.sub(r"[^\w£$%' -]", "", n)):
            return times[i]["start"]
    return default
