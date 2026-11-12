"""Original, royalty-free beds for shorts: faster than the documentary bed, with a soft pulse so the edit feels
driven. Synthesized, so there is nothing to license (Content ID / TikTok copyright never fires on it).

On TikTok a trending sound added in the app can lift reach: every build also writes a *_nomusic.mp4 (voice + effects
only) so the person can lay a trending sound under it at 5-10 % volume in the TikTok editor."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .. import audio

MOODS = {
    # (chords, bpm, kick, hats)
    "tense": ([(146.83, 174.61, 220.00), (196.00, 233.08, 293.66), (146.83, 174.61, 220.00), (220.00, 277.18, 329.63)], 96, True, True),
    "curious": ([(220.00, 261.63, 329.63), (174.61, 220.00, 261.63), (261.63, 329.63, 392.00), (196.00, 246.94, 293.66)], 100, False, True),
    "upbeat": ([(261.63, 329.63, 392.00), (196.00, 246.94, 293.66), (220.00, 261.63, 329.63), (174.61, 220.00, 261.63)], 112, True, True),
    "calm": ([(220.00, 261.63, 329.63), (174.61, 220.00, 261.63), (261.63, 329.63, 392.00), (196.00, 246.94, 293.66)], 76, False, False),
}


def bed(duration: float, out: str | Path, mood: str = "curious", seed: int = 5) -> Path:
    chords, bpm, kick, hats = MOODS.get(mood, MOODS["curious"])
    sr = audio.SR
    n = int(sr * (duration + 1.0))
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    y = np.zeros(n, dtype="float32")
    k, start = 0, 0.0
    while start < duration + 1.0:
        s, e = int(start * sr), min(n, int((start + bar) * sr))
        tt = np.arange(e - s) / sr
        env = np.minimum(1, tt / 0.25) * np.minimum(1, (bar - tt) / 0.4)
        chord = chords[k % len(chords)]
        for f in chord:
            y[s:e] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt + 0.4)) * env * 0.045
        y[s:e] += np.sin(2 * np.pi * chord[0] / 2 * tt) * env * 0.05
        for j in range(8):  # eighth-note arpeggio: the "explainer" pulse
            ps = s + int(j * beat / 2 * sr)
            if ps >= n or rng.random() < 0.25:
                continue
            note = chord[j % 3] * (2 if j % 4 else 4)
            ln = min(n - ps, int(sr * 0.5))
            tp = np.arange(ln) / sr
            y[ps:ps + ln] += np.sin(2 * np.pi * note * tp) * np.exp(-tp * 9) * 0.03
        for j in range(4):
            ps = s + int(j * beat * sr)
            if ps >= n:
                break
            if kick:
                ln = min(n - ps, int(sr * 0.25))
                tp = np.arange(ln) / sr
                f = 55 + 70 * np.exp(-tp * 30)
                y[ps:ps + ln] += np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tp * 14) * 0.16
            if hats:
                hs = ps + int(beat / 2 * sr)
                ln = min(n - hs, int(sr * 0.05))
                if ln > 0:
                    hn = rng.standard_normal(ln).astype("float32")
                    hn = hn - np.convolve(hn, np.ones(4) / 4, mode="same")
                    y[hs:hs + ln] += hn * np.exp(-np.arange(ln) / sr * 80) * 0.025
        start += bar
        k += 1
    d = int(0.011 * sr)
    right = np.concatenate([np.zeros(d, dtype="float32"), y[:-d]]) * 0.9 + y * 0.1
    st = np.stack([y, right], axis=1)
    fo = int(1.5 * sr)
    st[-fo:] *= np.linspace(1, 0, fo)[:, None]
    st = st[: int(sr * duration)]
    st = st / (np.abs(st).max() + 1e-9) * 0.7
    audio.write_wav(out, st)
    return Path(out)
