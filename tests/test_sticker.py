"""The sticker look, rigged characters, the `stage` scene, beat transitions and the cast registry
(docs/plans/story-sticker-agent.md §2-3)."""

import copy
import json
import re
from pathlib import Path

import pytest

from vfactory.lesson import build, characters as C, gate, scenes, schema, stage, sticker

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "docs" / "examples" / "sticker-check.lesson.json"
BRAND = {"primary_color": "#E8B06A", "secondary_color": "#12100E", "font": "Inter"}
CAST = [{"id": "linh", "name": "Linh", "tag": "Linh · 27", "look": {"hair": "bob", "shirt": "#E77A5F"}},
        {"id": "tung", "name": "Anh Tùng", "look": {"hair": "cap", "outfit": "jacket", "shirt": "#7DB892"}}]
STAGE = {"type": "stage", "set": "cafe", "caption": "Quán quen · 8 giờ",
         "characters": [{"id": "linh", "x": 0.3, "expression": "worried", "action": "idle",
                         "cues": [{"cue": "nhưng", "expression": "surprised", "action": "jump"}]},
                        {"id": "tung", "x": 0.7, "action": "talk", "cues": [{"cue": "vẫy", "action": "wave"}]}],
         "props": [{"icon": "phone", "x": 0.5, "y": 0.3, "cue": "điện thoại"}],
         "bubble": {"who": "linh", "text": "Sao lại đắt thế?", "cue": "sao"}}


def look(style="sticker", w=1920, h=1080, cast=CAST):
    return scenes.Look({} if style == "sticker" else BRAND, w, h, "vi", None, style=style, cast=cast)


def cue_of(table):
    return lambda w, d, after=None: table.get(w, d)


def words(text, t0=0.5, step=0.25):
    return [{"word": w, "start": round(t0 + i * step, 3), "end": round(t0 + i * step + 0.2, 3)} for i, w in enumerate(text.split())]


def tween_spans(tweens):
    """(selector, prop) -> [(start, end)] of every fromTo."""
    out = {}
    for t in tweens:
        m = re.match(r'tl\.fromTo\("([^"]+)", \{([^}]*)\}, \{(.*)\}, ([\d.]+)\);$', t)
        if not m:
            continue
        sel, frm, to, at = m.group(1), m.group(2), m.group(3), float(m.group(4))
        d = float(re.search(r"duration: ([\d.]+)", to).group(1))
        for prop in re.findall(r"(\w+):", frm):
            if prop in ("svgOrigin", "transformOrigin"):
                continue
            out.setdefault((sel, prop), []).append((at, at + d))
    return out


def lum(h):
    r, g, b = (c / 255 for c in sticker.hex_rgb(h))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- 1. the sticker look

def test_sticker_palette_reads_on_cream_and_dark_stays_default():
    L = look()
    assert L.style == "sticker" and L.bg == sticker.PALETTE["bg"] and L.serif == L.sans == "'Inter'"
    assert contrast(L.ink, L.bg) >= 7 and contrast(L.muted, L.bg) >= 4.5
    for c in (L.colors["a"], L.colors["b"]):  # concept colours: large text only (everything is >= 36 px)
        assert contrast(c, L.bg) >= 3.0
    assert len(sticker.PASTELS) >= 4
    D = scenes.Look(BRAND, 1440, 1080, "vi")
    assert D.style == "dark" and D.bg == "#12100E" and D.serif == "'EB Garamond'" and D.muted == "#9A9388"


def test_dark_scenes_unchanged_and_sticker_scenes_are_stickers():
    v = {"type": "icon", "icon": "pot", "kicker": "Một nồi", "line": "Ninh từ xương"}
    dark = scenes.scene_file(scenes.Look(BRAND, 1440, 1080, "vi"), "b1", v, 5.0, cue_of({}), 4.0, last=False)
    assert "-tx" not in dark and 'filter: "blur(8px)", duration: 0.22' in dark and "text-shadow" not in dark
    st = scenes.scene_file(look(), "b1", v, 5.0, cue_of({}), 4.0, last=False)
    assert "drop-shadow(" in st and "text-shadow" in st and 'fill-opacity="0.15"' not in st
    for html in (dark, st):
        assert not re.search(r"font-weight[:=]\s*\"?700", html)


def test_stickerize_fills_line_art_but_not_washes():
    out = sticker.stickerize('<path fill="#D2643F" fill-opacity="0.15"/><circle fill="#2E2A35" fill-opacity="0.04"/>')
    assert 'fill-opacity="0.15"' not in out and re.search(r'fill="#[0-9A-F]{6}"/><circle fill="#2E2A35" fill-opacity="0.04"', out)


