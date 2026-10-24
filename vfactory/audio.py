"""Sound design and mix.

Effects are synthesized (no stock libraries, no licensing questions) and tied to
visible events only: a transition, a title landing, a lower third. Few effects,
each on the frame, read as designed; many read as a template.
"""

from __future__ import annotations

import json
import re
import wave
from pathlib import Path

import numpy as np

from . import ffmpeg as ff

SR = 48000


def _env(n: int, attack: float, release_shape: float = 3.0) -> np.ndarray:
    a = max(1, int(n * attack))
    up = np.linspace(0, 1, a) ** 2
    down = np.linspace(1, 0, n - a) ** release_shape
    return np.concatenate([up, down])


def _lowpass(x: np.ndarray, alpha: np.ndarray | float) -> np.ndarray:
    y = np.empty_like(x)
    acc = 0.0
    al = np.broadcast_to(alpha, x.shape)
    for i in range(len(x)):
        acc += al[i] * (x[i] - acc)
        y[i] = acc
    return y


def _noise(n: int, rng) -> np.ndarray:
    return rng.standard_normal(n).astype("float32")


def whoosh(dur: float = 0.7, seed: int = 1) -> tuple[np.ndarray, float]:
    """Air moving past camera: band-limited noise sweeping up then down. Returns (stereo, peak_offset)."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    centre = 0.6
    sweep = np.exp(-((t - centre) ** 2) / 0.04)
    alpha = 0.02 + 0.35 * sweep
    x = _noise(n, rng)
    lp = _lowpass(x, alpha)
    hp = lp - _lowpass(lp, 0.01)
    env = np.exp(-((t - centre) ** 2) / 0.05) * (t < centre) + np.exp(-((t - centre) ** 2) / 0.02) * (t >= centre)
    y = hp * env
    pan = np.sin(np.pi * t) * 0.6
    left, right = y * (1 - pan * (t < 0.5)), y * (1 - pan * (t >= 0.5))
    st = np.stack([left, right], axis=1)
    return _normalize(st, -6), dur * centre


def hit(dur: float = 1.6, seed: int = 2, weight: float = 1.0) -> tuple[np.ndarray, float]:
    """Cinematic impact: sub drop + transient crack + short noise tail."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6) * weight
    crack = _noise(n, rng) * np.exp(-t * 55) * 0.6
    body = _lowpass(_noise(n, rng), 0.08) * np.exp(-t * 6) * 0.8
    y = np.tanh(1.6 * (sub + crack + body))
    # tiny stereo room
    d = int(0.011 * SR)
    left = y
    right = np.concatenate([np.zeros(d), y[:-d]]) * 0.92 + y * 0.08
    return _normalize(np.stack([left, right], axis=1), -3), 0.0


def riser(dur: float = 2.2, seed: int = 3) -> tuple[np.ndarray, float]:
    """Tension build ending exactly at its last sample (the hit lands after it)."""
    rng = np.random.default_rng(seed)
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    alpha = 0.01 + 0.5 * t ** 2
    noise = _lowpass(_noise(n, rng), alpha)
    f = 180 * 2 ** (3 * t)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    y = (noise + tone) * t ** 2.2
    y[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return _normalize(np.stack([y, y], axis=1), -6), dur


def tick(seed: int = 4) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(seed)
    n = int(SR * 0.08)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 2400 * t) * 0.5 + _noise(n, rng) * 0.3) * np.exp(-t * 90)
    return _normalize(np.stack([y, y], axis=1), -12), 0.0


SFX = {"whoosh": whoosh, "hit": hit, "riser": riser, "tick": tick}


def _normalize(x: np.ndarray, peak_db: float) -> np.ndarray:
    peak = np.abs(x).max() + 1e-9
    return (x / peak * 10 ** (peak_db / 20)).astype("float32")


def build_sfx_track(events: list[dict], duration: float, out: str | Path) -> Path | None:
    """events: [{"kind": "hit", "at": 3.2, "gain_db": -4}] where `at` is the visible contact frame."""
    if not events:
        return None
    n = int(SR * (duration + 0.5))
    track = np.zeros((n, 2), dtype="float32")
    for i, ev in enumerate(events):
        fn = SFX.get(ev["kind"])
        if not fn:
            continue
        clip, contact = fn(seed=i + 7)
        start = int((ev["at"] - contact) * SR)
        gain = 10 ** (ev.get("gain_db", 0) / 20)
        a, b = max(0, start), min(n, start + len(clip))
        if b > a:
            track[a:b] += clip[a - start:b - start] * gain
    write_wav(out, track[: int(SR * duration)])
    return Path(out)


