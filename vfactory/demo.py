"""Generate synthetic demo material so the whole factory can be exercised with
no footage at hand: four b-roll clips with internal scene changes, a talking
clip voiced by flite (with exact word timings for captions), and a music bed."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import audio, ffmpeg as ff

BROLL = [
    # (name, lavfi graph, seconds) — each clip changes scene midway so shot detection has work to do
    ("aurora", "gradients=s=320x180:r=30:c0=0x0b1d3a:c1=0x2bd1a0:c2=0x7a2bd1:c3=0x050a14:n=4:speed=0.02,"
               "gblur=sigma=3,scale=1280:720:flags=bicubic", 9),
    ("fractal", "mandelbrot=s=480x270:r=30:maxiter=200:start_scale=3:end_scale=0.4:end_pts=20:inner=period,"
                "scale=1280:720:flags=bicubic", 8),
    ("dunes", "gradients=s=320x180:r=30:c0=0xe0a060:c1=0x7a3b1c:c2=0xf3d3a3:n=3:speed=0.015:type=radial,"
              "gblur=sigma=3,scale=1280:720:flags=bicubic", 8),
    ("city", "life=s=320x180:r=30:mold=10:ratio=0.18:death_color=#14121f:life_color=#ffb347:mold_color=#3b2b6b,"
             "scale=1280:720:flags=neighbor,gblur=sigma=1.2", 8),
]

LINES = [
    "Every film starts with a question.",
    "Ours was simple.",
    "What does the road remember, after everyone has gone home?",
    "We drove for nine days to find out.",
]


def make_broll(out_dir: Path) -> list[Path]:
    paths = []
    for name, graph, secs in BROLL:
        p = out_dir / f"broll_{name}.mp4"
        if not p.exists():
            # Second half is a different framing of the same source (hflip + crop) => a scene cut.
            half = secs / 2
            ff.run(["-f", "lavfi", "-t", str(secs), "-i", graph, "-f", "lavfi", "-t", str(secs), "-i",
                    "anoisesrc=r=48000:c=brown:a=0.02",
                    "-filter_complex",
                    f"[0:v]split[a][b];[a]trim=0:{half},setpts=PTS-STARTPTS[a1];"
                    f"[b]trim={half}:{secs},setpts=PTS-STARTPTS,hflip,crop=iw*0.6:ih*0.6,scale=1280:720,eq=saturation=1.3[b1];"
                    f"[a1][b1]concat=n=2:v=1:a=0,format=yuv420p[v]",
                    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-shortest", str(p)])
        paths.append(p)
    return paths


def make_talk(out_dir: Path) -> tuple[Path, Path]:
    """A 'talking head' clip: flite voice, one word at a time so we know every word's timing."""
    p, words_path = out_dir / "talk_narrator.mp4", out_dir / "talk_narrator.words.json"
    if p.exists() and words_path.exists():
        return p, words_path
    sr = audio.SR
    chunks, words, t = [np.zeros(int(sr * 0.8), dtype="float32")], [], 0.8
    for li, line in enumerate(LINES):
        for w in line.split():
            y = _trim_silence(_flite(w, sr))
            words.append({"word": w, "start": round(t, 3), "end": round(t + len(y) / sr, 3)})
            chunks.append(y)
            gap = 0.07
            chunks.append(np.zeros(int(sr * gap), dtype="float32"))
            t += len(y) / sr + gap
        pause = 1.1 if li % 2 == 0 else 1.6  # long pauses: the silence cutter should remove most of these
        chunks.append(np.zeros(int(sr * pause), dtype="float32"))
        t += pause
    y = np.concatenate(chunks)
    wav = out_dir / "_talk.wav"
    audio.write_wav(wav, np.stack([y, y], axis=1) * 0.9)
    dur = len(y) / sr
    ff.run(["-f", "lavfi", "-t", f"{dur:.3f}", "-i",
            "gradients=s=320x180:r=30:c0=0x2a1f1a:c1=0x6b4a33:c2=0x1a1410:n=3:speed=0.004,gblur=sigma=3,scale=1280:720,"
            "drawbox=x=iw*0.38:y=ih*0.28:w=iw*0.24:h=ih*0.72:color=0x0f0b09@0.85:t=fill,"
            "drawbox=x=iw*0.44:y=ih*0.12:w=iw*0.12:h=ih*0.2:color=0x0f0b09@0.85:t=fill",
            "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(p)])
    wav.unlink(missing_ok=True)
    words_path.write_text(json.dumps({"talk": words}, indent=1))
    return p, words_path


def _flite(word: str, sr: int) -> np.ndarray:
    import subprocess

    text = word.strip(".,?!").replace("'", "")
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"flite=text={text}:voice=slt",
                           "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, stdin=subprocess.DEVNULL)
    return np.frombuffer(proc.stdout, dtype="<f4").copy()


def _trim_silence(y: np.ndarray, th: float = 0.01) -> np.ndarray:
    idx = np.where(np.abs(y) > th)[0]
    return y[max(0, idx[0] - 200): idx[-1] + 400] if idx.size else y


def make_music(out_dir: Path, bpm: float = 96.0, bars: int = 24) -> Path:
    """A simple cinematic pulse: kick on every beat, hats on offbeats, a minor pad, a lift at bar 9."""
    p = out_dir / "music_pulse.wav"
    if p.exists():
        return p
    sr = audio.SR
    beat = 60 / bpm
    n = int(sr * beat * 4 * bars)
    y = np.zeros(n, dtype="float32")
    t_k = np.arange(int(sr * 0.35)) / sr
    kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-t_k * 30)) * t_k) * np.exp(-t_k * 9)
    rng = np.random.default_rng(0)
    hat = rng.standard_normal(int(sr * 0.05)).astype("float32") * np.exp(-np.arange(int(sr * 0.05)) / sr * 120) * 0.25
    hat = hat - np.convolve(hat, np.ones(8) / 8, mode="same")
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66), (164.81, 207.65, 246.94)]
    for b in range(bars * 4):
        s = int(b * beat * sr)
        bar = b // 4
        lift = bar >= 8
        if bar >= 2 or b % 2 == 0:
            e = min(n, s + len(kick))
            y[s:e] += kick[: e - s] * (0.9 if lift else 0.6)
        if lift or bar >= 4:
            h = s + int(beat * sr / 2)
            e = min(n, h + len(hat))
            y[h:e] += hat[: e - h]
    t = np.arange(n) / sr
    pad = np.zeros(n, dtype="float32")
    for bar in range(bars):
        s, e = int(bar * 4 * beat * sr), int((bar + 1) * 4 * beat * sr)
        tt = t[s:e]
        env = np.minimum(1, (tt - tt[0]) / 0.4) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.6)
        for f in chords[bar % 4]:
            pad[s:e] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt)) * env * 0.08
    pad = np.convolve(pad, np.ones(24) / 24, mode="same")
    y = y + pad * 1.6
    y[int(8 * 4 * beat * sr):] *= 1.25
    stereo = np.stack([y, np.roll(y, int(0.004 * sr))], axis=1)
    audio.write_wav(p, stereo / (np.abs(stereo).max() + 1e-9) * 0.8)
    return p


def make_all(out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    broll = make_broll(out)
    talk, words = make_talk(out)
    music = make_music(out)
    return {"broll": [str(p) for p in broll], "talk": str(talk), "words": str(words), "music": str(music)}