def test_paper_texture_is_written(tmp_path):
    from PIL import Image

    p = sticker.paper_png(tmp_path / "paper.png", size=128)
    im = Image.open(p)
    assert im.mode == "RGBA" and im.size == (128, 128)


# ---------------------------------------------------------------- 2. rigged characters

@pytest.mark.parametrize("hair", C.HAIRS)
def test_every_hair_style_draws_a_full_rig(hair):
    svg = C.rig_svg("x1", {"hair": hair, "outfit": "ao_dai" if hair == "long" else "tee", "glasses": hair == "bald"})
    for part in ("pose", "stool", "legL", "legR", "br", "head", "hb", "ey", "mx", "mt", "armL", "armR", "foreL", "foreR"):
        assert f'id="x1-{part}"' in svg, part
    for e in C.EXPRESSIONS:
        assert f'id="x1-ey-{e}"' in svg and f'id="x1-mo-{e}"' in svg and f'id="x1-bw-{e}"' in svg
    ids = re.findall(r'id="([^"]+)"', svg)
    assert len(ids) == len(set(ids))


def test_variety_of_people_and_bad_looks_are_named():
    for lk in ({"age": "child", "hair": "spiky"}, {"age": "older", "hair": "bald"}, {"hair": "non_la", "outfit": "ao_dai"},
               {"hair": "bun", "outfit": "dress"}, {"hair": "ponytail", "outfit": "shirt"}):
        assert C.look_problems(lk) == [] and C.rig_svg("p", lk)
    assert C.norm_look({"age": "older"})["hair_color"] == "#B9B4AE"
    assert stage.char_scale(look(), {"age": "child"}) < stage.char_scale(look(), {})
    probs = C.look_problems({"hair": "mohawk", "skin": "pink", "hat": 1})
    assert len(probs) == 3


def test_keys_never_overlap_on_one_property():
    K = C.Keys()
    K.add("#a", "rotation", 1.0, 30, 0.5)
    K.add("#a", "rotation", 1.2, -30, 0.5)  # starts inside the first: waits for it
    K.add("#a", "rotation", 3.0, 0, 0.3)
    spans = tween_spans(K.tweens())[("#a", "rotation")]
    assert all(b0 >= a1 - 1e-6 for (a0, a1), (b0, b1) in zip(spans, spans[1:]))


def _chor(actions, ws=None, **kw):
    events = [{"t": 0.0, "expression": "neutral", "action": "idle"}] + [{"t": t, "action": a, **extra} for t, a, extra in actions]
    tw, K, xt = C.choreograph("c1", {"id": "c"}, x_px=600, scale=1.7, W=1920, dur=10, events=events, words=ws or [],
                              talk_spans=kw.get("spans", []), speech_end=9, partner_side=1)
    return tw, K, xt


def test_every_action_moves_the_right_parts():
    tw, K, xt = _chor([(0.5, "wave", {}), (2.6, "point", {}), (4.6, "shrug", {}), (6.2, "nod", {}), (7.4, "facepalm", {})])
    sp = tween_spans(tw)
    assert len(sp[("#c1-foreR", "rotation")]) >= 4  # the forearm waves
    assert ("#c1-head", "y") in sp and ("#c1-armL", "rotation") in sp
    assert any(abs(K.value_at("#c1-armR", "rotation", t) - 150) < 1e-6 for t in (7.9, 8.2))  # hand to face
    tw, K, xt = _chor([(1.0, "sit", {}), (4.0, "jump", {}), (6.0, "walk_out", {})])
    sp = tween_spans(tw)
    assert K.value_at("#c1-pose", "y", 2.0) == 30 and K.value_at("#c1-stool", "opacity", 2.0) == 1
    assert K.value_at("#c1-pose", "y", 5.0) == 0  # jumping stands up first
    assert ("#c1-mv", "y") in sp and ("#c1-sh", "scaleX") in sp
    assert K.value_at("#c1-mv", "x", 9.9) < -600  # walked off the left edge
    tw, K, xt = _chor([(1.0, "think", {})])
    assert K.value_at("#c1-armR", "rotation", 2.0) == 80
    assert any("#c1-br" in t and "repeat" in t for t in tw) and ("#c1-ey", "scaleY") in tween_spans(tw)  # breathe, blink


def test_walk_in_starts_off_screen_and_cue_x_walks_there():
    events = [{"t": 0.0, "action": "walk_in"}, {"t": 5.0, "x": 1200}]
    tw, K, xt = C.choreograph("w", {}, x_px=600, scale=1.7, W=1920, dur=9, events=events, words=[], talk_spans=[], speech_end=8)
    assert K.init[("#w-mv", "x")] < -600 and abs(K.value_at("#w-mv", "x", 3.0)) < 1e-6
    assert abs(K.value_at("#w-mv", "x", 8.5) - 600) < 1e-6 and K.value_at("#w-legL", "rotation", 8.9) == 0


