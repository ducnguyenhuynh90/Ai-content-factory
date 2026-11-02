"""Engine upgrades for clearer explainers: readable type, frozen-screen metric, concepts and their colours, storyboard
lint, the scenario and board scenes, and two gate fixes ($ heard as "đô la", strikes on their cue)."""

import copy
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pytest

from vfactory.lesson import build, canvas, gate, scenes, schema

ROOT = Path(__file__).resolve().parents[1]
LESSONS = [ROOT / "lessons" / "investing" / "001-newton-south-sea-bubble" / "lesson.json",
           ROOT / "lessons" / "books" / "001-good-to-great" / "lesson.json",
           ROOT / "lessons" / "books" / "026-noise" / "lesson.json"]
BRAND = {"primary_color": "#E8B06A", "secondary_color": "#12100E", "font": "Inter"}
CONCEPTS = [{"id": "noise", "visual": "dice", "color": "b", "shows": "judgments scattered", "omits": "the cause"},
            {"id": "bias", "visual": "target", "color": "a", "shows": "all off to one side", "omits": "how far"}]
SCENARIO = {"type": "scenario", "kicker": "Một ví dụ", "heading": "Cùng hồ sơ, hai cách chấm", "cue": "sau khi",
            "bars": [{"label": "Chấm chung một lượt", "before": 55, "after": 55, "concept": "noise"},
                     {"label": "Chấm riêng rồi mới gộp", "before": 55, "after": 20, "color": "a", "delta": "−35", "cue": "chấm riêng"}],
            "suffix": "%", "takeaway": "Bớt nhiễu mà không cần người giỏi hơn.", "takeaway_cue": "bớt"}
BOARD = {"type": "board", "kicker": "Ba thói quen", "overview": True, "overview_cue": "ba thói", "line": "Một tấm bảng, ba thói quen",
         "regions": [{"icon": "people", "label": "Chấm riêng, rồi mới gộp", "cue": "chấm riêng"},
                     {"icon": "puzzle", "label": "Chia nhỏ, rồi mới chấm", "cue": "chia nhỏ"},
                     {"concept": "noise", "label": "Tự kiểm tra nhiễu", "note": "đo trước khi sửa", "cue": "tự kiểm"}]}


def look(lang="vi", concepts=CONCEPTS):
    return scenes.Look(BRAND, 1440, 1080, lang, concepts)


def fixed_cue(table):
    return lambda w, d, after=None: table.get(w, d)


def sizes(html: str) -> list[int]:
    return [int(x) for x in re.findall(r'font-size(?::\s*|=")(\d+)(?:px|")', html)]


# ---------------------------------------------------------------- 1. readable type

def test_text_floor_is_36px_on_every_scene():
    L = look()
    assert L.fs(0.0) == 36 and L.fs(0.019) == 36 and L.fs(0.1) == 108
    visuals = []
    for p in LESSONS:
        for b in schema.load(p)["beats"]:
            v = b["visual"]
            visuals += [(f'{b["id"]}s{i}', s) for i, s in enumerate(v["shots"])] if v["type"] == "shots" else [(b["id"], v)]
    visuals += [("sc", SCENARIO), ("bd", BOARD),
                ("tl", {"type": "timeline", "events": [{"year": y, "text": "Một sự kiện có nhãn khá dài để xuống dòng"} for y in range(1990, 1996)]}),
                ("en", {"type": "end", "title": "T", "sources_line": "Nguồn: " + "sách " * 30, "disclaimer": "Không phải lời khuyên."})]
    seen = set()
    for vid, v in visuals:
        html = scenes.scene_file(L, vid, v, 9.0, lambda w, d, after=None: d, 7.0, last=False)
        small = [x for x in sizes(html) if x < 36]
        assert not small, (vid, v["type"], small)
        seen.add(v["type"])
    assert {"statement", "stat", "timeline", "end", "icon", "trio", "swap", "scenario", "board"} <= seen
    # the board's labels stay readable even when the camera shows the whole board
    lay = canvas.board_layout(L, 6)
    so = canvas._overview_scale(L, lay, True)
    html = scenes.scene_file(L, "b6", {**BOARD, "regions": BOARD["regions"] * 2}, 12.0, lambda w, d, after=None: d, 10.0, last=False)
    label = int(re.search(r'id="b6-rl0" style="font-size:(\d+)px', html).group(1))
    assert label * so >= 36


