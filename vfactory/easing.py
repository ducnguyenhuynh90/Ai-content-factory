"""Easing curves. Never animate linearly — linear motion reads as robotic."""

from __future__ import annotations

import math


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def progress(t: float, start: float, dur: float) -> float:
    """Normalized 0..1 progress of an animation that starts at `start` and lasts `dur`."""
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return clamp((t - start) / dur)


def lerp(a: float, b: float, p: float) -> float:
    return a + (b - a) * p


def linear(p: float) -> float:
    return p


def out_cubic(p: float) -> float:
    return 1 - (1 - p) ** 3


def in_cubic(p: float) -> float:
    return p ** 3


def in_out_cubic(p: float) -> float:
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def out_quint(p: float) -> float:
    return 1 - (1 - p) ** 5


def out_expo(p: float) -> float:
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def in_expo(p: float) -> float:
    return 0.0 if p <= 0 else 2 ** (10 * p - 10)


def in_out_expo(p: float) -> float:
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    return 2 ** (20 * p - 10) / 2 if p < 0.5 else (2 - 2 ** (-20 * p + 10)) / 2


def out_back(p: float, s: float = 1.70158) -> float:
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def in_out_sine(p: float) -> float:
    return -(math.cos(math.pi * p) - 1) / 2


EASINGS = {
    name: fn
    for name, fn in globals().items()
    if callable(fn) and name not in {"clamp", "progress", "lerp"} and not name.startswith("_")
    and name not in {"annotations", "math"}
}