def test_talk_mouth_opens_on_every_spoken_word():
    ws = words("tháng này lỗ rồi anh ơi", t0=1.0)
    tw, K, _ = _chor([], ws=ws, spans=[(1.0, 2.5)])
    opens = sorted(a for (sel, prop), spans in tween_spans(tw).items() if sel == "#c1-mt" and prop == "scaleY" for a, _ in spans)
    for w in ws:
        assert any(abs(o - w["start"]) < 0.02 for o in opens), w
    assert K.value_at("#c1-mt", "opacity", 1.5) == 1 and K.value_at("#c1-mx", "opacity", 3.0) == 1


def test_bubble_words_are_found_in_the_narration():
    ws = words("Linh thở dài: tháng này lỗ rồi anh ơi.", t0=0.4)
    a, b = stage.speech_span("Tháng này lỗ rồi anh ơi!", ws, 1.0)
    assert a == ws[3]["start"] and b == ws[-1]["end"]
    a, b = stage.speech_span("Một câu không có trong lời kể", ws, 2.0)  # not spoken: its own length from its cue
    assert a == pytest.approx(2.1) and b > a + 1.5


# ---------------------------------------------------------------- 3. the stage scene

@pytest.mark.parametrize("set_name", stage.SETS)
@pytest.mark.parametrize("wh", [(1920, 1080), (1440, 1080), (1080, 1920)])
def test_stage_renders_every_set_and_aspect(set_name, wh):
    L = look(w=wh[0], h=wh[1])
    v = {**copy.deepcopy(STAGE), "set": set_name, "_words": words("nhưng anh vẫy tay rồi cầm điện thoại hỏi sao lại đắt thế")}
    html = scenes.scene_file(L, "s1", v, 7.0, cue_of({"nhưng": 0.8, "vẫy": 1.5, "điện thoại": 2.4, "sao": 3.0}), 6.4, last=False,
                             tr_in="slide", tr_out="whip")
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1][:5]
    assert all(x >= 36 for x in (int(s) for s in re.findall(r'font-size(?::\s*|=")(\d+)', html)))
    for part in ("s1-linh-mv", "s1-tung-mv", "s1-b0", "s1-p0", "s1-cap", "s1-tx", "s1-set"):
        assert f'id="{part}"' in html, part
    assert "Sao lại đắt thế?" in html and "s1-stk" in html


def test_stage_tags_first_appearance_and_real_people():
    cast = CAST + [{"id": "musk", "name": "Elon Musk", "real": True, "look": {"hair": "short"}}]
    vis = [{"type": "stage", "characters": [{"id": "linh"}]},
           {"type": "shots", "shots": [{"type": "stage", "characters": [{"id": "linh"}, {"id": "musk"}]}]}]
    vis = stage.prepare(vis, cast)
    assert vis[0]["_tags"] == ["linh"] and vis[1]["shots"][0]["_tags"] == ["musk"]
    L = look(cast=cast)
    m, _, _ = stage.stage(L, "s9", {"type": "stage", "characters": [{"id": "linh"}, {"id": "musk"}], "_tags": []}, 5.0, cue_of({}))
    assert "Elon Musk" in m and "Linh · 27" not in m  # a real person always carries a name tag; Linh was introduced


def test_set_lettering_steps_back_under_a_bubble():
    L = look()
    v = {"type": "stage", "set": "cafe", "characters": [{"id": "linh", "x": 0.3}, {"id": "tung", "x": 0.68}],
         "bubble": {"who": "tung", "text": "Đơn giản vậy thôi.", "cue": "đơn"}}
    _, _, tw = stage.stage(L, "s4", v, 6.0, cue_of({"đơn": 2.0}))
    assert any(t.startswith('tl.fromTo("#s4-z0", {opacity: 1') for t in tw)


def test_stage_inside_shots_gets_its_own_word_clock():
    L = look()
    v = {"type": "shots", "_words": words("một hai ba bốn năm sáu bảy tám", t0=0.5, step=0.5), "shots": [
        {"type": "stage", "characters": [{"id": "linh", "action": "talk"}]},
        {"type": "stage", "cue": "năm", "transition": "cut", "characters": [{"id": "tung", "action": "talk"}]}]}
    html = scenes.scene_file(L, "s5", v, 5.0, lambda w, d, after=None: {"năm": 2.5}.get(w, d), 4.6, last=False)
    assert 'id="s5s1-tung-mt"' in html and 'tl.fromTo("#s5s1-shot", {opacity: 0}' in html


# ---------------------------------------------------------------- 4. transitions