def test_timeline_labels_grow_away_from_the_line():
    html = scenes.scene_file(look(), "t", {"type": "timeline", "events": [{"year": 1, "text": "a"}, {"year": 2, "text": "b"}]},
                             6.0, lambda w, d: d, 5.0, last=False)
    assert re.search(r'id="t-e0" style="[^"]*bottom:\d+px', html) and re.search(r'id="t-e1" style="[^"]*top:\d+px', html)


# ---------------------------------------------------------------- 2. frozen screens

def test_frozen_stretches_merge_and_excuse():
    ch = [(2.5, 12.0), (5.0, 1.0), (7.5, 0.5), (10.0, 9.0), (12.5, 2.0), (15.0, 3.0)]
    fz = gate.frozen_stretches(ch)
    assert [(f["start"], f["end"]) for f in fz] == [(2.5, 7.5), (10.0, 15.0)]
    assert fz[0]["min_change"] == 0.5
    # the second run lies inside a question's countdown: not flagged
    assert [(f["start"], f["end"]) for f in gate.frozen_stretches(ch, excused=[(10.0, 15.0)])] == [(2.5, 7.5)]
    assert gate.DEAD_MAX_S == 2.0


def test_frame_changes_ignore_the_caption_band(monkeypatch):
    h, w = 240, 320
    a = np.zeros((h, w), np.uint8)
    b = a.copy()
    b[int(h * 0.9):, :] = 255  # only the captions changed
    c = b.copy()
    c[:100, :] = 200  # the picture changed

    class R:
        stdout = a.tobytes() + b.tobytes() + c.tobytes()

    monkeypatch.setattr(gate.subprocess, "run", lambda *a, **k: R())
    ch = gate.frame_changes(Path("x.mp4"))
    assert ch[0] == (2.5, 0.0) and ch[1][1] > 50


def test_frame_changes_on_a_real_render(tmp_path):
    mp4 = tmp_path / "v.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=10:duration=5",
                        "-f", "lavfi", "-i", "color=c=gray:size=320x240:rate=10:duration=8",
                        "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p", str(mp4)],
                       capture_output=True)
    if r.returncode:
        pytest.skip("ffmpeg lavfi unavailable")
    ch = gate.frame_changes(mp4)
    assert ch and ch[0][1] > gate.FROZEN_DIFF  # the test pattern moves
    fz = gate.frozen_stretches(ch)
    assert fz and fz[-1]["end"] >= 10.0 and fz[0]["start"] >= 5.0  # the grey still is caught


# ---------------------------------------------------------------- 3. concepts

def _lesson():
    return {"meta": {"title": "T", "lang": "vi", "target_minutes": [0.1, 5], "concepts": copy.deepcopy(CONCEPTS)},
            "sources": [{"id": "s", "cite": "x"}], "principles": [{"name": "a"}, {"name": "b"}],
            "beats": [{"id": "h1", "act": "hook", "narration": "Nhưng năm mươi lăm phần trăm thì sao?",
                       "visual": {"type": "icon", "concept": "noise", "line": "55%"}, "sources": ["s"]},
                      {"id": "b1", "act": "misconception", "narration": "Ta nghĩ lỗi chỉ là lệch.",
                       "visual": {"type": "trio", "items": [{"icon": "target", "label": "Lệch", "concept": "bias"},
                                                            {"label": "Tản mát", "concept": "noise"}]}},
                      {"id": "q", "act": "question", "narration": "Cái nào?", "visual": {"type": "question", "question": "?"}},
                      {"id": "r", "act": "recap", "narration": "Đo nhiễu.", "visual": {"type": "board", "regions": BOARD["regions"]}}]}


