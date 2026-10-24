"""Footage + music analysis. Produces the facts the director reasons from:
speech vs silence, shot boundaries, per-second picture quality/motion, loudness
peaks, and the music beat grid. Text and numbers — never frame dumps."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import ffmpeg as ff

ANALYSIS_FPS = 4  # samples/sec for picture statistics


@dataclass
class Shot:
    start: float
    end: float
    motion: float = 0.0
    sharpness: float = 0.0
    contrast: float = 0.0
    brightness: float = 0.0
    score: float = 0.0
    peak: float = 0.0  # time of highest interest inside the shot

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class SourceAnalysis:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool
    kind: str = "broll"                     # talk | broll
    speech_ratio: float = 0.0
    silences: list[tuple[float, float]] = field(default_factory=list)
    speech: list[tuple[float, float]] = field(default_factory=list)
    shots: list[Shot] = field(default_factory=list)
    energy: list[float] = field(default_factory=list)   # audio RMS per 0.25s
    interest: list[float] = field(default_factory=list)  # picture interest per 1/ANALYSIS_FPS s

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class MusicAnalysis:
    path: str
    duration: float
    bpm: float
    beats: list[float]
    downbeats: list[float]
    drop: float | None  # biggest energy rise — where the edit should "open up"
    energy: list[float]  # RMS per 0.5s


# ---------------------------------------------------------------- audio

def detect_silences(path: str, noise_db: float = -35.0, min_dur: float = 0.35) -> list[tuple[float, float]]:
    log = ff.run_log(["-i", path, "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else None
        out.append((max(0.0, s), e if e is not None else float("inf")))
    return out


def complement(ranges: list[tuple[float, float]], duration: float, min_len: float = 0.15) -> list[tuple[float, float]]:
    out, cur = [], 0.0
    for s, e in sorted(ranges):
        if s - cur >= min_len:
            out.append((round(cur, 3), round(s, 3)))
        cur = max(cur, min(e, duration))
    if duration - cur >= min_len:
        out.append((round(cur, 3), round(duration, 3)))
    return out


def rms_envelope(samples: np.ndarray, sr: int, hop_s: float) -> np.ndarray:
    hop = max(1, int(sr * hop_s))
    n = len(samples) // hop
    if n == 0:
        return np.zeros(0)
    frames = samples[: n * hop].reshape(n, hop)
    return np.sqrt((frames ** 2).mean(axis=1) + 1e-12)


# ---------------------------------------------------------------- picture

def picture_stats(path: str, duration: float) -> dict[str, np.ndarray]:
    """Decode a 96x54 grey proxy at ANALYSIS_FPS and compute per-sample statistics."""
    w, h = 96, 54
    import subprocess

    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf",
                           f"fps={ANALYSIS_FPS},scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"],
                          capture_output=True, stdin=subprocess.DEVNULL)
    buf = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = len(buf) // (w * h)
    if n == 0:
        z = np.zeros(1)
        return {"brightness": z, "contrast": z, "motion": z, "sharpness": z}
    fr = buf[: n * w * h].reshape(n, h, w).astype("float32") / 255.0
    brightness = fr.mean(axis=(1, 2))
    contrast = fr.std(axis=(1, 2))
    motion = np.concatenate([[0.0], np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))])
    lap = np.abs(4 * fr[:, 1:-1, 1:-1] - fr[:, :-2, 1:-1] - fr[:, 2:, 1:-1] - fr[:, 1:-1, :-2] - fr[:, 1:-1, 2:])
    sharpness = lap.mean(axis=(1, 2))
    return {"brightness": brightness, "contrast": contrast, "motion": motion, "sharpness": sharpness}


def detect_scenes(path: str, threshold: float = 0.32) -> list[float]:
    log = ff.run_log(["-i", path, "-an", "-vf", f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", log)]


def _norm(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    lo, hi = np.percentile(x, 5), np.percentile(x, 95)
    return np.clip((x - lo) / (hi - lo + 1e-6), 0, 1)


def interest_curve(stats: dict[str, np.ndarray]) -> np.ndarray:
    """Per-sample 'how good is this moment' — motion with intent, sharp, exposed, not black."""
    b = stats["brightness"]
    exposure = 1 - np.clip(np.abs(b - 0.45) / 0.45, 0, 1)
    motion = _norm(stats["motion"])
    # Too much motion (whip pans, shake) is less useful than purposeful motion.
    motion = np.where(motion > 0.92, 0.7, motion)
    score = 0.4 * motion + 0.3 * _norm(stats["sharpness"]) + 0.15 * _norm(stats["contrast"]) + 0.15 * exposure
    # Near-black frames are never interesting; dim ones are rarely the best choice.
    score = score * np.clip((b - 0.04) / 0.08, 0.0, 1.0)
    k = np.ones(3) / 3
    return np.convolve(score, k, mode="same") if score.size >= 3 else score


def shots_from(cuts: list[float], duration: float, stats: dict[str, np.ndarray], interest: np.ndarray) -> list[Shot]:
    bounds = [0.0, *[c for c in cuts if 0.3 < c < duration - 0.3], duration]
    shots = []
    for s, e in zip(bounds, bounds[1:]):
        if e - s < 0.5:
            continue
        i0, i1 = int(s * ANALYSIS_FPS), max(int(s * ANALYSIS_FPS) + 1, int(e * ANALYSIS_FPS))
        sl = slice(i0, min(i1, interest.size))
        seg = interest[sl]
        if seg.size == 0:
            continue
        peak = s + (int(np.argmax(seg)) + 0.5) / ANALYSIS_FPS
        shots.append(Shot(
            start=round(s, 3), end=round(e, 3),
            motion=float(stats["motion"][sl].mean()), sharpness=float(stats["sharpness"][sl].mean()),
            contrast=float(stats["contrast"][sl].mean()), brightness=float(stats["brightness"][sl].mean()),
            score=float(np.percentile(seg, 75)), peak=round(min(peak, e), 3),
        ))
    return shots


# ---------------------------------------------------------------- sources

def analyze_source(path: str) -> SourceAnalysis:
    info = ff.probe(path)
    sa = SourceAnalysis(path=str(path), duration=info.duration, width=info.width, height=info.height,
                        fps=info.fps, has_audio=info.has_audio)
    if info.has_audio:
        sa.silences = detect_silences(path)
        sa.speech = complement(sa.silences, info.duration)
        voiced = sum(e - s for s, e in sa.speech)
        sa.speech_ratio = voiced / info.duration if info.duration else 0.0
        audio = ff.read_audio_mono(path, sr=16000)
        env = rms_envelope(audio, 16000, 0.25)
        sa.energy = [round(float(x), 5) for x in env]
        # Speech has syllabic modulation; ambient beds and music are steadier. A crude but useful test.
        if env.size > 8:
            mod = float(np.std(np.diff(20 * np.log10(env + 1e-6))))
            dynamic = float(np.percentile(env, 90) / (np.percentile(env, 20) + 1e-6))
            if sa.speech_ratio > 0.45 and len(sa.silences) >= 2 and mod > 2.0 and dynamic > 3.0:
                sa.kind = "talk"
    if info.has_video:
        stats = picture_stats(path, info.duration)
        interest = interest_curve(stats)
        sa.interest = [round(float(x), 4) for x in interest]
        sa.shots = shots_from(detect_scenes(path), info.duration, stats, interest)
    return sa


# ---------------------------------------------------------------- music

def analyze_music(path: str) -> MusicAnalysis:
    sr = 22050
    y = ff.read_audio_mono(path, sr=sr)
    dur = len(y) / sr
    hop, win = 512, 2048
    if len(y) < win * 4:
        return MusicAnalysis(path, dur, 0.0, [], [], None, [])
    n = 1 + (len(y) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    frames = y[idx] * np.hanning(win)[None, :]
    mag = np.abs(np.fft.rfft(frames, axis=1))
    logmag = np.log1p(10 * mag)
    flux = np.maximum(0, np.diff(logmag, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux = flux - np.convolve(flux, np.ones(16) / 16, mode="same")
    flux = np.maximum(flux, 0)
    fps = sr / hop
    # tempo via autocorrelation over 60..180 bpm
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    lags = np.arange(len(ac))
    bpm_lags = (lags > fps * 60 / 180) & (lags < fps * 60 / 60)
    weights = np.exp(-0.5 * (np.log2((60 * fps / np.maximum(lags, 1)) / 120)) ** 2 / 0.9 ** 2)  # prefer ~120bpm
    cand = np.where(bpm_lags, ac * weights, 0)
    lag = int(np.argmax(cand)) if cand.any() else int(fps / 2)
    period = lag / fps
    bpm = 60 / period if period > 0 else 0
    # phase: offset maximizing onset energy on the grid
    best_off, best_val = 0.0, -1.0
    for off in np.linspace(0, period, 32, endpoint=False):
        ts = np.arange(off, dur, period)
        val = flux[np.clip((ts * fps).astype(int), 0, len(flux) - 1)].sum()
        if val > best_val:
            best_off, best_val = off, val
    beats = [round(float(t), 3) for t in np.arange(best_off, dur, period)]
    # downbeat phase: which of 4 offsets has the most energy
    if len(beats) >= 8:
        strengths = [flux[np.clip((np.array(beats[k::4]) * fps).astype(int), 0, len(flux) - 1)].sum() for k in range(4)]
        k = int(np.argmax(strengths))
        downbeats = beats[k::4]
    else:
        downbeats = beats[::4]
    env = rms_envelope(y, sr, 0.5)
    drop = None
    if env.size > 8:
        sm = np.convolve(env, np.ones(4) / 4, mode="same")
        rise = sm[4:] - sm[:-4]
        i = int(np.argmax(rise))
        if rise[i] > 0.15 * sm.max():
            t = (i + 4) * 0.5
            drop = min(downbeats, key=lambda d: abs(d - t)) if downbeats else t
    return MusicAnalysis(path=str(path), duration=round(dur, 3), bpm=round(bpm, 2), beats=beats,
                         downbeats=[round(d, 3) for d in downbeats], drop=drop, energy=[round(float(x), 4) for x in env])


def analyze_all(sources: dict[str, str], music: str | None = None) -> dict:
    out = {"sources": {}, "music": None}
    for key, path in sources.items():
        out["sources"][key] = analyze_source(path).to_dict()
    if music:
        out["music"] = asdict(analyze_music(music))
    return out


def summarize(analysis: dict) -> str:
    """Compact text view of the analysis — what an LLM director reads."""
    lines = []
    for key, s in analysis["sources"].items():
        lines.append(f"## {key}  {Path(s['path']).name}  {s['duration']:.1f}s {s['width']}x{s['height']} "
                     f"kind={s['kind']} speech={s['speech_ratio']:.0%}")
        for i, sh in enumerate(s["shots"][:40]):
            lines.append(f"  shot{i:02d} [{sh['start']:.2f}-{sh['end']:.2f}] score={sh['score']:.2f} "
                         f"motion={sh['motion']:.3f} bright={sh['brightness']:.2f} peak@{sh['peak']:.2f}")
        if s["kind"] == "talk":
            for a, b in s["speech"][:60]:
                lines.append(f"  speech [{a:.2f}-{b:.2f}]")
    m = analysis.get("music")
    if m:
        lines.append(f"## music {Path(m['path']).name} {m['duration']:.1f}s bpm={m['bpm']} drop={m['drop']} "
                     f"downbeats={len(m['downbeats'])}")
    return "\n".join(lines)


def save(analysis: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(analysis, indent=1))
