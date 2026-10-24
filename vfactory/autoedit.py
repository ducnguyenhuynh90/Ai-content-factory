"""Heuristic auto-director: analysis -> recipe.

This is the no-LLM baseline. It encodes editing craft as rules:
  * structure: cold open (strongest moment) -> title -> build -> peak -> resolve -> end card
  * talking footage: cut on silences, pad 50-120 ms, never inside a word
  * b-roll: score every shot, cut on the music's beats, faster toward the peak,
    breathe at the end, hard cuts by default and designed transitions only at
    section boundaries
A director (you, or Claude via the skill) is expected to read and revise the
recipe it writes — it is a strong first cut, not the final word.
"""

from __future__ import annotations

import random
from pathlib import Path

from . import styles
from .analyze import ANALYSIS_FPS


def _best_window(interest: list[float], start: float, end: float, length: float) -> tuple[float, float]:
    """Inside [start, end], the `length`-second window with the highest mean interest."""
    if end - start <= length + 1e-3 or not interest:
        return start, min(end, start + length)
    i0, i1 = int(start * ANALYSIS_FPS), int(end * ANALYSIS_FPS)
    n = max(1, int(length * ANALYSIS_FPS))
    best, best_v = i0, -1.0
    for i in range(i0, max(i0 + 1, i1 - n + 1)):
        seg = interest[i:i + n]
        if not seg:
            break
        v = sum(seg) / len(seg)
        if v > best_v:
            best, best_v = i, v
    s = best / ANALYSIS_FPS
    s = min(max(start, s), end - length)
    return round(s, 3), round(s + length, 3)


def _talk_segments(src_key: str, sa: dict, pad_in: float = 0.06, pad_out: float = 0.12, merge_gap: float = 0.45) -> list[dict]:
    ranges = []
    for s, e in sa["speech"]:
        s, e = max(0.0, s - pad_in), min(sa["duration"], e + pad_out)
        if ranges and s - ranges[-1][1] < merge_gap:
            ranges[-1][1] = e
        else:
            ranges.append([s, e])
    return [{"source": src_key, "start": round(s, 3), "end": round(e, 3), "transition": "cut", "beat": "VOICE"}
            for s, e in ranges if e - s >= 0.5]


def _shot_lengths(n_target: float, look: styles.Look, beat: float | None, rng: random.Random) -> list[float]:
    """A pacing curve: longer shots to open, accelerate to ~70%, breathe at the end."""
    out, t = [], 0.0
    while t < n_target:
        pos = t / max(n_target, 1e-6)
        if beat:
            pattern = look.beats_per_shot
            if pos < 0.2:
                k = pattern[0]
            elif pos < 0.75:
                k = pattern[min(len(pattern) - 1, 1 + int((pos - 0.2) / 0.55 * (len(pattern) - 1)))]
            else:
                k = pattern[min(1, len(pattern) - 1)] if pos < 0.9 else pattern[0]
            d = k * beat
            while d < look.min_shot * 0.6 and k < 16:
                k *= 2
                d = k * beat
        else:
            accel = 1 - 0.55 * max(0.0, 1 - abs(pos - 0.7) / 0.5)
            d = look.max_shot * accel * rng.uniform(0.85, 1.1)
            d = max(look.min_shot, min(look.max_shot, d))
        out.append(round(d, 3))
        t += d
    return out


