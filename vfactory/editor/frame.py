"""Face tracking and reframing (e.g. 16:9 recording -> 9:16 reel) without distortion.

Local only: OpenCV's bundled Haar detectors (no model download). The crop is static per
segment, centred on the speaker's median face position — pro reframes don't wobble — with
the face kept in the upper third where captions won't cover it. Never stretches; never
upscales beyond what the platform needs (we warn instead).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np

PLATFORMS = {
    "instagram": (1080, 1920), "reels": (1080, 1920), "tiktok": (1080, 1920), "shorts": (1080, 1920),
    "youtube-shorts": (1080, 1920), "youtube": (1920, 1080), "linkedin": (1080, 1350), "x": (1920, 1080),
    "square": (1080, 1080),
}

# Where captions may sit on each canvas (fractions of height), clear of platform UI.
SAFE = {
    "vertical": {"top": 168 / 1920, "bottom": 1330 / 1920, "right_rail": 0.12},
    "landscape": {"top": 0.05, "bottom": 0.93, "right_rail": 0.0},
}


@dataclass
class FaceTrack:
    times: list[float]
    boxes: list[tuple[float, float, float, float] | None]  # normalized x, y, w, h
    width: int
    height: int

    def median_center(self, t0: float = 0.0, t1: float = 1e9) -> tuple[float, float, float] | None:
        sel = [b for t, b in zip(self.times, self.boxes) if b and t0 <= t <= t1]
        if not sel:
            sel = [b for b in self.boxes if b]
        if not sel:
            return None
        cx = float(np.median([b[0] + b[2] / 2 for b in sel]))
        cy = float(np.median([b[1] + b[3] / 2 for b in sel]))
        h = float(np.median([b[3] for b in sel]))
        return cx, cy, h

    @property
    def coverage(self) -> float:
        return sum(1 for b in self.boxes if b) / max(1, len(self.boxes))

    def to_dict(self) -> dict:
        return {"times": self.times, "boxes": self.boxes, "width": self.width, "height": self.height,
                "coverage": round(self.coverage, 3)}


def track_faces(path: str, duration: float, width: int, height: int, fps: float = 2.0) -> FaceTrack:
    import cv2

    pw = 480
    ph = int(round(height * pw / width / 2) * 2)
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={pw}:{ph},format=gray",
                           "-f", "rawvideo", "-"], capture_output=True, stdin=subprocess.DEVNULL)
    buf = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = len(buf) // (pw * ph)
    frontal = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    profile = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    times, boxes = [], []
    min_side = max(24, ph // 12)
    for i in range(n):
        fr = buf[i * pw * ph:(i + 1) * pw * ph].reshape(ph, pw)
        fr = cv2.equalizeHist(fr)
        faces = frontal.detectMultiScale(fr, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side))
        if len(faces) == 0:
            faces = profile.detectMultiScale(fr, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side))
        times.append(round(i / fps, 3))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])  # the speaker: the largest face
            boxes.append((x / pw, y / ph, w / pw, h / ph))
        else:
            boxes.append(None)
    return FaceTrack(times, boxes, width, height)


@dataclass
class Reframe:
    crop_w: int
    crop_h: int
    out_w: int
    out_h: int
    warnings: list[str]

    def crop_x(self, src_w: int, center: float) -> int:
        x = int(round(center * src_w - self.crop_w / 2))
        return max(0, min(src_w - self.crop_w, x)) // 2 * 2

    def crop_y(self, src_h: int, center: float, eye_line: float = 0.36) -> int:
        y = int(round(center * src_h - self.crop_h * eye_line))
        return max(0, min(src_h - self.crop_h, y)) // 2 * 2


def plan_reframe(src_w: int, src_h: int, target_w: int, target_h: int) -> Reframe:
    """Largest crop of the source with the target's aspect, then the output size we can honestly deliver."""
    tar = target_w / target_h
    if src_w / src_h > tar:  # source is wider: crop the sides
        crop_h, crop_w = src_h, int(round(src_h * tar / 2)) * 2
    else:                    # source is taller: crop top/bottom
        crop_w, crop_h = src_w, int(round(src_w / tar / 2)) * 2
    warnings = []
    out_w, out_h = target_w, target_h
    scale = target_h / crop_h
    if scale > 1.34:
        # Don't blow 405x720 up to 1080x1920 and call it HD: deliver at most 1.33x the crop, flag it.
        out_h = int(round(min(target_h, crop_h * 1.33) / 2)) * 2
        out_w = int(round(out_h * tar / 2)) * 2
        warnings.append(f"source crop is {crop_w}x{crop_h}; delivering {out_w}x{out_h} instead of upscaling "
                        f"{scale:.1f}x to {target_w}x{target_h}. A higher-resolution recording (4K) would look sharper.")
    return Reframe(crop_w, crop_h, out_w, out_h, warnings)


def caption_band(out_w: int, out_h: int, face_center_y: float | None, face_h: float | None) -> tuple[float, float]:
    """(top, bottom) fractions of the frame for captions: below the face, inside the platform-safe band."""
    vertical = out_h > out_w
    safe = SAFE["vertical" if vertical else "landscape"]
    lo, hi = (0.60, safe["bottom"]) if vertical else (0.80, safe["bottom"])
    if face_center_y is not None and face_h is not None:
        chin = face_center_y + face_h * 0.65
        if chin > lo - 0.02:  # the face sits low: put captions above the head instead
            top = max(safe["top"] + 0.02, face_center_y - face_h * 1.2 - 0.12)
            return top, top + 0.12
    return lo, hi
