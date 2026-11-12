"""Deterministic checks for an agent-written lesson: the `stage` contract (docs/plans/story-sticker-agent.md §3) and the
series rules the human writers learned the hard way (BRIEF_frameworks / BRIEF_book_episodes_v2 / the gate briefs).

These run before `python -m vfactory.lesson lint` and do not depend on the engine knowing the sticker style, so a lesson
is checked even while the engine work is still landing. Errors go back to the model in the repair loop; warnings are
editor's notes (also shown to the critique stage).
"""

from __future__ import annotations

import re

try:  # read-only reuse of the engine's word counter and hedge list; fall back if the engine module is mid-edit
    from vfactory.lesson.schema import ACTS, HEDGE_RE, words
except Exception:  # noqa: BLE001
    ACTS = ("hook", "context", "story", "misconception", "complication", "turn", "principle", "example", "question",
            "recap", "close")
    HEDGE_RE = re.compile(r"\b(?:theo lời|theo ước tính|theo|được cho là|người ta kể|khoảng|có lẽ|"
                          r"chính\s+(?:\w+\s+){0,3}?(?:nói|kể|viết|thừa nhận|cho biết)|ước tính|tương truyền|"
                          r"gây tranh cãi|chưa kiểm chứng)\b", re.I)

    def words(text: str) -> list[str]:
        return re.findall(r"[\w'’£$€%-]+", text)

# ---- length: calibrated on real builds, not on the TTS spec sheet
# Fitted on the 10 built framework episodes (lessons/frameworks/001-010 at speed 0.88: every beat's timing.json `narr`
# and `dur` against its lesson.json narration): speech runs at ~211 syllables/min at speed 0.88 (= 240 x speed); each
# narrated beat adds ~1.3 s (lead-in + tail), the retrieval question adds think_seconds + ~4.5 s (answer reveal), the
# end card ~2.6 s, a silent beat its `hold`. Whole films average ~180 syllables/min (854 syllables -> 286.7 s in the
# sticker pilot; this model says 291 s). Mean absolute error over the 10 episodes: 1.4 % (the engine lint's 270 x speed
# with no gaps reads them ~22 % short).
SPEECH_SYL_PER_MIN = 240.0   # at speed 1.0; scales with meta.speed
BEAT_GAP_S = 1.3
QUESTION_EXTRA_S = 4.5
END_GAP_S = 2.6
FILM_SYL_PER_MIN = 180.0     # whole-film average at speed 0.88 (planning figure for prompts)


def speech_seconds(text: str, speed: float = 1.0) -> float:
    return len(words(text or "")) / (SPEECH_SYL_PER_MIN * (speed or 1.0)) * 60


def beat_seconds(b: dict, speed: float = 1.0) -> float:
    """Screen time of one beat as the engine builds it (calibrated; see SPEECH_SYL_PER_MIN)."""
    v = b.get("visual") or {}
    narr = b.get("narration") or ""
    if not narr.strip():
        return float(v.get("hold", 3.0))
    sp = float(b.get("speed", speed) or speed)
    extra = (float(v.get("think_seconds", 5.0)) + QUESTION_EXTRA_S if v.get("type") == "question"
             else END_GAP_S if v.get("type") == "end" else BEAT_GAP_S)
    return speech_seconds(narr, sp) + extra


def estimate_seconds(L: dict) -> float:
    speed = float((L.get("meta") or {}).get("speed", 1.0) or 1.0)
    return sum(beat_seconds(b, speed) for b in L.get("beats") or [])


def length_window(minutes) -> tuple[float, float]:
    """The accepted range in seconds for a [lo, hi] minutes target (the engine lint's tolerances: -10 % / +5 %)."""
    lo, hi = (float(minutes[0]), float(minutes[-1])) if isinstance(minutes, (list, tuple)) and minutes else (4.0, 6.0)
    return lo * 60 * 0.9, hi * 60 * 1.05

SPINE = ("ngay_xua", "cho_den_mot_ngay", "vi_vay", "cho_den_khi", "tu_do", "va_gio")
SPINE_VI = {"ngay_xua": "Ngày xưa / Mỗi ngày…", "cho_den_mot_ngay": "Cho đến một ngày…", "vi_vay": "Vì vậy… vì vậy…",
            "cho_den_khi": "Cho đến khi…", "tu_do": "Từ đó…", "va_gio": "Và giờ…"}