def test_concepts_validate_and_lint():
    L = _lesson()
    schema.validate(L)  # an icon visual may name its concept instead of an icon
    rep = schema.lint(L)
    assert rep["errors"] == [] and not any("concept" in w for w in rep["warnings"])
    bad = _lesson()
    bad["beats"][1]["visual"]["items"][1]["icon"] = "brain"  # noise drawn a second way
    errs = schema.lint(bad)["errors"]
    assert any("'noise'" in e and "'brain'" in e and "registered as 'dice'" in e for e in errs)
    bad = _lesson()
    bad["beats"][0]["visual"]["concept"] = "luck"
    assert any("unknown concept 'luck'" in e for e in schema.lint(bad)["errors"])
    bad = _lesson()
    bad["beats"][1]["visual"] = {"type": "funnel", "total": 10, "concept": "bias"}  # a scene type as the picture
    assert any("as 'funnel'" in e for e in schema.lint(bad)["errors"])
    bad = _lesson()
    del bad["meta"]["concepts"][0]["omits"]
    assert any("where the metaphor stops" in w for w in schema.lint(bad)["warnings"])
    bad = _lesson()
    bad["meta"]["concepts"][0]["color"] = "c"
    with pytest.raises(schema.LessonError):
        schema.validate(bad)


def test_script_craft_documents_concepts():
    doc = (ROOT / ".claude" / "skills" / "lesson-video" / "references" / "script-craft.md").read_text()
    assert "meta.concepts" in doc and "omits" in doc


# ---------------------------------------------------------------- 4. two concept colours