def write_wav(path: str | Path, stereo: np.ndarray) -> None:
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def mix(dialogue_src: str, duration: float, out: str | Path, *, music: dict | None = None,
        sfx_wav: str | Path | None = None, music_db: float = -16.0, duck_db: float = 12.0,
        has_dialogue: bool = True, music_fade_out: float = 2.5, target_lufs: float = -14.0) -> Path:
    """Dialogue (audio of the joined edit) + ducked music + SFX -> two-pass loudness-normalized WAV."""
    out = Path(out)
    raw = out.with_name(out.stem + "_raw.wav")
    inputs = ["-i", str(dialogue_src)]
    graph = [f"[0:a]aformat=sample_rates={SR}:channel_layouts=stereo,atrim=0:{duration:.3f},asetpts=N/SR/TB[dlg]"]
    mix_in = ["[dlgm]"]
    if music and music.get("file"):
        inputs += ["-stream_loop", "-1", "-ss", f"{music.get('start', 0):.3f}", "-i", music["file"]]
        gain = music.get("gain_db", music_db)
        fade_in = music.get("fade_in", 0.8)
        graph.append(
            f"[1:a]aformat=sample_rates={SR}:channel_layouts=stereo,atrim=0:{duration:.3f},asetpts=N/SR/TB,"
            f"volume={gain}dB,afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, duration - music_fade_out):.3f}:d={music_fade_out}[mus]")
        if has_dialogue:
            ratio = max(2, min(20, 10 ** (duck_db / 20)))
            graph.append("[dlg]asplit=2[dlgm][dlgsc]")
            graph.append(f"[mus][dlgsc]sidechaincompress=threshold=0.015:ratio={ratio:.1f}:attack=15:release=450:makeup=1[musd]")
            mix_in.append("[musd]")
        else:
            graph.append("[dlg]anull[dlgm]")
            mix_in.append("[mus]")
    else:
        graph.append("[dlg]anull[dlgm]")
    if sfx_wav:
        idx = len([x for x in inputs if x == "-i"])
        inputs += ["-i", str(sfx_wav)]
        graph.append(f"[{idx}:a]aformat=sample_rates={SR}:channel_layouts=stereo,volume=-6dB[sfx]")
        mix_in.append("[sfx]")
    graph.append(f"{''.join(mix_in)}amix=inputs={len(mix_in)}:normalize=0:duration=first,alimiter=limit=0.95:level=false[mix]")
    ff.run([*inputs, "-filter_complex", ";".join(graph), "-map", "[mix]", "-t", f"{duration:.3f}", "-c:a", "pcm_s16le", str(raw)])
    loudnorm(raw, out, target_lufs)
    raw.unlink(missing_ok=True)
    return out


def loudnorm(src: str | Path, dst: str | Path, target: float = -14.0, tp: float = -1.0) -> dict:
    log = ff.run_log(["-i", str(src), "-af", f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", log, re.S)
    if not m:
        ff.run(["-i", str(src), "-af", f"loudnorm=I={target}:TP={tp}", "-ar", str(SR), str(dst)])
        return {}
    meas = json.loads(m.group(0))
    if float(meas.get("input_i", "-inf").replace("inf", "1e9")) < -60:  # silence: nothing to normalize
        ff.run(["-i", str(src), "-c:a", "pcm_s16le", str(dst)])
        return meas
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
          f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true,"
          # loudnorm cannot always hold the ceiling in linear mode, and AAC adds overshoot: a final brickwall.
          f"aresample={SR * 4},alimiter=limit={10 ** ((tp - 1.5) / 20):.4f}:attack=1:release=60:level=false,aresample={SR}")
    ff.run(["-i", str(src), "-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)])
    return meas


def measure(path: str | Path) -> dict:
    log = ff.run_log(["-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)
    return {"integrated_lufs": float(i[-1]) if i else None, "true_peak_dbfs": float(p[-1]) if p else None}