def direct(analysis: dict, *, look_name: str = "prestige", title: str | None = None, kicker: str = "",
           subtitle: str = "", target: float | None = None, aspect: str = "16:9", fps: int = 30,
           music: str | None = None, ending: dict | None = None, lower_thirds: list | None = None,
           seed: int = 7) -> dict:
    look = styles.get(look_name)
    rng = random.Random(seed)
    sources = {k: v["path"] for k, v in analysis["sources"].items()}
    talk = {k: v for k, v in analysis["sources"].items() if v["kind"] == "talk"}
    broll = {k: v for k, v in analysis["sources"].items() if v["kind"] != "talk"}
    m = analysis.get("music")
    beat = (60.0 / m["bpm"]) if m and m.get("bpm") else None

    segments: list[dict] = []
    cutaways: list[dict] = []
    cold_open: list[dict] = []
    used: set[tuple[str, int]] = set()

    # Shots, ranked.
    pool = []
    for k, sa in broll.items():
        n = 0
        for sh in sa["shots"]:
            if sh["end"] - sh["start"] < 0.8 or sh["brightness"] <= 0.05:
                continue
            # Long takes hold several usable moments: split them so each can be its own shot.
            for part in _split_shot(sh, look.max_shot * 1.25, sa["interest"]):
                if part["score"] < 0.18:  # dark, soft or empty stretch: not worth a cut
                    continue
                pool.append((k, n, part))
                n += 1
    pool.sort(key=lambda x: -x[2]["score"])

    if talk:
        # ----- talking-led edit: voice is the spine, b-roll breathes in at section breaks.
        for k, sa in talk.items():
            segments += _talk_segments(k, sa)
        if look.cold_open > 0 and segments:
            sa_key = segments[0]["source"]
            env = talk[sa_key]["energy"]
            best = max(segments[1:] or segments, key=lambda s: _mean(env, s["start"], s["end"], 0.25))
            if best["end"] - best["start"] <= look.cold_open * 1.8:
                cold_open.append({**best, "beat": "COLD OPEN"})
        if pool:  # one establishing shot before the voice (music carries it in)
            k, i, sh = pool[0]
            s, e = _best_window(broll[k]["interest"], sh["start"], sh["end"], min(look.max_shot, sh["end"] - sh["start"]))
            segments.insert(0, {"source": k, "start": s, "end": e, "transition": "cut", "beat": "ESTABLISH"})
            used.add((k, i))
            named = {lt["segment"] for lt in _resolve_lower_thirds(lower_thirds or [], segments)}
            cutaways = _plan_cutaways(segments, pool[1:] or pool, broll, look, avoid=named)
    else:
        # ----- montage: shots cut to the music, with an arc.
        total_avail = sum(sh["end"] - sh["start"] for _, _, sh in pool)
        if target is None:
            target = min(60.0, max(16.0, total_avail * 0.6))
            if m:
                target = min(target, m["duration"] - look.endcard_hold - look.title_hold)
        if look.cold_open > 0 and pool:
            k, i, sh = pool[0]
            s, e = _best_window(broll[k]["interest"], sh["start"], sh["end"], min(look.cold_open, sh["end"] - sh["start"]))
            cold_open.append({"source": k, "start": s, "end": e, "transition": "cut", "beat": "COLD OPEN"})
            used.add((k, i))
        lengths = _shot_lengths(target, look, beat, rng)
        available = [x for x in pool if (x[0], x[1]) not in used]
        # Arc: open on a composed, calmer shot; peak with the most kinetic; resolve on a beautiful one.
        calm = sorted(available, key=lambda x: (x[2]["motion"], -x[2]["score"]))
        kinetic = sorted(available, key=lambda x: -(min(x[2]["motion"] / 0.05, 1.0) * 0.5 + x[2]["score"] * 0.5))
        picks: list = []
        last_source = None
        for j, d in enumerate(lengths):
            pos = j / max(1, len(lengths) - 1)
            ranked = calm if (pos < 0.2 or pos > 0.85) else kinetic
            cand = [x for x in ranked if (x[0], x[1]) not in used and x[2]["end"] - x[2]["start"] >= min(d, 0.8)]
            if not cand:
                used = set()  # pool exhausted: allow repeats rather than end early
                cand = [x for x in ranked if x[2]["end"] - x[2]["start"] >= min(d, 0.8)]
                if not cand:
                    break
            # avoid two consecutive shots from the same source when possible
            choice = next((x for x in cand[:4] if x[0] != last_source), cand[0])
            k, i, sh = choice
            used.add((k, i))
            last_source = k
            dur = min(d, sh["end"] - sh["start"])
            s, e = _best_window(broll[k]["interest"], sh["start"], sh["end"], dur)
            picks.append({"source": k, "start": s, "end": e, "transition": "cut",
                          "beat": "OPEN" if pos < 0.2 else ("RESOLVE" if pos > 0.85 else "BUILD" if pos < 0.6 else "PEAK")})
        # Designed transitions only at section changes; everything else is a cut.
        # Extra punctuation inside a long section is allowed, but never within 4 cuts of another.
        designed = [t for t in look.transitions if t != "cut"] or ["cut"]
        last = -99
        for j in range(1, len(picks)):
            if picks[j]["beat"] != picks[j - 1]["beat"]:
                picks[j]["transition"] = rng.choice(designed)
                last = j
            elif j - last >= 5 and rng.random() < 0.25:
                picks[j]["transition"] = rng.choice(designed)
                last = j
        segments = picks

    if not segments:
        raise ValueError("nothing usable found in the footage")
    name = title or Path(next(iter(sources.values()))).parent.name.replace("_", " ").replace("-", " ").title()
    rec = {
        "version": 1,
        "look": look.name,
        "format": {"aspect": aspect, "fps": fps},
        "sources": sources,
        "title": {"text": name, "kicker": kicker, "subtitle": subtitle, "mode": "auto"},
        "cold_open": cold_open,
        "segments": segments,
        "lower_thirds": _resolve_lower_thirds(lower_thirds or [], segments),
        "cutaways": cutaways,
        "chapters": [],
        "ending": ending if ending is not None else {"title": name, "tagline": subtitle, "cta": "", "handle": kicker},
        "captions": {"words": None},
        "music": ({"file": music, "sync_downbeats": m["downbeats"][:64]} if m else {"file": music}) if music else {},
        "sfx": True,
        "output": "final.mp4",
    }
    if music and broll:
        # Ambient b-roll sound sits under the score.
        rec["source_gain_db"] = {k: -14.0 for k in broll}
    return rec


