"""short.json: the contract between the writer (Claude, via the tiktok-shorts skill) and the renderer.

{
  "meta": {
    "title": "internal working title", "lang": "vi", "pillar": "history", "format": "story",
    "hook_type": "contrarian", "target_seconds": [25, 45], "theme": "night",
    "voice": "vi-VN-NamMinhNeural", "rate": "+8%", "music": "tense",
    "caption": "post caption with a question at the end", "hashtags": ["#lichsu", "#kienthuc"],
    "cover_text": "3-5 word cover", "disclaimer": "", "series": "Bài học từ lịch sử", "part": 1,
    "cta": "Theo dõi để xem phần 2", "handle": "@kenh"
  },
  "sources": [{"id": "s1", "cite": "...", "url": "..."}],
  "beats": [{"id": "b1", "narration": "spoken words", "visual": {"type": "hook", ...},
             "sources": ["s1"], "certainty": "established|estimate|disputed|attributed",
             "sfx": [{"kind": "hit", "cue": "word"}], "captions": true}],
  "pronounce": {"Odlyzko": "Ốt-lít-skô"}
}

Visual types and their fields: VISUALS below; rendering in render.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

VISUALS = {
    # frame 0: the claim is ALREADY on screen; line 2 slams in on punch_cue
    "hook": {"required": ["lines"], "optional": ["highlight", "punch_cue", "picture", "image", "kicker"]},
    "text": {"required": ["text"], "optional": ["highlight", "kicker", "picture"]},
    "stat": {"required": ["value", "label"], "optional": ["from", "prefix", "suffix", "cue", "picture"]},
    "picture": {"required": ["asset"], "optional": ["caption", "act", "count", "cue", "highlight"]},
    "image": {"required": ["src"], "optional": ["caption", "move", "highlight", "credit"]},
    "clip": {"required": ["src"], "optional": ["caption", "start", "highlight", "credit", "mute"]},
    "list": {"required": ["items"], "optional": ["title", "cues"]},
    "compare": {"required": ["left", "right"], "optional": ["title", "cue"]},
    "question": {"required": ["question"], "optional": ["choices", "answer", "think_seconds"]},
    "end": {"required": ["text"], "optional": ["cta", "handle", "next", "disclaimer"]},
}
PICTURE_ACTS = ("pop", "float", "shake", "grow", "shrink", "fall", "bounce")
THEMES = ("night", "paper", "neon")
FORMATS = ("story", "explainer", "list", "myth", "quiz", "compare", "pov", "news")
HOOK_TYPES = ("question", "shock_stat", "contrarian", "story", "list", "mistake", "secret", "pov", "challenge")
CERTAINTY = ("established", "estimate", "disputed", "attributed")
# words per minute of natural TTS narration; Vietnamese counts syllables, which run faster than English words
WPM = {"vi": 200.0, "en": 160.0}
HEDGE = {
    "vi": ("khoảng", "chừng", "ước tính", "ước chừng", "được cho là", "tương truyền", "người ta kể", "có lẽ",
           "theo", "gần", "hơn", "dưới", "chưa được kiểm chứng", "giai thoại", "nghe nói"),
    "en": ("about", "around", "roughly", "estimate", "reportedly", "attributed", "is said", "allegedly",
           "according to", "nearly", "almost", "more than", "under", "legend"),
}
PREAMBLE = re.compile(r"^\s*(hôm nay|xin chào|chào các bạn|chào mọi người|trong video này|today|hi |hello|hey guys|"
                      r"in this video|welcome)", re.I)
FOLLOW = re.compile(r"(theo dõi|follow|đăng ký|subscribe|like và|thả tim|nhấn like)", re.I)
SAFE_MAX_WORDS = 8  # words in one on-screen element: more and nobody reads it in a 2 s scene


class ShortError(ValueError):
    pass


def load(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(data)
    return data


def words(text: str) -> list[str]:
    return re.findall(r"[\w'’£$€%.,-]+", text or "", re.UNICODE)


def lang_of(S: dict) -> str:
    return "vi" if str(S.get("meta", {}).get("lang", "vi")).lower().startswith("vi") else "en"


def rate_factor(rate: str | None) -> float:
    m = re.match(r"([+-]\d+)%", str(rate or "+0%"))
    return 1.0 + (int(m.group(1)) / 100.0 if m else 0.0)


def est_seconds(text: str, lang: str = "vi", rate: str | None = None) -> float:
    return len(words(text)) / (WPM[lang] * rate_factor(rate)) * 60


def has_anchor(text: str) -> bool:
    """A number, or a proper name (a capitalised word that doesn't start a sentence)."""
    if re.search(r"\d", text):
        return True
    for sent in re.split(r"[.!?…]+", text):
        ws = sent.split()
        if any(w[:1].isupper() for w in ws[1:]):
            return True
    return False


def validate(S: dict) -> None:
    for k in ("meta", "beats"):
        if k not in S:
            raise ShortError(f"short needs '{k}'")
    if not S["beats"]:
        raise ShortError("short needs at least one beat")
    ids, src_ids = set(), {s["id"] for s in S.get("sources", [])}
    for i, b in enumerate(S["beats"]):
        where = f"beat {i} ({b.get('id')})"
        if not b.get("id") or b["id"] in ids:
            raise ShortError(f"{where}: missing or duplicate id")
        ids.add(b["id"])
        v = b.get("visual") or {}
        t = v.get("type")
        if t not in VISUALS:
            raise ShortError(f"{where}: visual.type must be one of {list(VISUALS)}")
        for r in VISUALS[t]["required"]:
            if r not in v:
                raise ShortError(f"{where}: visual '{t}' needs '{r}'")
        if not str(b.get("narration", "")).strip() and not v.get("hold") and t != "question":
            raise ShortError(f"{where}: empty narration needs visual.hold seconds")
        if t == "picture" and v.get("act", "pop") not in PICTURE_ACTS:
            raise ShortError(f"{where}: picture act must be one of {PICTURE_ACTS}")
        if t == "list" and not 1 <= len(v["items"]) <= 5:
            raise ShortError(f"{where}: a list holds 1-5 items")
        if t == "hook" and not 1 <= len(v["lines"]) <= 2:
            raise ShortError(f"{where}: a hook holds 1-2 lines")
        if b.get("certainty") and b["certainty"] not in CERTAINTY:
            raise ShortError(f"{where}: certainty must be one of {CERTAINTY}")
        for s in b.get("sources", []):
            if s not in src_ids:
                raise ShortError(f"{where}: unknown source '{s}'")
    th = S["meta"].get("theme", "night")
    if th not in THEMES:
        raise ShortError(f"meta.theme must be one of {THEMES}")


def screen_texts(v: dict) -> list[str]:
    t = v["type"]
    if t == "hook":
        return list(v["lines"])
    if t == "list":
        return [i if isinstance(i, str) else i.get("text", "") for i in v["items"]] + [v.get("title", "")]
    if t == "compare":
        return [str(v["left"].get("label", "")), str(v["right"].get("label", "")), v.get("title", "")]
    if t == "question":
        return [v["question"], *v.get("choices", [])]
    return [str(v.get(k, "")) for k in ("text", "label", "caption", "cta") if v.get(k)]


def beat_seconds(b: dict, lang: str, rate: str | None) -> float:
    v = b["visual"]
    d = est_seconds(b.get("narration", ""), lang, b.get("rate", rate)) + 0.3
    if not b.get("narration", "").strip():
        d = float(v.get("hold", 1.5))
    if v["type"] == "question":
        d += float(v.get("think_seconds", 3.0)) + (1.2 if v.get("answer") else 0)
    return d


def lint(S: dict) -> dict:
    """TikTok retention + honesty checks. Returns {errors, warnings, stats}; errors block rendering."""
    errors, warns = [], []
    meta, beats = S["meta"], S["beats"]
    lang = lang_of(S)
    rate = meta.get("rate")
    durs = [beat_seconds(b, lang, rate) for b in beats]
    total = sum(durs)
    lo, hi = meta.get("target_seconds", [20, 60])
    if total > hi * 1.08:
        errors.append(f"estimated {total:.0f}s is over the {hi}s target: cut words, keep the scenes")
    if total < lo * 0.85:
        warns.append(f"estimated {total:.0f}s is under the {lo}s target")
    if total > 90:
        warns.append("over 90 s: on TikTok, completion rate falls fast past a minute; split into parts unless the story needs it")
    # --- the first two seconds
    first = beats[0]
    if first["visual"]["type"] != "hook":
        errors.append("beat 1 must be visual.type 'hook': frame 0 is the scroll-stop, the claim already on screen")
    hook_words = words(first.get("narration", ""))
    hook_s = est_seconds(first.get("narration", ""), lang, rate)
    if hook_s > 3.2:
        errors.append(f"hook narration runs ~{hook_s:.1f}s ({len(hook_words)} words): the hook must land inside ~3 s")
    if PREAMBLE.search(first.get("narration", "")):
        errors.append("hook starts with a preamble (hello/today/in this video): open on the claim")
    if not has_anchor(first.get("narration", "")) and not first["visual"].get("picture") and not first["visual"].get("image"):
        warns.append("hook has no concrete anchor (a name, a number, a year, a picture): specific beats vague")
    for t in screen_texts(first["visual"]):
        if len(words(t)) > 7:
            warns.append(f"hook line '{t}' has {len(words(t))} words: ≤ 6 reads in one glance")
    # --- pacing: a new picture every 2-4 s (pattern interrupt)
    for b, d in zip(beats, durs):
        if d > 6.5 and b["visual"]["type"] not in ("question", "list", "clip"):
            warns.append(f"{b['id']}: ~{d:.1f}s on one scene; split it (TikTok viewers expect a new picture every 2-4 s)")
        for t in screen_texts(b["visual"]):
            if len(words(t)) > SAFE_MAX_WORDS:
                errors.append(f"{b['id']}: on-screen text '{t[:40]}…' has {len(words(t))} words (max {SAFE_MAX_WORDS}): "
                              "show the key phrase, the captions carry the sentence")
    # --- honesty
    hedges = HEDGE[lang]
    for b in beats:
        c = b.get("certainty")
        if c in ("estimate", "disputed", "attributed"):
            low = b.get("narration", "").lower()
            if not any(h in low for h in hedges):
                errors.append(f"{b['id']}: certainty '{c}' must be SAID in the narration (e.g. {', '.join(hedges[:4])})")
        has_num = re.search(r"\d", b.get("narration", "")) or b["visual"]["type"] == "stat"
        if has_num and not b.get("sources") and b["visual"]["type"] not in ("end", "question"):
            warns.append(f"{b['id']}: a number with no source: add one or make it clearly an example")
    if any(b.get("sources") for b in beats) and not S.get("sources"):
        errors.append("beats cite sources but 'sources' is empty")
    topic = (meta.get("pillar", "") + " " + meta.get("topic", "")).lower()
    if any(k in topic for k in ("invest", "finance", "tài chính", "đầu tư", "health", "sức khỏe", "y tế", "crypto")) \
            and not meta.get("disclaimer"):
        errors.append("finance/health topic needs meta.disclaimer (shown on the end card and in the caption)")
    # --- CTA only at the end, after the payoff
    for b in beats[:-1]:
        if FOLLOW.search(b.get("narration", "")):
            warns.append(f"{b['id']}: asks to follow/like before the payoff; keep the one CTA for the last beat")
    if beats[-1]["visual"]["type"] != "end":
        warns.append("last beat is not an 'end' card: close the loop and give one CTA")
    # --- publish kit
    if not meta.get("caption"):
        warns.append("meta.caption is empty: write the post caption (a line of context + a question that invites comments)")
    tags = meta.get("hashtags", [])
    if not 3 <= len(tags) <= 6:
        warns.append(f"{len(tags)} hashtags: use 3-6 (1-2 broad, 2-3 niche, 1 series tag)")
    if meta.get("format") and meta["format"] not in FORMATS:
        warns.append(f"meta.format '{meta['format']}' is not one of {FORMATS} (analytics groups by it)")
    if meta.get("hook_type") and meta["hook_type"] not in HOOK_TYPES:
        warns.append(f"meta.hook_type '{meta['hook_type']}' is not one of {HOOK_TYPES} (analytics groups by it)")
    if not meta.get("hook_type"):
        warns.append("meta.hook_type is empty: analytics learns which hooks work only if you tag them")
    n_words = sum(len(words(b.get("narration", ""))) for b in beats)
    return {"errors": errors, "warnings": warns,
            "stats": {"beats": len(beats), "words": n_words, "est_seconds": round(total, 1),
                      "hook_seconds": round(hook_s, 1), "avg_scene_seconds": round(total / len(beats), 1)}}


def script_markdown(S: dict) -> str:
    """Approval view: what is said, what is seen, the sources, the post caption."""
    meta = S["meta"]
    rep = lint(S)
    rows = ["| # | ~s | narration | on screen |", "|---|---|---|---|"]
    lang, rate = lang_of(S), meta.get("rate")
    for b in S["beats"]:
        v = b["visual"]
        screen = " / ".join(t for t in screen_texts(v) if t) or v.get("asset") or v.get("src") or ""
        if v["type"] == "picture":
            screen = f"{v['asset']}{' ×' + str(v['count']) if v.get('count', 1) > 1 else ''} ({v.get('act', 'pop')}) {screen}"
        flag = f" _({b['certainty']})_" if b.get("certainty") in ("estimate", "disputed", "attributed") else ""
        rows.append(f"| {b['id']} | {beat_seconds(b, lang, rate):.1f} | {b.get('narration', '')}{flag} | {v['type']}: {screen} |")
    st = rep["stats"]
    out = [f"# {meta.get('title', 'Short')}",
           f"_{meta.get('series', '')} · {st['words']} words · ~{st['est_seconds']} s · hook ~{st['hook_seconds']} s · "
           f"{meta.get('format', '?')} / {meta.get('hook_type', '?')}_", "",
           "## Script", *rows, "",
           "## Post", f"**Caption:** {meta.get('caption', '')}", f"**Hashtags:** {' '.join(meta.get('hashtags', []))}",
           f"**Cover:** {meta.get('cover_text', '')}", "",
           "## Sources", *[f"- [{s['id']}] {s['cite']}" + (f" — {s['url']}" if s.get('url') else '') for s in S.get("sources", [])],
           "", "## Lint", *[f"- ERROR: {e}" for e in rep["errors"]], *[f"- warning: {w}" for w in rep["warnings"]]]
    if not rep["errors"] and not rep["warnings"]:
        out.append("- clean")
    return "\n".join(out) + "\n"
