"""Editorial decisions from the transcript: retakes, best takes, dead time, separate videos.

Learned from GhostEditor's take-selection guide (adapted from talking-head-reel, MIT) and
video-use: people record a script two or three times; the transcript is the map; pick one
version of each sentence by meaning and fluency (later is a tiebreaker, not a rule), keep
one-breath runs together, cut on word times with padding, keep short pauses (they are the
speaker's rhythm) and only tighten real dead time. When a choice changes the message and
confidence is low, flag it instead of guessing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

RESTART_PATTERNS = [
    # English
    r"let'?s (re-?do|redo|do) (that|this|it) again", r"let me (do|say|try) (that|this|it) again", r"start (again|over)",
    r"one more time", r"(okay|ok|alright),? again", r"take two", r"from the top", r"let'?s try (that )?again",
    r"scratch that", r"(sorry|wait),? (let me|i'?ll) (start|redo)", r"cut,? cut",
    # Vietnamese
    r"làm lại", r"nói lại", r"quay lại", r"thu lại", r"lại nhé",
    # Spanish / French / German / Portuguese
    r"otra vez", r"de nuevo", r"desde el principio", r"on recommence", r"je recommence", r"encore une fois",
    r"noch ?mal", r"von vorne", r"de novo", r"mais uma vez",
]
RESTART_RE = re.compile("|".join(RESTART_PATTERNS), re.I)
FILLERS = {"um", "uh", "uhm", "umm", "er", "erm", "ah", "hmm", "mm", "eh", "ờ", "ừ", "ừm", "à", "ơ", "euh", "ähm", "äh", "eh"}
TOPIC_RE = re.compile(r"(next video|video (two|2|three|3)|part (two|2|three|3)|new topic|next topic|next one|second video|"
                      r"okay,? next|video tiếp|video thứ (hai|ba)|chủ đề (tiếp|mới))", re.I)


def norm_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[\w']+", text.lower()) if t not in FILLERS]


@dataclass
class Sentence:
    idx: int
    words: list[dict]
    is_marker: bool = False
    group: int = -1
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def start(self) -> float:
        return self.words[0]["start"]

    @property
    def end(self) -> float:
        return self.words[-1]["end"]

    @property
    def text(self) -> str:
        return " ".join(w["word"] for w in self.words)

    @property
    def tokens(self) -> list[str]:
        return norm_tokens(self.text)


def split_sentences(words: list[dict], gap: float = 0.7) -> list[Sentence]:
    out, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] >= gap:
            out.append(cur)
            cur = []
        cur.append(w)
        if w["word"][-1:] in ".?!…":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    sents = []
    for ws in out:
        s = Sentence(len(sents), ws)
        text = s.text
        m = RESTART_RE.search(text)
        if m:
            # A marker sentence is mostly the marker; otherwise the marker ends a failed attempt inside it.
            if len(norm_tokens(m.group(0))) >= len(s.tokens) * 0.5:
                s.is_marker = True
            else:
                s.notes.append(f"contains restart phrase '{m.group(0)}'")
        sents.append(s)
    return sents


CONTENT_STOP = set("a an the and or but so to of in on for with at by is are was were be it this that i you we they "
                   "my your our me us them he she his her its just very really".split())


def similarity(a: list[str], b: list[str]) -> float:
    """How likely two sentences are attempts at the same line. Parallel lines ("first point" / "second point")
    share structure but not content, so content-word overlap must agree with the sequence match."""
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    prefix = k / min(len(a), len(b)) if k >= 3 else 0.0
    ca, cb = {t for t in a if t not in CONTENT_STOP}, {t for t in b if t not in CONTENT_STOP}
    content = len(ca & cb) / max(1, len(ca | cb))
    if prefix:
        return max(prefix, ratio)
    if content < 0.5:
        return min(ratio, content)
    if min(len(a), len(b)) < 6 and ratio < 0.8:  # short lines need near-identical wording
        return min(ratio, 0.55)
    return ratio


def group_retakes(sents: list[Sentence], window: int = 8, threshold: float = 0.6) -> list[list[Sentence]]:
    """Group sentences that are attempts at the same line. Order of groups = order the idea first appears."""
    groups: list[list[Sentence]] = []
    content = [s for s in sents if not s.is_marker]
    for s in content:
        best, best_sim = None, 0.0
        for g in groups[-window:]:
            sim = max(similarity(s.tokens, o.tokens) for o in g)
            if sim > best_sim:
                best, best_sim = g, sim
        if best is not None and best_sim >= threshold:
            best.append(s)
        else:
            groups.append([s])
    # False starts: a short fragment whose tokens begin the next idea ("so the thing is" -> "so the thing is, ...").
    merged: list[list[Sentence]] = []
    for g in groups:
        if merged and len(merged[-1]) == 1 and len(merged[-1][0].tokens) <= 5:
            frag = merged[-1][0].tokens
            nxt = g[0].tokens
            if frag and nxt[:len(frag)] == frag and len(nxt) > len(frag):
                frag_s = merged.pop()[0]
                frag_s.notes.append("false start")
                g = [frag_s, *g]
        merged.append(g)
    for gi, g in enumerate(merged):
        for s in g:
            s.group = gi
    return merged


def score_take(s: Sentence, group: list[Sentence], energy: list[float] | None = None, hop: float = 0.25,
               median_wps: float | None = None) -> float:
    toks = s.tokens
    longest = max(len(o.tokens) for o in group) or 1
    complete = (0.25 if s.text.rstrip()[-1:] in ".?!…" else 0.0) + 0.25 * len(toks) / longest
    raw = [w["word"].lower().strip(",.?!") for w in s.words]
    fillers = sum(1 for t in raw if t in FILLERS)
    repeats = sum(1 for a, b in zip(raw, raw[1:]) if a == b and a)
    fluency = -0.08 * fillers - 0.1 * repeats - (0.2 if any("restart" in n for n in s.notes) else 0.0) - \
        (0.25 if "false start" in s.notes else 0.0)
    probs = [w.get("prob", 0.9) for w in s.words]
    clarity = 0.15 * (sum(probs) / len(probs))
    dur = max(0.3, s.end - s.start)
    wps = len(toks) / dur
    pacing = 0.0
    if median_wps:
        pacing = -0.1 * min(1.0, abs(math.log(max(wps, 0.1) / median_wps)) / 0.7)
    audio = 0.0
    if energy:
        seg = energy[int(s.start / hop):max(int(s.start / hop) + 1, int(s.end / hop))]
        med = sorted(energy)[len(energy) // 2] if energy else 0
        if seg and med > 0:
            audio = -0.1 * max(0.0, 1 - (sum(seg) / len(seg)) / med)
    order = group.index(s)
    recency = 0.05 * order / max(1, len(group) - 1)  # people warm up; a tiebreaker only
    return round(complete + fluency + clarity + pacing + audio + recency, 4)


@dataclass
class TakeDecision:
    group: int
    chosen: Sentence
    alternatives: list[Sentence]
    confidence: float
    flagged: bool
    reason: str


def choose_takes(groups: list[list[Sentence]], energy: list[float] | None = None) -> list[TakeDecision]:
    all_s = [s for g in groups for s in g]
    rates = sorted(len(s.tokens) / max(0.3, s.end - s.start) for s in all_s) or [2.5]
    median_wps = rates[len(rates) // 2]
    out = []
    for gi, g in enumerate(groups):
        for s in g:
            s.score = score_take(s, g, energy, median_wps=median_wps)
        ranked = sorted(g, key=lambda s: -s.score)
        best = ranked[0]
        alts = ranked[1:]
        margin = best.score - alts[0].score if alts else 1.0
        flagged = bool(alts) and margin < 0.08 and similarity(best.tokens, alts[0].tokens) < 0.9
        reason = "only take" if not alts else (
            f"score {best.score:.2f} vs {alts[0].score:.2f}" + (f"; {', '.join(best.notes)}" if best.notes else ""))
        out.append(TakeDecision(gi, best, alts, round(min(1.0, margin / 0.2), 2) if alts else 1.0, flagged, reason))
    return out


@dataclass
class Segment:
    start: float
    end: float
    sentences: list[int]


PACE = {  # (max pause kept as-is, mid-sentence pause target, sentence-boundary pause target)
    "tight": (0.35, 0.18, 0.3),
    "natural": (0.5, 0.25, 0.45),
    "relaxed": (0.7, 0.35, 0.6),
}


def build_segments(decisions: list[TakeDecision], pace: str = "natural", pad_in: float = 0.12, pad_out: float = 0.22,
                   fps: float = 30.0) -> tuple[list[Segment], list[dict]]:
    """Chosen sentences -> source ranges with tightened pauses. Returns (segments, pauses_removed)."""
    max_keep, mid_target, sent_target = PACE.get(pace, PACE["natural"])
    chosen = [d.chosen for d in decisions]
    words: list[tuple[dict, int, bool]] = []  # (word, sentence idx, is sentence end)
    for s in chosen:
        for i, w in enumerate(s.words):
            words.append((w, s.idx, i == len(s.words) - 1))
    segs: list[Segment] = []
    removed: list[dict] = []
    if not words:
        return segs, removed
    cur_start = words[0][0]["start"] - pad_in
    cur_sents = [words[0][1]]
    for (w, si, is_end), (nw, nsi, _) in zip(words, words[1:]):
        gap = nw["start"] - w["end"]
        contiguous = nsi == si or nsi == si + 1  # same sentence or the very next one in the recording
        if contiguous and 0 <= gap <= max_keep:
            if nsi not in cur_sents:
                cur_sents.append(nsi)
            continue
        if contiguous and gap > max_keep:
            # Tighten, but keep breath: sentence ends and punchlines keep more air.
            target = sent_target if is_end else mid_target
            following = _rest_of_sentence(words, nw)
            if is_end and len(following) <= 4 and following and following[-1]["word"][-1:] in "!?.":
                target = max(target, 0.6)  # a short payoff line after a pause: the pause is the setup
            keep_after, keep_before = target * 0.55, target * 0.45
            seg_end = w["end"] + keep_after
            removed.append({"at": round(w["end"], 3), "gap": round(gap, 3), "kept": round(target, 3)})
        else:
            seg_end = min(w["end"] + pad_out, nw["start"] - 0.05) if nw["start"] > w["end"] else w["end"] + pad_out
            keep_before = pad_in
        segs.append(Segment(round(cur_start, 3), round(seg_end, 3), cur_sents))
        cur_start = nw["start"] - keep_before
        cur_sents = [nsi]
    last = words[-1][0]
    segs.append(Segment(round(cur_start, 3), round(last["end"] + pad_out, 3), cur_sents))
    # Snap to the frame grid (truncate starts, round ends) so picture and voice cut at the same instants.
    for s in segs:
        s.start = max(0.0, math.floor(s.start * fps) / fps)
        s.end = math.ceil(s.end * fps) / fps
    merged: list[Segment] = []
    for s in segs:
        if merged and s.start <= merged[-1].end + 1e-6:
            merged[-1].end = max(merged[-1].end, s.end)
            merged[-1].sentences += [x for x in s.sentences if x not in merged[-1].sentences]
        else:
            merged.append(s)
    return merged, removed


def _rest_of_sentence(words, start_word) -> list[dict]:
    out, on = [], False
    for w, _, is_end in words:
        if w is start_word:
            on = True
        if on:
            out.append(w)
            if is_end:
                break
    return out


def split_topics(sents: list[Sentence], min_gap: float = 4.0) -> list[list[Sentence]]:
    """Split one recording into separate videos only on strong evidence: an explicit 'next video'
    marker, or a long gap where the vocabulary on both sides barely overlaps."""
    if not sents:
        return []
    cuts = []
    for i in range(1, len(sents)):
        prev, cur = sents[i - 1], sents[i]
        gap = cur.start - prev.end
        if TOPIC_RE.search(cur.text) and (gap > 1.0 or cur.is_marker or len(cur.tokens) <= 8):
            cuts.append(i)
            continue
        if gap >= min_gap:
            before = {t for s in sents[max(0, i - 6):i] for t in s.tokens if len(t) > 3}
            after = {t for s in sents[i:i + 6] for t in s.tokens if len(t) > 3}
            jacc = len(before & after) / max(1, len(before | after))
            if jacc < 0.08:
                cuts.append(i)
    parts, last = [], 0
    for c in cuts:
        parts.append(sents[last:c])
        last = c
    parts.append(sents[last:])
    # drop a part that is only the marker line ("okay, next video")
    cleaned = [[s for s in p if not (TOPIC_RE.search(s.text) and len(s.tokens) <= 6)] for p in parts]
    return [p for p in cleaned if any(not s.is_marker for s in p)]


def plan(words: list[dict], energy: list[float] | None = None, pace: str = "natural", fps: float = 30.0,
         split: bool = True) -> list[dict]:
    """Full editorial pass. Returns one plan per output video."""
    sents = split_sentences(words)
    parts = split_topics(sents) if split else [sents]
    plans = []
    for pi, part in enumerate(parts):
        markers = [s for s in part if s.is_marker]
        groups = group_retakes(part)
        decisions = choose_takes(groups, energy)
        segs, removed = build_segments(decisions, pace=pace, fps=fps)
        plans.append({
            "part": pi + 1,
            "title_hint": " ".join(decisions[0].chosen.text.split()[:8]) if decisions else "",
            "segments": [{"start": s.start, "end": s.end, "sentences": s.sentences} for s in segs],
            "duration": round(sum(s.end - s.start for s in segs), 3),
            "decisions": [{
                "idea": d.group + 1, "chosen": {"sentence": d.chosen.idx, "start": d.chosen.start, "end": d.chosen.end,
                                                "text": d.chosen.text, "score": d.chosen.score},
                "alternatives": [{"sentence": a.idx, "start": a.start, "end": a.end, "text": a.text, "score": a.score}
                                 for a in d.alternatives],
                "confidence": d.confidence, "flagged": d.flagged, "reason": d.reason} for d in decisions],
            "restart_markers": [{"start": m.start, "end": m.end, "text": m.text} for m in markers],
            "pauses_tightened": removed,
            "words_kept": [w for d in decisions for w in d.chosen.words],
        })
    return plans
