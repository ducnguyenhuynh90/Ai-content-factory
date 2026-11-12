"""Deterministic checks for an agent-written lesson: the `stage` contract (docs/plans/story-sticker-agent.md §3) and the
series rules the human writers learned the hard way (BRIEF_frameworks / BRIEF_book_episodes_v2 / the gate briefs).

These run before `python -m vfactory.lesson lint` and do not depend on the engine knowing the sticker style, so a lesson
is checked even while the engine work is still landing. Errors go back to the model in the repair loop; warnings are
editor's notes (also shown to the critique stage).
"""

from __future__ import annotations

import re

try:  # read-only reuse of the engine's word counter; fall back if the engine module is mid-edit
    from vfactory.lesson.schema import ACTS, est_seconds, words
except Exception:  # noqa: BLE001
    ACTS = ("hook", "context", "story", "misconception", "complication", "turn", "principle", "example", "question",
            "recap", "close")

    def words(text: str) -> list[str]:
        return re.findall(r"[\w'’£$€%-]+", text)

    def est_seconds(text: str, speed: float = 1.0, lang: str = "en") -> float:
        return len(words(text)) / ((270.0 if lang == "vi" else 150.0) * speed) * 60

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
BAD_GLYPHS = set("✓✔✗✘→←↑↓⟷↔★☆•●◆■▶►…") - {"…"}
LIKENESS_KEYS = ("photo", "image", "image_url", "likeness", "caricature")


def engine_vocab() -> dict:
    """Expression/action/set names from the engine, when the sticker engine exposes them; else the plan's names."""
    vocab = {"expressions": EXPRESSIONS, "actions": ACTIONS, "sets": SETS, "transitions": TRANSITIONS,
             "icons": icon_keys()}
    try:
        import importlib

        for mod in ("vfactory.lesson.sticker", "vfactory.lesson.characters", "vfactory.lesson.stage"):
            try:
                m = importlib.import_module(mod)
            except Exception:  # noqa: BLE001
                continue
            for k, attr in (("expressions", "EXPRESSIONS"), ("actions", "ACTIONS"), ("sets", "SETS"),
                            ("transitions", "TRANSITIONS")):
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


def check_stage_visual(v: dict, b: dict, cast_ids: set, vocab: dict) -> tuple[list[str], list[str]]:
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
        if not p.get("icon"):
            e.append(f"{bid}: every prop needs an 'icon'")
        elif icons and p["icon"] not in icons:
            w.append(f"{bid}: prop icon {p['icon']!r} is not in the engine's icon set (it may not draw)")
        if p.get("cue") and not _cue_in(p["cue"], narr):
            e.append(f"{bid}: prop cue {p['cue']!r} is not a word in this beat's narration")
    for bub in ([v["bubble"]] if v.get("bubble") else []) + list(v.get("bubbles") or []):
        if bub.get("who") not in here:
            e.append(f"{bid}: bubble.who {bub.get('who')!r} is not a character on this stage")
        if bub.get("cue") and not _cue_in(bub["cue"], narr):
            e.append(f"{bid}: bubble cue {bub['cue']!r} is not a word in this beat's narration")
        if len(words(bub.get("text", ""))) > 10:
            w.append(f"{bid}: bubble text has {len(words(bub.get('text', '')))} words: ≤ 10 so it reads in time")
    if v.get("caption") and len(words(v["caption"])) > 12:
        w.append(f"{bid}: caption has {len(words(v['caption']))} words: on-screen text is the key phrase (≤ 12)")
    if v.get("transition") is not None and v["transition"] not in vocab["transitions"]:
        e.append(f"{bid}: transition must be one of {list(vocab['transitions'])}")
    if not chars and not v.get("props"):
        w.append(f"{bid}: an empty stage (no characters, no props)")
    return e, w


def check_lesson(L: dict, *, research: dict | None = None, end_narration: str | None = None) -> tuple[list[str], list[str]]:
    """Series rules + stage contract. Returns (errors, warnings)."""
    e: list[str] = []
    w: list[str] = []
    meta = L.get("meta") or {}
    beats = L.get("beats") or []
    if not beats:
        return ["lesson has no beats"], w
    vocab = engine_vocab()

    # -- meta
    if meta.get("style") != "sticker":
        e.append('meta.style must be "sticker"')
    if meta.get("lang") != "vi":
        e.append('meta.lang must be "vi"')
    if meta.get("aspect", "16:9") not in ("16:9", "9:16"):
        w.append(f"meta.aspect {meta.get('aspect')!r}: the sticker series is 16:9 (9:16 for Shorts)")
    cast = meta.get("cast")
    cast_ids: set = set()
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
        if c.get("real"):
            if not c.get("name_tag"):
                e.append(f"meta.cast {c['id']!r} is a real person: give a 'name_tag' (a generic figure plus a name tag)")
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
    lang = meta.get("lang", "vi")
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
        t += est_seconds(narr, speed, lang) + 1.1 if narr.strip() else float(v.get("hold", 3.0))
        if re.search(r"\d", narr) and not b.get("allow_digits"):
            e.append(f"{bid}: digits in narration; write numbers as spoken Vietnamese words (\"hai mươi triệu\")")
        run = 0
        for tok in words(narr.lower()):
            run = run + 1 if NUMBER_WORD.match(tok) else 0
            if run >= 6:
                w.append(f"{bid}: a long number spoken word by word; round it in speech (\"hơn chín nghìn\") and "
                         "put the exact figure on screen")
                break
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
            ee, ww = check_stage_visual(sv, b, cast_ids, vocab)
            e += ee
            w += ww
        if b.get("certainty") in ("disputed", "attributed", "estimate") and not b.get("sources"):
            e.append(f"{bid}: certainty {b['certainty']} needs the source ids it rests on")
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
            w.append(f"{end.get('id')}: end narration differs from the series line (a cached voice take): "
                     f"\"{end_narration}\"")
    # -- retrieval question and recap (the learning-science spine survives the story format)
    acts = [b.get("act") for b in beats]
    for need in ("hook", "misconception", "question"):
        if need not in acts:
            (e if need == "hook" else w).append(f"no '{need}' beat")
    q = [b for b in beats if (b.get("visual") or {}).get("type") == "question"]
    for b in q:
        if len(b["visual"].get("choices", [])) != 3:
            w.append(f"{b.get('id')}: the retrieval question has 3 choices in this series")

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