def test_transitions_default_and_explicit():
    beats = [{"visual": {}}, {"visual": {}}, {"visual": {}}, {"transition": "zoom", "visual": {}}, {"visual": {"transition": "circle"}}]
    assert [scenes.transition_of(b, i, "sticker") for i, b in enumerate(beats)] == [None, "slide", "whip", "zoom", "circle"]
    assert [scenes.transition_of(b, i, "dark") for i, b in enumerate(beats)] == [None, None, None, "zoom", "circle"]
    L = look()
    for kind in scenes.TRANSITIONS:
        html = scenes.scene_file(L, "t1", {"type": "stage", "characters": [{"id": "linh"}]}, 5.0, cue_of({}), 4.0, last=False,
                                 tr_in=kind, tr_out=kind)
        assert 'id="t1-tx"' in html
        assert 0.0 <= scenes.OVERLAP[kind] <= 0.7  # the swap itself lasts about half a second


# ---------------------------------------------------------------- 5. cast registry and lint

def _lesson():
    return json.loads(EXAMPLE.read_text())


def test_example_lints_clean_and_exercises_everything():
    L = _lesson()
    schema.validate(L)
    rep = schema.lint(L)
    assert rep["errors"] == []
    blob = json.dumps(L, ensure_ascii=False)
    acts = set(re.findall(r'"action": "(\w+)"', blob))
    assert set(C.ACTIONS) - {"stand"} <= acts | {"idle"} and set(C.ACTIONS) - acts <= {"stand"}
    assert set(C.EXPRESSIONS) <= set(re.findall(r'"expression": "(\w+)"', blob))
    assert set(scenes.TRANSITIONS) <= set(re.findall(r'"transition": "(\w+)"', blob))
    assert L["meta"]["style"] == "sticker" and len(L["meta"]["cast"]) == 2 and 4 <= len(L["beats"]) <= 5
    assert build.aspect_of(L["meta"]) == "16:9" and build.aspect_of({"style": "sticker"}) == "16:9" and build.aspect_of({}) == "4:3"
    assert {"Linh", "Anh Tùng"} <= set(gate.screen_strings(L))


@pytest.mark.parametrize("mutate, needle", [
    (lambda L: L["beats"][0]["visual"]["characters"][0].update(id="mai"), "unknown character 'mai'"),
    (lambda L: L["beats"][1]["visual"]["characters"][0].update(look={"shirt": "#123456"}), "look.shirt"),
    (lambda L: L["meta"].pop("cast"), "need meta.cast"),
    (lambda L: L["beats"][1].update(transition="spin"), "transition 'spin'"),
    (lambda L: L["beats"][0]["visual"]["characters"][0].update(expression="angry"), "expression 'angry'"),
    (lambda L: L["beats"][0]["visual"]["characters"][0]["cues"][0].update(action="dance"), "action 'dance'"),
    (lambda L: L["beats"][0]["visual"]["bubble"].update(who="tung"), "bubble 'who'"),
    (lambda L: L["beats"][0]["visual"].update(set="beach"), "set 'beach'"),
    (lambda L: L["beats"][0]["visual"]["props"][0].update(icon="unicorn"), "icon 'unicorn'"),
    (lambda L: L["meta"]["cast"][0]["look"].update(hair="mohawk"), "hair 'mohawk'"),
    (lambda L: L["meta"].update(style="neon"), "meta.style"),
])
def test_story_lint_errors(mutate, needle):
    L = _lesson()
    mutate(L)
    errs = schema.lint(L)["errors"]
    assert any(needle in e for e in errs), errs


def test_look_must_match_across_beats_even_without_a_registered_key():
    L = _lesson()
    L["beats"][1]["visual"]["characters"][0]["look"] = {"glasses": True}
    L["beats"][2]["visual"]["characters"][0]["look"] = {"glasses": False}
    assert any("look.glasses" in e for e in schema.lint(L)["errors"])


def test_existing_lessons_gain_no_errors():
    for p in sorted((ROOT / "lessons").glob("**/lesson.json")) + [ROOT / "docs" / "examples" / "engine-check.lesson.json"]:
        assert schema.lint(schema.load(p))["errors"] == [], p


# ---------------------------------------------------------------- 6. docs

def test_docs_teach_the_sticker_story_layer():
    skill = (ROOT / ".claude" / "skills" / "lesson-video" / "SKILL.md").read_text()
    craft = (ROOT / ".claude" / "skills" / "lesson-video" / "references" / "script-craft.md").read_text()
    for word in ("`stage`", "meta.cast", "transition", "sticker-check.lesson.json", '"style": "sticker"'):
        assert word in skill or word in craft, word
    for word in ("walk_in", "facepalm", "bubble", "whip"):
        assert word in skill + craft, word
