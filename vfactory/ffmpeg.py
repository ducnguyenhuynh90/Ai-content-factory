"""Thin wrappers around ffmpeg / ffprobe."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
VERBOSE = False


class FFmpegError(RuntimeError):
    pass


def run(args: list[str], *, capture: bool = False, input: bytes | None = None) -> subprocess.CompletedProcess:
    cmd = [FFMPEG, "-hide_banner", "-y", "-loglevel", "error" if not capture else "info", *args]
    if VERBOSE:
        print("$", shlex.join(cmd))
    proc = subprocess.run(cmd, input=input, capture_output=True) if input is not None else subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        tail = proc.stderr.decode(errors="replace")[-3000:]
        raise FFmpegError(f"ffmpeg failed ({proc.returncode}):\n{shlex.join(cmd)[:2000]}\n---\n{tail}")
    return proc


def run_log(args: list[str]) -> str:
    """Run ffmpeg for its analysis output (stderr) and return the log text."""
    cmd = [FFMPEG, "-hide_banner", "-nostats", *args]
    if VERBOSE:
        print("$", shlex.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr.decode(errors="replace")[-3000:])
    return proc.stderr.decode(errors="replace")


@dataclass
class MediaInfo:
    path: str
    duration: float
    width: int = 0
    height: int = 0
    fps: float = 0.0
    has_video: bool = False
    has_audio: bool = False
    rotation: int = 0

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 0.0


def probe(path: str | Path) -> MediaInfo:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    if out.returncode != 0:
        raise FFmpegError(f"ffprobe failed on {path}: {out.stderr.decode(errors='replace')}")
    data = json.loads(out.stdout)
    info = MediaInfo(path=str(path), duration=float(data.get("format", {}).get("duration") or 0.0))
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and not info.has_video and s.get("disposition", {}).get("attached_pic", 0) == 0:
            info.has_video = True
            info.width, info.height = int(s.get("width", 0)), int(s.get("height", 0))
            num, _, den = (s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1").partition("/")
            try:
                info.fps = float(num) / float(den or 1)
            except ZeroDivisionError:
                info.fps = 0.0
            rot = s.get("tags", {}).get("rotate")
            for sd in s.get("side_data_list", []) or []:
                if "rotation" in sd:
                    rot = sd["rotation"]
            info.rotation = int(float(rot or 0)) % 360
            if info.rotation in (90, 270):
                info.width, info.height = info.height, info.width
        elif s.get("codec_type") == "audio":
            info.has_audio = True
    return info


def read_audio_mono(path: str | Path, sr: int = 16000, start: float = 0.0, duration: float | None = None):
    """Decode audio to a float32 mono numpy array."""
    import numpy as np

    args = [FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}"]
    if duration:
        args += ["-t", f"{duration:.3f}"]
    args += ["-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    proc = subprocess.run(args, capture_output=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        return np.zeros(0, dtype="float32")
    return np.frombuffer(proc.stdout, dtype="<f4").copy()


def extract_frame(path: str | Path, t: float, out: str | Path, width: int | None = None) -> Path:
    vf = ["-vf", f"scale={width}:-2"] if width else []
    run(["-ss", f"{max(t, 0):.3f}", "-i", str(path), "-frames:v", "1", *vf, str(out)])
    return Path(out)