def _contrast(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_concept_colours_everywhere_and_readable():
    L = look()
    assert L.colors == {"a": "#E8B06A", "b": "#E77A5F"}
    for c in L.colors.values():
        for bg in ("#12100E", "#0E0E0E"):
            assert _contrast(c, bg) >= 4.5
    assert L.color({"concept": "noise"}) == "#E77A5F" and L.color({"color": "a"}) == "#E8B06A" and L.color({}, "#000000") == "#000000"
    ic = scenes.scene_file(L, "i", {"type": "icon", "concept": "noise"}, 5.0, lambda w, d: d, 4.0, last=False)
    assert 'stroke="#E77A5F"' in ic and "<rect" in ic  # the dice, in coral
    st = scenes.scene_file(L, "s", {"type": "stat", "value": 55, "label": "x", "color": "b"}, 5.0, lambda w, d: d, 4.0, last=False)
    assert re.search(r'id="s-n"[^>]*color:#E77A5F', st)
    hl = scenes.scene_file(L, "h", {"type": "statement", "text": "Lệch và tản mát", "highlight": ["Lệch", {"text": "tản mát", "concept": "noise"}]},
                           5.0, lambda w, d: d, 4.0, last=False)
    assert 'id="h-h0" class="hl" style="color:#E8B06A"' in hl and 'id="h-h1" class="hl" style="color:#E77A5F"' in hl
    # captions light the highlighted words in the same colour
    Ls = {"meta": {}, "beats": [{"id": "b", "narration": "Lệch và tản mát.", "visual": {"type": "statement", "text": "x",
                                                                                       "highlight": [{"text": "tản mát", "color": "b"}]}}]}
    times = {"b": [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate("Lệch và tản mát.".split())]}
    cap = build.captions_file(L, Ls, [{"id": "b", "start": 0, "dur": 3, "narr": 1.2, "lead": 0.4}], times, 3.0, 1440, 1080)
    assert '"#cap0w2", { color: "rgba(242,237,228,0.42)" }, { color: "#E77A5F"' in cap
    assert '"#cap0w0", { color: "rgba(242,237,228,0.42)" }, { color: "#F2EDE4"' in cap


# ---------------------------------------------------------------- 5. storyboard lint

def test_storyboard_lint_warns_on_slides():
    L = _lesson()
    L["beats"][0]["visual"] = {"type": "statement", "text": "55%"}
    L["beats"][1]["visual"] = {"type": "shots", "shots": [{"type": "stat", "value": 1, "label": "x", "action": "đếm"},
                                                          {"type": "quote", "text": "q", "by": "b", "cue": "lỗi", "action": "đếm"},
                                                          {"type": "icon", "icon": "dice", "action": "đếm"}]}
    L["beats"][3]["visual"] = {"type": "list", "items": ["a"]}
    sb = schema.lint(L)["storyboard"]
    assert any("text-led" in w and "≤ 30 %" in w for w in sb)
    assert any("first content picture" in w for w in sb) and any("last content picture" in w for w in sb)
    assert any("three shots running" in w for w in sb)
    L["beats"][1]["visual"]["shots"][2].pop("action")
    assert any("without an 'action'" in w for w in schema.lint(L)["storyboard"])
    long = _lesson()
    long["beats"][1]["narration"] = "Ta nghĩ lỗi chỉ là lệch. " * 8
    assert any("held ~" in w for w in schema.lint(long)["storyboard"])
    long["beats"][1]["hold"] = True
    assert not any("held ~" in w for w in schema.lint(long)["storyboard"])
    # warnings only: no existing lesson gains an error, and the "lint clean" warnings list is untouched
    for p in LESSONS:
        rep = schema.lint(schema.load(p))
        assert rep["errors"] == [] and isinstance(rep["storyboard"], list)


# ---------------------------------------------------------------- 6. scenario

def test_scenario_changes_state_on_its_cue():
    L = look()
    schema.validate({**_lesson(), "beats": [{**_lesson()["beats"][0], "visual": SCENARIO}]})
    html = scenes.scene_file(L, "sc", SCENARIO, 12.0, fixed_cue({"sau khi": 4.0, "chấm riêng": 1.5, "bớt": 8.0}), 11.0, last=False)
    assert "window.__timelines" in html and "Math.random" not in html
    # the knob, the fill and both bars move together on the cue word; the numbers count from before to after
    assert re.search(r'"#sc-kn", \{x: 0\}, \{x: 1152, duration: 1.4.*4\.000\);', html)
    assert re.search(r'"#sc-b1", \{scaleX: 0\.9524\}, \{scaleX: 0\.3463.*4\.000\);', html)
    assert 'tl.fromTo(scP1, { v: 55.0 }, { v: 20.0' in html
    assert re.search(r'"#sc-r1".*1\.500\);', html)  # a bar enters on its own cue
    assert re.search(r'"#sc-tk".*8\.000\);', html)
    assert 'color:#E77A5F' in html and "Trước" in html and "Sau" in html
    bad = {**SCENARIO, "bars": [{"label": "x"}]}
    with pytest.raises(schema.LessonError):
        schema.validate({**_lesson(), "beats": [{**_lesson()["beats"][0], "visual": bad}]})


# ---------------------------------------------------------------- 7. board

def test_board_camera_glides_between_regions_and_pulls_back():
    L = look()
    cue = fixed_cue({"chấm riêng": 0.5, "chia nhỏ": 3.0, "tự kiểm": 6.0, "ba thói": 9.0})
    html = scenes.scene_file(L, "bd", BOARD, 13.0, cue, 12.0, last=False)
    cam = re.findall(r'tl\.fromTo\("#bd-cv", \{x: ([-\d.]+), y: ([-\d.]+), scale: ([\d.]+)\}, \{x: ([-\d.]+), y: ([-\d.]+), scale: ([\d.]+), '
                     r'duration: ([\d.]+), ease: "([\w.]+)".*, ([\d.]+)\);', html)
    assert len(cam) >= 4
    for a, b in zip(cam, cam[1:]):  # one continuous path: every segment starts where the last one ended
        assert a[3:6] == b[0:3]
        assert float(b[8]) == pytest.approx(float(a[8]) + float(a[6]), abs=0.02)
    starts = {round(float(c[8]), 1): c for c in cam if c[7] == "power2.inOut"}
    assert {3.0, 6.0, 9.0} <= set(starts)  # glides on the cue words, the pull-back on its own
    zf = canvas.board_layout(L, 3)["zoom"]
    assert float(starts[9.0][5]) < 1.0 < zf  # pulled back: the whole board fits
    assert re.search(r'"#bd-ri2".*', html) and 'stroke="#E77A5F"' in html  # the concept region draws its registered dice in coral
    for bad in ("elastic", "rough", "shake", "flash"):
        assert bad not in html  # calm motion only
    assert re.search(r'"#bd-ln0", \{strokeDashoffset: \d+\}', html)  # the path draws itself between regions


def test_board_continues_over_beats():
    vis = [{"type": "board", "board_id": "k", "regions": BOARD["regions"], "focus": [0, 1]},
           {"type": "statement", "text": "x"},
           {"type": "board", "board_id": "k", "focus": [2], "overview": True},
           {"type": "board", "board_id": "k", "focus": [], "line": "x"}]
    r = canvas.resolve_boards(vis)
    assert "_drawn" not in vis[0] and r[2]["regions"] == BOARD["regions"]
    assert r[2]["_drawn"] == [0, 1] and r[2]["_cam0"] == 1 and r[2]["_cont_next"] and not r[0]["_cont_next"]
    assert r[3]["_cam0"] == "overview" and r[3]["_drawn"] == [0, 1, 2]
    L = look()
    html = scenes.scene_file(L, "c2", r[2], 8.0, lambda w, d, after=None: d, 7.0, last=False)
    assert '"#c2-c", {opacity: 1' not in html  # no exit: the next beat picks up the same board
    assert 'id="c2-ri0" width' in html and '"#c2-ri0"' not in html  # region 0 is already drawn, not drawn again
    schema.validate({**_lesson(), "beats": [{**_lesson()["beats"][0], "visual": vis[0]}, {**_lesson()["beats"][1], "visual": vis[2]}]})
    with pytest.raises(schema.LessonError):  # a board that continues nothing
        schema.validate({**_lesson(), "beats": [{**_lesson()["beats"][0], "visual": vis[2]}]})


def test_docs_show_the_new_scenes():
    doc = (ROOT / ".claude" / "skills" / "lesson-video" / "SKILL.md").read_text()
    assert "`scenario`" in doc and "`board`" in doc
    ex = (ROOT / "docs" / "examples" / "engine-check.lesson.json")
    L = json.loads(ex.read_text())
    schema.validate(L)
    assert {b["visual"]["type"] for b in L["beats"]} >= {"scenario", "board"}


# ---------------------------------------------------------------- 8. gate fixes

def test_dollar_sign_is_heard_as_do_la():
    assert gate._vi_digits_to_words("giá 4.000$ một tháng") == "giá bốn nghìn đô la một tháng"
    assert gate._vi_digits_to_words("giá $4.000 một tháng") == "giá bốn nghìn đô la một tháng"
    assert gate._vi_digits_to_words("trả 1,1 $") == "trả một phẩy một đô la"
    said = "Mỗi tháng bốn nghìn đô la, tức hai mươi phần trăm."
    heard = "Mỗi tháng 4.000$, tức 20%."
    assert gate.spoken_tokens(said, "vi") == gate.spoken_tokens(heard, "vi", heard=True)
    assert gate.misread_numbers(said, heard) == []
    # "đô" alone in the script is not reported as dropped when Whisper writes "$"
    import difflib
    nt, ht = gate.spoken_tokens("bốn nghìn đô mỗi tháng", "vi"), gate.spoken_tokens("4.000$ mỗi tháng", "vi", heard=True)
    gone = [op for op, a1, a2, _, _ in difflib.SequenceMatcher(None, nt, ht).get_opcodes() if op == "delete"]
    assert gone == []


def test_strike_lands_on_its_cue_not_at_one_second():
    L = look()
    v = {"type": "statement", "text": "Hộp đen thì màu đen", "strike": "màu đen", "replace": "Thật ra: màu cam", "strike_cue": "thật ra"}

    def at(html):
        return float(re.search(r'tl\.fromTo\("#(?:\w+)-sl".*, ([\d.]+)\);', html).group(1))

    for t in (2.2, 3.7, 5.1):
        assert at(scenes.scene_file(L, "s", v, 8.0, fixed_cue({"thật ra": t}), 7.0, last=False)) == pytest.approx(t)
    # a cue before the struck words are even drawn waits for them, not for a fixed 1.0 s
    early = at(scenes.scene_file(L, "s", v, 8.0, fixed_cue({"thật ra": 0.2}), 7.0, last=False))
    assert early == pytest.approx(0.12 + 0.09 * 4 + 0.2 + 0.15)
    # inside shots the cue word is looked up from the shot's start on, not where it was said earlier in the line
    from vfactory.lesson import voice

    wt = voice.word_times("Thật ra ai cũng nghĩ vậy. Hộp đen thì sao? Thật ra nó màu cam.", 9.0)

    def cue(word, default, after=None):
        return 0.45 + voice.find_word(wt, word, default - 0.45, after=None if after is None else after - 0.45)

    sh = {"type": "shots", "shots": [{"type": "icon", "icon": "clock"}, {**v, "cue": "hộp đen"}]}
    html = scenes.scene_file(L, "b", sh, 10.0, cue, 9.0, last=False)
    t_shot = float(re.search(r'"#bs1-shot", \{opacity: 0.*, ([\d.]+)\);', html).group(1))
    second = 0.45 + [w for w in wt if w["word"] == "Thật"][1]["start"]
    assert t_shot < second and at(html) == pytest.approx(second, abs=0.01)
