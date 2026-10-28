"""Measured, conservative correction of picture and sound.

Picture: exposure, contrast, white balance, noise, softness are measured on a proxy and
corrected only past thresholds, with caps so skin keeps its texture. Badly broken footage is
reported with a reshoot recommendation instead of being "fixed" into artifacts.

Sound: every voice is treated on its own (high-pass, gentle denoise when the floor is high,
light compression, de-click on clipping) and normalized on its own, so the person's real
voice never gets quieter because another source is louder. Music only ever ducks.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

import numpy as np

from .. import audio as A
from .. import ffmpeg as ff


@dataclass
class PictureReport:
    luma: float
    p05: float
    p95: float
    rgb: tuple[float, float, float]
    noise: float
    softness: float
    verdict: str = "ok"
    corrections: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    filter: str = ""


def measure_picture(path: str, duration: float, samples: int = 24) -> dict:
    w, h = 320, 180
    fps = max(0.2, min(4.0, samples / max(duration, 1)))
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps:.3f},scale={w}:{h}:flags=area,format=rgb24",
                           "-f", "rawvideo", "-"], capture_output=True, stdin=subprocess.DEVNULL)
    buf = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = len(buf) // (w * h * 3)
    fr = buf[: n * w * h * 3].reshape(n, h, w, 3).astype("float32") / 255.0
    y = 0.2126 * fr[..., 0] + 0.7152 * fr[..., 1] + 0.0722 * fr[..., 2]
    mid = (y > 0.2) & (y < 0.8)
    rgb = tuple(float(fr[..., c][mid].mean()) if mid.any() else float(fr[..., c].mean()) for c in range(3))
    # noise: high-pass energy in flat regions; softness: low gradient energy overall
    hp = np.abs(y[:, 1:-1, 1:-1] * 4 - y[:, :-2, 1:-1] - y[:, 2:, 1:-1] - y[:, 1:-1, :-2] - y[:, 1:-1, 2:])
    gx = np.abs(np.diff(y, axis=2))[:, 1:-1, :-1]
    flat = gx < 0.02
    noise = float(hp[flat].mean()) if flat.any() else float(hp.mean())
    softness = float(1.0 / (gx.mean() * 40 + 1e-3))
    return {"luma": float(y.mean()), "p05": float(np.percentile(y, 5)), "p95": float(np.percentile(y, 95)),
            "rgb": rgb, "noise": noise, "softness": softness}


def picture_correction(m: dict) -> PictureReport:
    r = PictureReport(round(m["luma"], 3), round(m["p05"], 3), round(m["p95"], 3), tuple(round(c, 3) for c in m["rgb"]),
                      round(m["noise"], 4), round(m["softness"], 3))
    poor = r.luma < 0.12 or r.noise > 0.09
    f = []
    # 1. Noise first: every later gain would amplify it.
    if r.noise > 0.035:
        s = min(4.0, 1.5 + (r.noise - 0.035) * 60)
        f.append(f"hqdn3d=luma_spatial={s:.1f}:chroma_spatial={s * 1.5:.1f}:luma_tmp={s * 1.5:.1f}:chroma_tmp={s * 2:.1f}")
        r.corrections.append(f"noisy/grainy (index {r.noise:.3f}): temporal denoise {s:.1f}")
    # 2. Exposure: lift midtones toward ~0.42 with gamma, capped (gentler on poor footage).
    gmax = 1.35 if poor else 1.7
    if r.luma < 0.33:
        gamma = min(gmax, max(1.05, np.log(0.42) / np.log(max(r.luma, 0.05))))
        f.append(f"eq=gamma={gamma:.2f}")
        r.corrections.append(f"underexposed (mean luma {r.luma:.2f}): gamma {gamma:.2f}")
    elif r.luma > 0.72:
        gamma = max(0.7, min(0.95, np.log(0.6) / np.log(r.luma)))
        f.append(f"eq=gamma={gamma:.2f}")
        r.corrections.append(f"overexposed (mean luma {r.luma:.2f}): gamma {gamma:.2f}")
    # 3. Contrast: stretch a flat image, but never more than 1.5x (1.2x on poor footage): beyond that it's noise.
    span = r.p95 - r.p05
    if span < 0.55:
        gain = min(1.2 if poor else 1.5, 0.75 / max(span, 0.05))
        mid = (r.p05 + r.p95) / 2
        lo, hi = mid - span / 2, mid + span / 2
        olo, ohi = max(0.0, mid - span * gain / 2), min(1.0, mid + span * gain / 2)
        f.append(f"curves=all='0/0 {lo:.3f}/{olo:.3f} {hi:.3f}/{ohi:.3f} 1/1'")
        r.corrections.append(f"flat contrast (5-95% span {span:.2f}): gentle stretch x{gain:.2f}")
    # 4. White balance: gray-world on midtones, at most +-8% per channel, applied at half strength.
    rr, gg, bb = r.rgb
    if gg > 0.02:
        kr, kb = gg / max(rr, 1e-3), gg / max(bb, 1e-3)
        kr, kb = max(0.92, min(1.08, kr)), max(0.92, min(1.08, kb))
        if abs(kr - 1) > 0.025 or abs(kb - 1) > 0.025:
            kr, kb = 1 + (kr - 1) * 0.5, 1 + (kb - 1) * 0.5
            f.append(f"colorchannelmixer=rr={kr:.3f}:bb={kb:.3f}")
            r.corrections.append(f"colour cast (R/G {rr / gg:.2f}, B/G {bb / gg:.2f}): balance R x{kr:.3f}, B x{kb:.3f}")
    # 5. Sharpen only clean, soft footage.
    if r.noise <= 0.035 and r.softness > 1.6:
        f.append("unsharp=5:5:0.35:5:5:0.0")
        r.corrections.append("soft image: light luma sharpen")
    if poor:
        r.verdict = "poor"
        r.warnings.append("Footage is very dark/noisy; only mild correction was applied to avoid artifacts. A reshoot "
                          "with more light (face a window, or one soft key light) would look far better.")
    elif f:
        r.verdict = "corrected"
    r.filter = ",".join(f)
    return r


@dataclass
class AudioReport:
    lufs: float | None
    true_peak: float | None
    noise_floor_db: float | None
    clipped: bool
    chain: str
    notes: list[str]


def measure_audio(path: str, silences: list[tuple[float, float]]) -> AudioReport:
    m = A.measure(path)
    y = ff.read_audio_mono(path, sr=16000)
    floor = None
    if y.size and silences:
        parts = [y[int(a * 16000):int(min(b, a + 2) * 16000)] for a, b in silences[:20] if b - a > 0.3]
        parts = [p for p in parts if p.size]
        if parts:
            rms = np.sqrt(np.mean(np.concatenate(parts) ** 2) + 1e-12)
            floor = round(20 * np.log10(rms), 1)
    clipped = bool(y.size and (np.abs(y) > 0.995).mean() > 1e-4)
    notes, chain = [], ["highpass=f=75"]
    if clipped:
        chain.insert(0, "adeclip")
        notes.append("clipping detected: de-clip (the original recording is distorted; check mic gain next time)")
    if floor is not None and floor > -55:
        nr = 8 if floor < -45 else 12
        chain.append(f"afftdn=nr={nr}:nf={max(-80, floor - 3):.0f}:tn=1")
        notes.append(f"background noise at {floor} dBFS: gentle denoise ({nr} dB, capped so the voice stays natural)")
    chain.append("acompressor=threshold=-21dB:ratio=2.5:attack=8:release=160:makeup=1.5")
    notes.append("light compression (2.5:1) for even level")
    return AudioReport(m.get("integrated_lufs"), m.get("true_peak_dbfs"), floor, clipped, ",".join(chain), notes)


def mix_stems(stems: list[dict], duration: float, out: str, voice_lufs: float = -16.0, target_lufs: float = -14.0) -> str:
    """stems: [{"file", "role": voice|ai_voice|guest|music|sfx, "start": 0.0, "gain_db": 0}]. Each voice-like stem is
    normalized on its own; music sits ~16 dB under the voices and ducks under them; the sum is limited, never pumped."""
    import os
    import tempfile

    td = tempfile.mkdtemp(prefix="mix_")
    try:
        return _mix_stems(stems, duration, out, voice_lufs, target_lufs, td)
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)  # each mix leaves ~190 MB of stems behind otherwise


def _mix_stems(stems, duration, out, voice_lufs, target_lufs, td) -> str:
    import os

    voices, others = [], []
    for i, s in enumerate(stems):
        norm = os.path.join(td, f"s{i}.wav")
        if s["role"] in ("voice", "ai_voice", "guest"):
            A.loudnorm(s["file"], norm, voice_lufs, -2.0)
            voices.append((s, norm))
        else:
            ff.run(["-i", s["file"], "-ar", str(A.SR), "-ac", "2", norm])
            others.append((s, norm))
    args, graph, labels = [], [], []
    k = 0
    for s, f in voices + others:
        args += ["-i", f]
        delay = int(float(s.get("start", 0)) * 1000)
        g = float(s.get("gain_db", 0)) + (-16.0 if s["role"] == "music" else 0.0)  # score sits well under the voice
        graph.append(f"[{k}:a]aformat=sample_rates={A.SR}:channel_layouts=stereo,adelay={delay}|{delay},"
                     f"apad,atrim=0:{duration:.3f},volume={g}dB[a{k}]")
        labels.append((s["role"], f"a{k}"))
        k += 1
    vlabels = [l for r, l in labels if r in ("voice", "ai_voice", "guest")]
    mus = [l for r, l in labels if r == "music"]
    rest = [l for r, l in labels if r not in ("voice", "ai_voice", "guest", "music")]
    final = []
    if vlabels:
        graph.append(f"{''.join('[' + l + ']' for l in vlabels)}amix=inputs={len(vlabels)}:normalize=0[vox]")
        if mus:
            graph.append("[vox]asplit=2[voxm][voxsc]")
            graph.append(f"{''.join('[' + l + ']' for l in mus)}amix=inputs={len(mus)}:normalize=0[mus]")
            graph.append("[mus][voxsc]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[musd]")
            final += ["[voxm]", "[musd]"]
        else:
            final.append("[vox]")
    else:
        final += [f"[{l}]" for l in mus]
    final += [f"[{l}]" for l in rest]
    graph.append(f"{''.join(final)}amix=inputs={len(final)}:normalize=0,alimiter=limit=0.89:level=false[mix]")
    raw = os.path.join(td, "mix_raw.wav")
    ff.run([*args, "-filter_complex", ";".join(graph), "-map", "[mix]", "-c:a", "pcm_s16le", raw])
    A.loudnorm(raw, out, target_lufs, -1.0)
    return out