SETS = ("street", "office", "cafe", "room", "phone", "plain")
TRANSITIONS = ("whip", "zoom", "circle", "slide", "cut")
# names assumed from the plan (§2: vui, lo, ngạc nhiên, suy nghĩ, buồn; đứng thở, chớp mắt, nói, vẫy, chỉ, nhún vai,
# đi vào/ra, nhảy, ngồi). If the engine exposes its own lists, those win (see engine_vocab()).
EXPRESSIONS = ("neutral", "happy", "worried", "surprised", "thinking", "sad")
ACTIONS = ("idle", "blink", "talk", "wave", "point", "shrug", "walk_in", "walk_out", "jump", "sit")

PREVIEW = re.compile(r"đến cuối (clip|video|tập)|trong (clip|video) này|hôm nay (chúng ta|mình sẽ)|lát nữa mình|"
                     r"phần tiếp theo mình sẽ|chào (các bạn|mừng)|xin chào", re.I)
FILLER = re.compile(r"pha một tách trà|ngồi xuống cùng mình|trước khi bắt đầu", re.I)
EXTRA_CTA = re.compile(r"đăng ký|subscribe|bấm chuông|nhấn like|chia sẻ (video|clip)|lưu lại (video|clip)|gửi cho bạn bè", re.I)
NUMBER_WORD = re.compile(r"^(không|một|mốt|hai|ba|bốn|tư|năm|lăm|sáu|bảy|tám|chín|mười|mươi|trăm|nghìn|ngàn|triệu|tỷ|"
                         r"lẻ|linh|phẩy)$", re.I)
DIGITS = {"một", "mốt", "hai", "ba", "bốn", "tư", "năm", "lăm", "sáu", "bảy", "tám", "chín", "mười"}  # significant digits
MAGNITUDES = {"mươi", "trăm", "nghìn", "ngàn", "triệu", "tỷ", "phẩy"}
YEAR_START = {"một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười"}
# only numbers when they continue a number ("đầu tư", "Linh", "lẻ loi", "không có" are words)
CONTINUATION_ONLY = {"tư", "mốt", "lăm", "mươi", "lẻ", "linh", "không", "phẩy"}
CHOICE_LETTER = re.compile(r"^\s*\(?[A-Da-d]\s*[.):\-–]\s*")
BAD_GLYPHS = set("✓✔✗✘→←↑↓⟷↔★☆•●◆■▶►…") - {"…"}
LIKENESS_KEYS = ("photo", "image", "image_url", "likeness", "caricature")


# the look keys of vfactory/lesson/characters.py (DEFAULT_LOOK, HAIRS, OUTFITS, AGES); the engine's own lists win
LOOK_KEYS = ("skin", "hair", "hair_color", "shirt", "pants", "shoes", "outfit", "age", "glasses", "hat_color")
HAIRS = ("short", "bob", "long", "bun", "ponytail", "cap", "spiky", "bald", "non_la")
OUTFITS = ("tee", "shirt", "dress", "ao_dai", "jacket")
AGES = ("child", "adult", "older")


def engine_vocab() -> dict:
    """Expression/action/set/look names from the engine, when the sticker engine exposes them; else the plan's names."""
    vocab = {"expressions": EXPRESSIONS, "actions": ACTIONS, "sets": SETS, "transitions": TRANSITIONS,
             "icons": icon_keys(), "look_keys": LOOK_KEYS, "hairs": HAIRS, "outfits": OUTFITS, "ages": AGES}
    try:
        import importlib

        for mod in ("vfactory.lesson.sticker", "vfactory.lesson.characters", "vfactory.lesson.stage"):
            try:
                m = importlib.import_module(mod)
            except Exception:  # noqa: BLE001
                continue
            if getattr(m, "DEFAULT_LOOK", None):
                vocab["look_keys"] = tuple(m.DEFAULT_LOOK)
            for k, attr in (("expressions", "EXPRESSIONS"), ("actions", "ACTIONS"), ("sets", "SETS"),
                            ("transitions", "TRANSITIONS"), ("hairs", "HAIRS"), ("outfits", "OUTFITS"),
                            ("ages", "AGES")):
                v = getattr(m, attr, None)
                if v:
                    vocab[k] = tuple(v) if not isinstance(v, dict) else tuple(v)
    except Exception:  # noqa: BLE001
        pass
    return vocab