def _plan_cutaways(segments: list[dict], pool: list, broll: dict, look: styles.Look,
                   first_after: float = 4.0, every: float = 7.0, avoid: set | None = None) -> list[dict]:
    """B-roll laid OVER the voice (the speaker keeps talking underneath) — the standard
    documentary/interview grammar. Never in the first seconds of the speaker, never at the end."""
    out, t, last = [], 0.0, -999.0
    voice_total = sum(s["end"] - s["start"] for s in segments if s["beat"] == "VOICE")
    voice_t = 0.0
    j = 0
    for idx, seg in enumerate(segments):
        dur = seg["end"] - seg["start"]
        if seg["beat"] == "VOICE" and pool:
            if (voice_t >= first_after and t - last >= every and dur >= 2.6 and voice_t < voice_total - 4.0
                    and idx not in (avoid or set())):
                k, _, sh = pool[j % len(pool)]
                j += 1
                length = min(3.6, dur - 0.8, sh["end"] - sh["start"])
                if length >= 1.8:
                    s, e = _best_window(broll[k]["interest"], sh["start"], sh["end"], length)
                    out.append({"segment": idx, "offset": 0.4, "source": k, "start": s, "end": e})
                    last = t
            voice_t += dur
        t += dur
    return out


def _resolve_lower_thirds(lts: list[dict], segments: list[dict]) -> list[dict]:
    """'segment': 'first_voice' -> the first speaking segment long enough to read a name over."""
    out = []
    for lt in lts:
        lt = dict(lt)
        if lt.get("segment") == "first_voice":
            idx = next((i for i, s in enumerate(segments) if s["beat"] == "VOICE" and s["end"] - s["start"] >= 3.5),
                       next((i for i, s in enumerate(segments) if s["beat"] == "VOICE"), 0))
            lt["segment"] = idx
        out.append(lt)
    return out


def _split_shot(sh: dict, max_len: float, interest: list[float]) -> list[dict]:
    dur = sh["end"] - sh["start"]
    if dur <= max_len * 1.6:
        return [sh]
    n = int(dur // max_len)
    step = dur / n
    parts = []
    for j in range(n):
        s, e = sh["start"] + j * step, sh["start"] + (j + 1) * step
        seg = interest[int(s * ANALYSIS_FPS):max(int(s * ANALYSIS_FPS) + 1, int(e * ANALYSIS_FPS))]
        score = sorted(seg)[int(len(seg) * 0.75)] if seg else sh["score"]
        parts.append({**sh, "start": round(s, 3), "end": round(e, 3), "score": float(score)})
    return parts


def _mean(env: list[float], s: float, e: float, hop: float) -> float:
    seg = env[int(s / hop):max(int(s / hop) + 1, int(e / hop))]
    return sum(seg) / len(seg) if seg else 0.0
