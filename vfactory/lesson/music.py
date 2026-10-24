"""An original, royalty-free documentary bed: slow minor-key pads, a soft low pulse and sparse
plucked notes. Synthesized, so there is nothing to license; mixed ~18 dB under the narration.
The "chill" mood is a lo-fi bed instead: major-seventh chords, a lazy soft kick and brushed hat, vinyl hiss."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .. import audio

PROGRESSIONS = {
    # i - VI - III - VII in A minor: reflective, slightly hopeful
    "reflective": [(220.00, 261.63, 329.63), (174.61, 220.00, 261.63), (261.63, 329.63, 392.00), (196.00, 246.94, 293.66)],
    # i - iv - i - V in D minor: tension for crashes and manias
    "tension": [(146.83, 174.61, 220.00), (196.00, 233.08, 293.66), (146.83, 174.61, 220.00), (220.00, 277.18, 329.63)],
    # Fmaj7 - Em7 - Dm7 - Cmaj7: warm, unhurried (lo-fi / study-beats colour)
    "chill": [(174.61, 220.00, 261.63, 329.63), (164.81, 196.00, 246.94, 293.66), (146.83, 174.61, 220.00, 261.63),
              (130.81, 164.81, 196.00, 246.94)],
}


def lofi_drums(n: int, sr: int, bpm: float, rng) -> np.ndarray:
    """Soft kick on 1 and the 'and' of 3, brushed hat on the off-beats, a whisper of vinyl hiss. Kept low: it is a
    pulse to sit back on, not a beat to dance to."""
    y = np.zeros(n, dtype="float32")
    beat = 60.0 / bpm
    kl, hl = int(sr * 0.35), int(sr * 0.09)
    tk, th = np.arange(kl) / sr, np.arange(hl) / sr
    kick = np.sin(2 * np.pi * (48 * tk + 40 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 9)
    noise = rng.normal(0, 1, hl)
    hat = np.diff(noise, prepend=0) * np.exp(-th * 55)
    b = 0
    while (s := int(b * beat * sr)) < n:
        swing = 0.06 * beat if b % 2 else 0.0  # lazy, behind-the-beat feel
        if b % 4 == 0:
            y[s:s + kl] += kick[: n - s] * 0.10
        if b % 4 == 2:
            s2 = s + int(0.5 * beat * sr)
            y[s2:s2 + kl] += kick[: max(0, n - s2)] * 0.07
        hs = s + int((0.5 * beat + swing) * sr)
        y[hs:hs + hl] += hat[: max(0, n - hs)] * (0.018 + 0.006 * rng.random())
        b += 1
    hiss = np.diff(rng.normal(0, 1, n + 1)).astype("float32") * 0.0015
    crackle = (rng.random(n) < 2.5 / sr) * rng.uniform(0.02, 0.06, n)
    return y + hiss + crackle.astype("float32")


def bed(duration: float, out: str | Path, mood: str = "reflective", bpm: float = 72.0, seed: int = 3,
        fade_in: float = 2.0) -> Path:
    sr = audio.SR
    n = int(sr * (duration + 1.0))
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    bar = 4 * 60.0 / bpm * 2  # two bars per chord: slow harmonic rhythm
    chords = PROGRESSIONS.get(mood, PROGRESSIONS["reflective"])
    pad = np.zeros(n, dtype="float32")
    pluck = np.zeros(n, dtype="float32")
    low = np.zeros(n, dtype="float32")
    k = 0
    start = 0.0
    while start < duration + 1.0:
        s, e = int(start * sr), min(n, int((start + bar) * sr))
        tt = t[s:e] - start
        env = np.minimum(1, tt / 1.8) * np.minimum(1, (bar - tt) / 1.8)
        chord = chords[k % len(chords)]
        for f in chord:
            detune = 1.0 + rng.uniform(-0.0015, 0.0015)
            pad[s:e] += (np.sin(2 * np.pi * f * detune * tt) + 0.35 * np.sin(2 * np.pi * f * 2 * tt + 0.3)) * env * 0.05
        root = chord[0] / 2
        low[s:e] += np.sin(2 * np.pi * root * tt) * env * 0.06
        beat = 60.0 / bpm
        for j in range(int(bar / beat)):
            if rng.random() < 0.45:
                ps = s + int(j * beat * sr)
                note = chord[rng.integers(0, 3)] * (2 if rng.random() < 0.6 else 4)
                ln = int(sr * 1.6)
                pe = min(n, ps + ln)
                tp = np.arange(pe - ps) / sr
                pluck[ps:pe] += np.sin(2 * np.pi * note * tp) * np.exp(-tp * 3.2) * 0.035
        start += bar
        k += 1
    y = pad + pluck + low
    if mood == "chill":
        y = y + lofi_drums(n, sr, bpm, rng)
    # gentle stereo: delay one side a few ms and add a tiny room
    d = int(0.012 * sr)
    left = y
    right = np.concatenate([np.zeros(d, dtype="float32"), y[:-d]]) * 0.95 + y * 0.05
    st = np.stack([left, right], axis=1)
    fade_in, fade_out = max(1, int(fade_in * sr)), int(3.0 * sr)  # a hook needs music from frame 0
    st[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    st[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    st = st[: int(sr * duration)]
    st = st / (np.abs(st).max() + 1e-9) * 0.7
    audio.write_wav(out, st)
    return Path(out)