def icon_keys() -> tuple:
    """Icon names the engine can draw (vfactory.lesson.metaphors.ICONS, plus sticker props if the engine adds them)."""
    keys: set = set()
    import importlib

    for mod, attr in (("vfactory.lesson.metaphors", "ICONS"), ("vfactory.lesson.sticker", "PROPS"),
                      ("vfactory.lesson.stage", "_icons_everyday")):
        try:
            v = getattr(importlib.import_module(mod), attr, {}) or {}
            keys |= set(v() if callable(v) else v)
        except Exception:  # noqa: BLE001
            continue
    return tuple(sorted(keys))


def engine_knows_stage() -> bool:
    try:
        from vfactory.lesson import schema

        return "stage" in schema.VISUALS
    except Exception:  # noqa: BLE001
        return False


def stage_visuals(v: dict):
    """The `stage` pictures in a visual: itself, or the stage shots of a `shots` visual."""
    if v.get("type") == "stage":
        yield v
    elif v.get("type") == "shots":
        for sh in v.get("shots") or []:
            if isinstance(sh, dict) and sh.get("type") == "stage":
                yield sh


def _cue_in(cue: str, narration: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(cue.lower().strip()), narration.lower()))


def long_numbers(narration: str) -> list[str]:
    """Genuine long cardinal amounts spoken word by word: one quantity of >= 4 number words carrying >= 3 significant
    digits ("một nghìn bốn trăm ba mươi lăm", "một trăm sáu mươi ba nghìn"). Not counted: years after "năm"
    ("năm hai nghìn lẻ tám"), "năm" meaning year(s) ("mười năm", "ba năm"), ordinals ("lần thứ tư"), round amounts
    ("năm mươi lăm nghìn", "ba trăm sáu mươi triệu"), and words that only look like numbers ("đầu tư", "Linh")."""
    out = []
    for clause in re.split(r"[,.;:!?()\[\]\"“”…—–]+", (narration or "").lower()):
        toks = words(clause)
        n = len(toks)

        def isnum(i: int) -> bool:
            return 0 <= i < n and bool(NUMBER_WORD.match(toks[i]))

        run: list[str] = []
        runs: list[list[str]] = []
        i = 0
        while i < n:
            t = toks[i]
            prev_num = bool(run)
            if t == "thứ" and isnum(i + 1):  # an ordinal: skip "thứ tư", "thứ mười hai"
                if run:
                    runs.append(run)
                run = []
                i += 1
                while isnum(i) and toks[i] not in MAGNITUDES:
                    i += 1
                continue
            if t == "năm":
                nxt = toks[i + 1] if i + 1 < n else ""
                prev = run[-1] if run else ""
                if prev in ("mười", "mươi") or (prev in DIGITS and nxt not in MAGNITUDES) or \
                        (not prev_num and nxt in YEAR_START):
                    # "mười năm", "ba năm" (years) or "năm <year>": a unit/marker, and a year after it is not counted
                    if run:
                        runs.append(run)
                    run = []
                    i += 1
                    if nxt in YEAR_START:
                        while isnum(i):
                            i += 1
                    continue
            if NUMBER_WORD.match(t) and (t not in CONTINUATION_ONLY or (prev_num and (
                    t not in ("lẻ", "linh", "không", "phẩy") or isnum(i + 1)))):
                run.append(t)
            else:
                if run:
                    runs.append(run)
                run = []
            i += 1
        if run:
            runs.append(run)
        out += [" ".join(r) for r in runs if len(r) >= 4 and sum(1 for w in r if w in DIGITS) >= 3]
    return out


def luminance(hex_color: str) -> float | None:
    """Perceived lightness 0-1 of a #RRGGBB colour (Rec. 709 luma on the sRGB values); None if not a colour."""
    m = re.fullmatch(r"#?([0-9A-Fa-f]{6})", str(hex_color or "").strip())
    if not m:
        return None
    r, g, b = (int(m.group(1)[k:k + 2], 16) / 255 for k in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def spoken_share(text: str, narration: str) -> float:
    """How much of an on-screen line is in the narration (share of its words heard in the beat)."""
    tw = [w.lower() for w in words(text or "")]
    nw = {w.lower() for w in words(narration or "")}
    return sum(1 for w in tw if w in nw) / max(1, len(tw))


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            if not k.endswith("cue") and k not in ("type", "id", "icon", "set", "transition", "expression", "action",
                                                    "concept", "color", "who", "look", "hair", "skin"):
                yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def check_stage_visual(v: dict, b: dict, cast_ids: set, vocab: dict,
                       concepts: dict | None = None) -> tuple[list[str], list[str]]:
    """`concepts`: meta.concepts by id (a prop may give only `concept`: the engine draws that concept's icon)."""
    concepts = concepts or {}
    e, w = [], []
    bid = b.get("id")
    narr = b.get("narration", "")
    if v.get("set") not in vocab["sets"]:
        e.append(f"{bid}: stage 'set' must be one of {list(vocab['sets'])}, got {v.get('set')!r}")
    chars = v.get("characters", [])
    if not isinstance(chars, list):
        e.append(f"{bid}: stage 'characters' must be a list")
        chars = []
    if len(chars) > 3:
        w.append(f"{bid}: {len(chars)} characters on one stage: keep it to 1-3 so each reads at phone size")
    here = set()
    for i, c in enumerate(chars):
        cid = c.get("id")
        here.add(cid)
        if cid not in cast_ids:
            e.append(f"{bid}: character {i} id {cid!r} is not in meta.cast (register every character once)")
        x = c.get("x")
        if not isinstance(x, (int, float)) or not 0 <= x <= 1:
            e.append(f"{bid}: character {cid!r} needs x between 0 and 1 (fraction of frame width)")
        if c.get("look"):
            w.append(f"{bid}: character {cid!r} repeats a 'look' in the beat; looks belong in meta.cast only")
        if c.get("expression") and c["expression"] not in vocab["expressions"]:
            w.append(f"{bid}: expression {c['expression']!r} not in {list(vocab['expressions'])}")
        if c.get("action") and c["action"] not in vocab["actions"]:
            w.append(f"{bid}: action {c['action']!r} not in {list(vocab['actions'])}")
        for cu in c.get("cues", []) or []:
            if not cu.get("cue") or not _cue_in(cu["cue"], narr):
                e.append(f"{bid}: character {cid!r} cue {cu.get('cue')!r} is not a word in this beat's narration")
            if cu.get("expression") and cu["expression"] not in vocab["expressions"]:
                w.append(f"{bid}: cue expression {cu['expression']!r} not in {list(vocab['expressions'])}")
            if cu.get("action") and cu["action"] not in vocab["actions"]:
                w.append(f"{bid}: cue action {cu['action']!r} not in {list(vocab['actions'])}")
    icons = vocab.get("icons") or ()
    for p in v.get("props", []) or []:
        key = p.get("icon")
        if p.get("concept") and p["concept"] not in concepts:
            e.append(f"{bid}: prop concept {p['concept']!r} is not registered in meta.concepts")
        elif not key and p.get("concept"):
            key = concepts[p["concept"]].get("visual")  # the engine draws the registered concept's icon
        if not key:
            e.append(f"{bid}: every prop needs an 'icon' (or a 'concept' registered in meta.concepts)")
        elif icons and key not in icons:
            w.append(f"{bid}: prop icon {key!r} is not in the engine's icon set (it may not draw)")
        if p.get("cue") and not _cue_in(p["cue"], narr):
            e.append(f"{bid}: prop cue {p['cue']!r} is not a word in this beat's narration")
    for bub in ([v["bubble"]] if v.get("bubble") else []) + list(v.get("bubbles") or []):
        if bub.get("who") not in here:
            e.append(f"{bid}: bubble.who {bub.get('who')!r} is not a character on this stage")
        if bub.get("cue") and not _cue_in(bub["cue"], narr):
            e.append(f"{bid}: bubble cue {bub['cue']!r} is not a word in this beat's narration")
        if len(words(bub.get("text", ""))) > 10:
            w.append(f"{bid}: bubble text has {len(words(bub.get('text', '')))} words: ≤ 10 so it reads in time")
        if bub.get("text") and spoken_share(bub["text"], narr) < 0.7:
            w.append(f"{bid}: bubble {bub['text']!r} is not (roughly) in this beat's narration: bubbles are spoken "
                     "(the speaker's mouth moves on those words), so quote the narration's own words")
    if v.get("caption") and len(words(v["caption"])) > 12:
        w.append(f"{bid}: caption has {len(words(v['caption']))} words: on-screen text is the key phrase (≤ 12)")
    if v.get("transition") is not None and v["transition"] not in vocab["transitions"]:
        e.append(f"{bid}: transition must be one of {list(vocab['transitions'])}")
    if not chars and not v.get("props"):
        w.append(f"{bid}: an empty stage (no characters, no props)")
    return e, w


def normalize_lesson(L: dict) -> dict:
    """Aliases the engine does not read, mapped to the names it does (a copy): meta.cast[].name_tag -> tag."""
    import copy

    out = copy.deepcopy(L)
    for c in (out.get("meta") or {}).get("cast") or []:
        if isinstance(c, dict) and c.get("name_tag") and not c.get("tag"):
            c["tag"] = c["name_tag"]
    return out


def check_lesson(L: dict, *, research: dict | None = None, end_narration: str | None = None,
                 brief: dict | None = None) -> tuple[list[str], list[str]]:
    """Series rules + stage contract. Returns (errors, warnings).

    `brief`: the owner's production constraints (pipeline.Pipeline.brief()): target_minutes, aspect, kicker, voice,
    end_narration, end_ask; keys listed in brief["owner_set"] were set by the owner and are enforced as errors, the
    others (defaults) as warnings."""
    e: list[str] = []
    w: list[str] = []
    meta = L.get("meta") or {}
    beats = L.get("beats") or []
    if not beats:
        return ["lesson has no beats"], w
    vocab = engine_vocab()
    brief = brief or {}
    owner = set(brief.get("owner_set") or ())

    def must(key: str, msg: str) -> None:
        (e if key in owner else w).append(msg + (" (the owner's brief)" if key in owner else " (series default)"))

    if end_narration is None:
        end_narration = brief.get("end_narration")

    # -- meta
    if meta.get("style") != "sticker":
        e.append('meta.style must be "sticker"')
    if meta.get("lang") != "vi":
        e.append('meta.lang must be "vi"')
    if meta.get("aspect", "16:9") not in ("16:9", "9:16"):
        w.append(f"meta.aspect {meta.get('aspect')!r}: the sticker series is 16:9 (9:16 for Shorts)")
    # what the owner set is binding (the defaults are only defaults: the length window still applies below)
    if "aspect" in owner and meta.get("aspect", "16:9") != brief["aspect"]:
        must("aspect", f"meta.aspect is {meta.get('aspect')!r} but the brief asks for {brief['aspect']!r}")
    if "voice" in owner and meta.get("voice") != brief["voice"]:
        must("voice", f"meta.voice is {meta.get('voice')!r} but the brief asks for {brief['voice']!r}")
    if "target_minutes" in owner and list(meta.get("target_minutes") or []) != list(brief["target_minutes"]):
        must("target_minutes", f"meta.target_minutes is {meta.get('target_minutes')!r} but the brief asks for "
                               f"{list(brief['target_minutes'])!r}")
    look = meta.get("look") or {}
    if meta.get("style") == "sticker" and isinstance(look, dict) and look.get("secondary_color"):
        lum = luminance(look["secondary_color"])
        if lum is None or lum < 0.5:
            e.append(f"meta.look.secondary_color {look['secondary_color']!r} is the page background and it is dark "
                     f"(luminance {0 if lum is None else lum:.2f} < 0.5): a sticker film sits on light paper. Remove "
                     "meta.look (the sticker tokens apply) or give a light colour")
    cast = meta.get("cast")
    cast_ids: set = set()
    concepts = {c["id"]: c for c in meta.get("concepts") or [] if isinstance(c, dict) and c.get("id")}
    if not isinstance(cast, list) or not cast:
        e.append("meta.cast must register every character once: [{id, name, look, role}]")
        cast = []
    for c in cast:
        if not isinstance(c, dict) or not c.get("id") or not c.get("name") or not isinstance(c.get("look"), dict):
            e.append(f"meta.cast entry needs id, name, look: {str(c)[:80]}")
            continue
        if c["id"] in cast_ids:
            e.append(f"meta.cast: duplicate id {c['id']!r}")
        cast_ids.add(c["id"])
        lk = c.get("look") or {}
        for k, val in lk.items():
            if k in LIKENESS_KEYS:
                continue
            if k not in vocab["look_keys"]:
                e.append(f"meta.cast {c['id']!r}: unknown look key {k!r} (one of {list(vocab['look_keys'])})")
        for k, allowed in (("hair", "hairs"), ("outfit", "outfits"), ("age", "ages")):
            if lk.get(k) is not None and lk[k] not in vocab[allowed]:
                e.append(f"meta.cast {c['id']!r}: look.{k} {lk[k]!r} is not one of {list(vocab[allowed])}")
        if c.get("name_tag") and not c.get("tag"):
            w.append(f"meta.cast {c['id']!r}: 'name_tag' is an alias; the engine reads 'tag' (renamed on save)")
        if c.get("real"):
            if not (c.get("tag") or c.get("name_tag")):
                e.append(f"meta.cast {c['id']!r} is a real person: give a 'tag' (a generic figure plus a name tag)")
            for k in LIKENESS_KEYS:
                if k in (c.get("look") or {}):
                    e.append(f"meta.cast {c['id']!r}: no likeness of real people ('{k}' in look)")
    if not any(c.get("role") == "protagonist" for c in cast if isinstance(c, dict)):
        w.append("meta.cast has no role 'protagonist'")

    # -- likeness anywhere
    def scan(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in LIKENESS_KEYS and isinstance(v, str):
                    e.append(f"{path}.{k}: no photos/likenesses of real people in this series")
                scan(v, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                scan(v, f"{path}[{i}]")
    scan(beats, "beats")

    # -- beats
    ids = [b.get("id") for b in beats]
    spine_seen = []
    speed = float(meta.get("speed", 1.0) or 1.0)
    t = 0.0
    inciting_at = None
    all_narr = " ".join(b.get("narration", "") for b in beats)
    for b in beats:
        bid = b.get("id")
        narr = b.get("narration", "") or ""
        v = b.get("visual") or {}
        if b.get("act") not in ACTS:
            e.append(f"{bid}: act {b.get('act')!r} must be one of {list(ACTS)}")
        sp = b.get("spine")
        if sp not in SPINE:
            e.append(f"{bid}: 'spine' must be one of {list(SPINE)} (the Pixar spine act this beat belongs to)")
        else:
            spine_seen.append(sp)
            if sp == "cho_den_mot_ngay" and inciting_at is None:
                inciting_at = t
        t += beat_seconds(b, speed)
        if re.search(r"\d", narr) and not b.get("allow_digits"):
            e.append(f"{bid}: digits in narration; write numbers as spoken Vietnamese words (\"hai mươi triệu\")")
        for num in long_numbers(narr)[:1]:
            w.append(f"{bid}: a long number spoken word by word (\"{num}\"); round it in speech (\"hơn chín nghìn\") "
                     "and put the exact figure on screen")
        if PREVIEW.search(narr):
            e.append(f"{bid}: no previews or greetings (\"{PREVIEW.search(narr).group(0)}\"): start inside the story")
        if FILLER.search(narr):
            e.append(f"{bid}: filler line (\"{FILLER.search(narr).group(0)}\") is banned in this series")
        if v.get("type") != "end" and EXTRA_CTA.search(narr):
            e.append(f"{bid}: a call to action outside the end card (\"{EXTRA_CTA.search(narr).group(0)}\"): one CTA only")
        for s in _strings(v):
            bad = sorted({ch for ch in s if ch in BAD_GLYPHS})
            if bad:
                e.append(f"{bid}: on-screen text uses glyphs the fonts may not draw {bad}: use words")
        for sv in stage_visuals(v):
            ee, ww = check_stage_visual(sv, b, cast_ids, vocab, concepts)
            e += ee
            w += ww
        if b.get("certainty") in ("disputed", "attributed", "estimate") and not b.get("sources"):
            e.append(f"{bid}: certainty {b['certainty']} needs the source ids it rests on")
        if b.get("certainty") in ("disputed", "attributed") and narr.strip() and not HEDGE_RE.search(narr):
            e.append(f"{bid}: certainty {b['certainty']} but the narration says it as fact: hedge it out loud "
                     "(\"theo lời…\", \"được cho là\", \"khoảng\")")
        for sc in [v] + [x for x in (v.get("shots") or []) if isinstance(x, dict)] if v.get("type") == "shots" else [v]:
            if sc.get("type") == "scenario":
                for k, bar in enumerate(sc.get("bars") or []):
                    lab = bar.get("label", k) if isinstance(bar, dict) else k
                    vals = {f: (bar.get(f) if isinstance(bar, dict) else None) for f in ("before", "after")}
                    for f, val in vals.items():
                        if isinstance(val, bool) or not isinstance(val, (int, float)):
                            e.append(f"{bid}: scenario bar {lab!r} needs a number for '{f}' (got {val!r}): every bar "
                                     "shows its before AND its after value")
                    if isinstance(vals["before"], (int, float)) and not isinstance(vals["before"], bool) \
                            and vals["before"] <= 0:
                        w.append(f"{bid}: scenario bar {lab!r} starts at {vals['before']}: an empty bar hides the "
                                 "before state; show what it was")
                    if isinstance(bar, dict) and bar.get("delta"):
                        w.append(f"{bid}: scenario bar {lab!r} has 'delta': the series shows before and after only")
    # a cold open (the hook, the open loop, the title sting) may come before "Ngày xưa"; from there the spine is in order
    first_normal = spine_seen.index("ngay_xua") if "ngay_xua" in spine_seen else 0
    order = [SPINE.index(s) for s in spine_seen[first_normal:]]
    if order and order != sorted(order):
        e.append("beats must follow the spine in order: " + " → ".join(SPINE_VI[s] for s in SPINE))
    missing = [SPINE_VI[s] for s in SPINE if s not in spine_seen]
    if missing:
        e.append(f"the Pixar spine is missing: {missing}")
    if inciting_at is not None and inciting_at > 12:
        w.append(f"'Cho đến một ngày…' starts at ~{inciting_at:.0f}s: the inciting incident should land in the first ~10 s")
    if len(set(ids)) != len(ids):
        e.append("beat ids must be unique")

    for b in beats:
        v = b.get("visual") or {}
        if v.get("type") == "title" and brief.get("kicker") and v.get("kicker") != brief["kicker"]:
            must("kicker", f"{b.get('id')}: title sting kicker should be \"{brief['kicker']}\"")
    # -- fiction label: once
    n_label = len(re.findall(r"hư cấu", all_narr, re.I))
    if n_label == 0:
        e.append("label the fictional thread once in narration (\"nhân vật hư cấu, chuyện có thật\")")
    elif n_label > 2:
        w.append(f"'hư cấu' said {n_label} times: once is enough")

    # -- end card: exactly one, last, one CTA
    ends = [b for b in beats if (b.get("visual") or {}).get("type") == "end"]
    if len(ends) != 1 or (beats[-1].get("visual") or {}).get("type") != "end":
        e.append("exactly one end card, as the last beat (visual type 'end')")
    else:
        end = beats[-1]
        ev = end["visual"]
        if end.get("act") != "close":
            e.append(f"{end.get('id')}: the end card's act is 'close'")
        if "cta" in ev:
            e.append(f"{end.get('id')}: no 'cta' on the end card: the one call to action is the 'ask' (a comment)")
        if not ev.get("ask"):
            e.append(f"{end.get('id')}: the end card needs 'ask' (the one question viewers answer in the comments)")
        for k in ("ask_cue", "sources_cue"):
            if ev.get(k) and not _cue_in(ev[k], end.get("narration", "")):
                e.append(f"{end.get('id')}: {k} {ev[k]!r} is not in the end narration")
        if end_narration and end.get("narration", "").strip() != end_narration.strip():
            (e if "end_narration" in owner else w).append(
                f"{end.get('id')}: end narration differs from the sign-off line (a cached voice take; use it word for "
                f"word): \"{end_narration}\"")
        if brief.get("end_ask") and ev.get("ask") != brief["end_ask"]:
            must("end_ask", f"{end.get('id')}: end card ask should be \"{brief['end_ask']}\"")
        if brief.get("end_ask_hint") and ev.get("ask_hint") != brief["end_ask_hint"]:
            must("end_ask_hint", f"{end.get('id')}: end card ask_hint should be \"{brief['end_ask_hint']}\"")
        if brief.get("kicker") and ev.get("kicker") != brief["kicker"]:
            must("kicker", f"{end.get('id')}: end card kicker should be \"{brief['kicker']}\"")
    # -- retrieval question and recap (the learning-science spine survives the story format)
    acts = [b.get("act") for b in beats]
    for need in ("hook", "misconception", "question"):
        if need not in acts:
            (e if need == "hook" else w).append(f"no '{need}' beat")
    q = [b for b in beats if (b.get("visual") or {}).get("type") == "question"]
    for b in q:
        if len(b["visual"].get("choices", [])) != 3:
            w.append(f"{b.get('id')}: the retrieval question has 3 choices in this series")
        for c in b["visual"].get("choices") or []:
            if isinstance(c, str) and CHOICE_LETTER.match(c):
                e.append(f"{b.get('id')}: choice {c!r} starts with its letter: the engine draws the A/B/C badges, "
                         "write the bare choice")
    # -- boards: the first beat of a board opens on the whole board (then the camera travels)
    seen_boards: set = set()
    for b in beats:
        v = b.get("visual") or {}
        if v.get("type") != "board":
            continue
        key = v.get("board_id") or f"#{b.get('id')}"
        if key not in seen_boards:
            seen_boards.add(key)
            if v.get("start") != "overview" and not v.get("overview"):
                w.append(f"{b.get('id')}: the first beat of board {key!r} should open on the overview "
                         "(\"start\": \"overview\") so the viewer sees the whole map before the camera moves in")
    # -- length (calibrated estimate; the owner's window when given, else meta.target_minutes)
    target = (brief["target_minutes"] if "target_minutes" in owner else None) or meta.get("target_minutes") \
        or brief.get("target_minutes")
    if target:
        lo, hi = length_window(target)
        est = estimate_seconds(L)
        if est > hi:
            e.append(f"estimated length {est / 60:.1f} min (~{FILM_SYL_PER_MIN:.0f} syllables/min with pauses) is over "
                     f"the {target[0]}-{target[-1]} min target: cut words, not scenes")
        elif est < lo:
            w.append(f"estimated length {est / 60:.1f} min is under the {target[0]}-{target[-1]} min target")

    # -- sources must come from the research pack (no invented sources)
    if research is not None:
        rs = {s.get("id") for s in research.get("sources", [])}
        for s in L.get("sources", []):
            if s.get("id") not in rs:
                e.append(f"source {s.get('id')!r} is not in the research pack: use only researched sources "
                         "(or add it to research.json after checking it)")
        cut = {c.get("id") for c in research.get("claims", []) if c.get("use") == "cut"}
        for b in beats:
            for cid in b.get("claims", []) or []:
                if cid in cut:
                    e.append(f"{b.get('id')}: uses claim {cid!r} that research marked 'cut'")

    # -- packaging draft
    yt = meta.get("youtube") or {}
    if yt.get("title") and len(yt["title"]) > 65:
        w.append(f"meta.youtube.title is {len(yt['title'])} chars (≤ 65)")
    return e, w


def check_package(p: dict, lesson: dict | None = None) -> list[str]:
    e = []
    title = p.get("title", "")
    if len(title) > 65:
        e.append(f"title is {len(title)} characters: at most 65")
    tt = p.get("thumbnail_text", "")
    if tt and title and tt.strip().lower() == title.strip().lower():
        e.append("thumbnail_text repeats the title: they must complement each other")
    if tt and len(words(tt)) > 9:
        e.append(f"thumbnail_text has {len(words(tt))} words: ≤ 9, readable at 320 px")
    if not 12 <= len(p.get("tags", [])) <= 15:
        e.append(f"{len(p.get('tags', []))} tags: give 12-15")
    d = p.get("description", "")
    if "nguồn" not in d.lower():
        e.append("the description must list the sources (a 'Nguồn:' section)")
    if "hư cấu" not in d.lower():
        e.append("the description must say the protagonist is fictional (\"nhân vật hư cấu\")")
    if lesson:
        for s in lesson.get("sources", []):
            url = s.get("url")
            if url and url not in d and s.get("id") not in d and not any(
                    tok in d for tok in re.findall(r"[A-Z][\w.]+", s.get("cite", ""))[:2]):
                e.append(f"source {s.get('id')!r} is not mentioned in the description")
    if EXTRA_CTA.search(title + " " + tt):
        e.append("no call to action in the title or thumbnail")
    return e
