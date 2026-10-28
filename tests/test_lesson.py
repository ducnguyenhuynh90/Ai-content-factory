import copy
import json
import re
from pathlib import Path

import pytest

from vfactory.lesson import build, scenes, schema, voice

LESSON = Path(__file__).resolve().parents[1] / "lessons" / "investing" / "001-newton-south-sea-bubble" / "lesson.json"


def test_example_lesson_is_valid_and_lint_clean():
    L = schema.load(LESSON)
    rep = schema.lint(L)
    assert rep["errors"] == [] and rep["warnings"] == []
    assert 3 <= rep["stats"]["est_minutes"] <= 5
    assert L["meta"]["aspect"] == "4:3"


def _mini():
    return {"meta": {"title": "T", "topic": "investing", "disclaimer": "Not advice.", "target_minutes": [0.1, 5]},
            "sources": [{"id": "s1", "cite": "x"}],
            "principles": [{"name": "a"}, {"name": "b"}],
            "beats": [{"id": "b1", "act": "hook", "narration": "In seventeen twenty a genius lost a fortune.",
                       "visual": {"type": "statement", "text": "T"}, "sources": ["s1"]},
                      {"id": "b2", "act": "misconception", "narration": "We think smart people are safe.", "visual": {"type": "statement", "text": "Smart = safe?"}},
                      {"id": "b3", "act": "question", "narration": "Which matters most?", "visual": {"type": "question", "question": "Which?"}},
                      {"id": "b4", "act": "recap", "narration": "Price is not value.", "visual": {"type": "list", "items": ["Price is not value"]}}]}


def test_lint_rules():
    L = _mini()
    assert schema.lint(L)["errors"] == []
    bad = copy.deepcopy(L)
    bad["beats"][0]["narration"] = "Today we will talk about bubbles."
    assert any("preamble" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(L)
    bad["meta"]["disclaimer"] = ""
    assert any("disclaimer" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(L)
    bad["beats"][1]["narration"] = "This fund is guaranteed to double."
    assert any("promissory" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(L)
    bad["beats"][1]["certainty"] = "attributed"
    assert any("states it as fact" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(L)
    bad["beats"][1]["narration"] = "In 1720 prices rose."
    w = schema.lint(bad)["warnings"]
    assert any("digits" in x for x in w) and any("no source" in x for x in w)
    bad = copy.deepcopy(L)
    del bad["beats"][2]
    assert any("retrieval question" in x for x in schema.lint(bad)["warnings"])


def test_validate_rejects_unknown_visual_and_source():
    L = _mini()
    L["beats"][0]["visual"]["type"] = "hologram"
    with pytest.raises(schema.LessonError):
        schema.validate(L)
    L = _mini()
    L["beats"][0]["sources"] = ["nope"]
    with pytest.raises(schema.LessonError):
        schema.validate(L)


def test_word_times_and_cues():
    wt = voice.word_times("Then came September. The bubble burst.", 3.0)
    assert wt[0]["start"] == 0 and wt[-1]["end"] <= 3.0
    assert 0 < voice.find_word(wt, "September") < voice.find_word(wt, "bubble burst")
    assert voice.find_word(wt, "missing", 9.9) == 9.9


def test_timing_holds_for_questions_and_graphics():
    L = schema.load(LESSON)
    durs = {b["id"]: 10.0 for b in L["beats"]}
    t = build.plan_timing(L, durs)
    by = {x["id"]: x for x in t}
    q = next(b for b in L["beats"] if b["visual"]["type"] == "question")
    assert by[q["id"]]["dur"] > 10 + q["visual"]["think_seconds"]
    for a, b in zip(t, t[1:]):
        assert b["start"] == pytest.approx(a["start"] + a["dur"], abs=1e-3)


def test_every_scene_type_renders_markup():
    L = schema.load(LESSON)
    look = scenes.Look({"primary_color": "#FF4F00", "secondary_color": "#0E0E0E", "font": "Inter"}, 1440, 1080)
    seen = set()
    for b in L["beats"]:
        html = scenes.scene_file(look, b["id"], b["visual"], 8.0, lambda w, d: d, 6.0, last=False)
        assert f'data-composition-id="{b["id"]}"' in html and f'window.__timelines["{b["id"]}"]' in html
        assert "font-size:1px" not in html
        seen.add(b["visual"]["type"])
    assert {"title", "chart", "timeline", "quote", "portrait", "principle", "question", "list", "end"} <= seen
    assert look.fs(0.01) >= 28  # type floor


def test_hook_rules_reject_slow_title_first_openings():
    slow = [{"id": "b1", "act": "hook", "narration": "In the spring of seventeen twenty, the smartest man in England made a "
             "fortune in the stock market. Then he gave it back. And then some.", "visual": {"type": "title", "title": "x"}},
            {"id": "b2", "act": "misconception", "narration": "We like to believe bubbles only catch fools.",
             "visual": {"type": "statement", "text": "x"}}]
    errs = schema.hook_errors(slow)
    assert any("title card" in e for e in errs) and any("5s" in e for e in errs)
    assert any("open a loop" in w for w in schema.hook_warnings(slow))
    L = schema.load(LESSON)
    assert schema.hook_errors(L["beats"]) == [] and schema.hook_warnings(L["beats"]) == []
    assert L["beats"][0]["visual"]["type"] == "hook"


def test_hook_scene_has_frame_zero_content_and_impact_on_cue():
    look = scenes.Look({"primary_color": "#FF4F00", "secondary_color": "#0E0E0E", "font": "Inter"}, 1440, 1080)
    v = {"type": "hook", "lines": ["He explained gravity.", "Then he lost a fortune to it."], "crash_cue": "lost"}
    html = scenes.scene_file(look, "h1", v, 6.0, lambda w, d: 3.0 if w == "lost" else d, 5.0, last=False)
    assert "He explained gravity." in html  # line 1 is in the markup with no entrance: visible at frame 0
    assert 'tl.fromTo("#h1-l1"' not in html
    assert '"#h1-l2", {opacity: 0, scale: 1.35}' in html and "3.000);" in html  # slam lands on the word


def test_silent_title_beat_is_allowed_only_with_hold():
    L = _mini()
    L["beats"].insert(1, {"id": "t0", "act": "context", "narration": "", "visual": {"type": "title", "title": "T", "hold": 3}})
    schema.validate(L)
    L["beats"][1]["visual"].pop("hold")
    with pytest.raises(schema.LessonError):
        schema.validate(L)


VI_LESSON = Path(__file__).resolve().parents[1] / "lessons" / "books" / "001-good-to-great" / "lesson.json"


def test_vietnamese_lesson_is_valid_and_lint_clean():
    L = schema.load(VI_LESSON)
    rep = schema.lint(L)
    assert rep["errors"] == [] and rep["warnings"] == []
    assert 3 <= rep["stats"]["est_minutes"] <= 5
    assert L["meta"]["lang"] == "vi" and L["meta"]["voice"].startswith(("piper:", "omnivoice:", "gemini:"))


def test_vietnamese_words_timing_and_hook_rules():
    assert schema.words("Từ tốt đến vĩ đại") == ["Từ", "tốt", "đến", "vĩ", "đại"]
    # Vietnamese syllables are short: the same count reads faster than English words
    assert schema.est_seconds("một " * 27, 1.0, "vi") < schema.est_seconds("one " * 27, 1.0, "en")
    L = _mini()
    L["meta"]["lang"] = "vi"
    L["beats"][0]["narration"] = "Xin chào các bạn, hôm nay chúng ta nói về sách."
    assert any("preamble" in e for e in schema.lint(L)["errors"])
    wt = voice.word_times("Chỉ mười một công ty đi được từ tốt đến vĩ đại.", 4.0)
    assert 0 < voice.find_word(wt, "mười một") < voice.find_word(wt, "vĩ đại")


def test_vietnamese_labels_and_numbers():
    look = scenes.Look({"primary_color": "#E8B06A", "secondary_color": "#12100E", "font": "Inter"}, 1440, 1080, "vi")
    html = scenes.scene_file(look, "q1", {"type": "question", "question": "Q?", "choices": ["a"], "answer": "a"}, 9.0,
                             lambda w, d: d, 3.0, last=False)
    assert "Dừng lại và nghĩ" in html and "Đáp án:" in html and "Pause and think" not in html
    html = scenes.scene_file(look, "s1", {"type": "stat", "value": 6.9, "decimals": 1, "label": "x"}, 5.0, lambda w, d: d, 3.0, last=False)
    assert 'toLocaleString("vi-VN"' in html
    assert scenes._fmt_num(1435, 0, "vi-VN") == "1.435" and scenes._fmt_num(6.9, 1, "vi-VN") == "6,9"
    assert scenes._fmt_num(1435.5, 1) == "1,435.5"


def test_chill_bed_has_a_soft_pulse(tmp_path):
    from vfactory.lesson import music
    import soundfile as sf

    y, sr = sf.read(str(music.bed(6.0, tmp_path / "c.wav", mood="chill")))
    assert len(y) == int(sr * 6.0) and 0.3 < abs(y).max() <= 0.71


def test_metaphor_scenes_render_and_validate():
    L = schema.load(VI_LESSON)
    look = scenes.Look({"primary_color": "#E8B06A", "secondary_color": "#12100E", "font": "Inter"}, 1440, 1080, "vi")
    kinds = set()
    visuals = []
    for b in L["beats"]:
        v = b["visual"]
        visuals += [(f'{b["id"]}s{i}', sh) for i, sh in enumerate(v["shots"])] if v["type"] == "shots" else [(b["id"], v)]
    for vid, v in visuals:
        t = v["type"]
        if t in ("funnel", "ladder", "venn", "flywheel", "halo", "swap", "company", "rise", "trio", "icon", "book", "climb") or v.get("strike"):
            html = scenes.scene_file(look, vid, v, 9.0, lambda w, d: d, 7.0, last=False)
            assert "window.__timelines" in html and "Math.random" not in html
            kinds.add(t)
    assert {"funnel", "ladder", "venn", "flywheel", "halo", "swap", "company", "rise", "trio", "icon", "book", "climb"} <= kinds
    strike = scenes.scene_file(look, "s9", {"type": "statement", "text": "Vĩ đại là một cú bùng nổ.", "strike": "một cú bùng nổ.",
                                            "replace": "từng bước nhỏ"}, 6.0, lambda w, d: d, 5.0, last=False)
    assert 'id="s9-sl"' in strike and "từng bước nhỏ" in strike
    for motion in ("spin", "swing", "grow", "rise", "sink", "crack", "shake"):
        html = scenes.scene_file(look, "m1", {"type": "icon", "icon": "pendulum", "motion": motion}, 6.0, lambda w, d: d, 5.0, last=False)
        assert "window.__timelines" in html
    funnel = scenes.scene_file(look, "f1", {"type": "funnel", "total": 100, "keep": 3, "seed": 1}, 6.0, lambda w, d: d, 5.0, last=False)
    assert funnel.count('id="f1-s') == 3  # the survivors are their own elements, gathered on cue


def test_gemini_voice_is_cached_and_needs_a_key(tmp_path, monkeypatch):
    import base64

    import numpy as np

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(voice.VoiceUnavailable):
        voice.synth("Xin chào", tmp_path / "a.wav", "gemini:Charon", style="Đọc chậm rãi.", model="m")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    calls = []
    pcm = (np.sin(np.arange(24000) / 10) * 8000).astype(np.int16).tobytes()

    def fake(url, body=None, timeout=180):
        calls.append((url, body))
        return {"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(pcm).decode()}}]}}]}

    monkeypatch.setattr(voice, "_http_json", fake)
    d = voice.synth("Tốt là kẻ thù của vĩ đại.", tmp_path / "b.wav", "gemini:Charon", style="Đọc chậm rãi.", model="m")
    assert 0.9 < d <= 1.0 and calls[0][0].endswith("/models/m:generateContent")
    assert calls[0][1]["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Charon"
    assert calls[0][1]["contents"][0]["parts"][0]["text"].startswith("Đọc chậm rãi.")
    voice.synth("Tốt là kẻ thù của vĩ đại.", tmp_path / "b.wav", "gemini:Charon", style="Đọc chậm rãi.", model="m")
    assert len(calls) == 1  # cached by content: a rebuild pays only for changed lines


def test_omnivoice_designs_one_narrator_then_clones_it(tmp_path, monkeypatch):
    import numpy as np

    torch = pytest.importorskip("torch")  # noqa: F841
    calls = []

    class Fake:
        def generate(self, **kw):
            calls.append(kw)
            return [np.zeros(24000, dtype="float32") + 0.1]

    monkeypatch.setattr(voice, "_OMNI", Fake())
    monkeypatch.setattr(voice, "OMNI_DIR", tmp_path / "omni")
    for i, line in enumerate(["Tốt là kẻ thù của vĩ đại.", "Đẩy bánh đà mỗi ngày."]):
        voice.synth(line, tmp_path / f"{i}.wav", "omnivoice:male, middle-aged, low pitch", 0.9, lang="vi")
    design = [c for c in calls if "instruct" in c]
    clones = [c for c in calls if c.get("ref_audio")]
    assert len(design) == 1 and design[0]["instruct"] == "male, middle-aged, low pitch" and design[0]["language"] == "vi"
    assert len(clones) == 2 and len({c["ref_audio"] for c in clones}) == 1 and clones[0]["speed"] == 0.9


def test_shots_shift_each_picture_to_its_cue():
    look = scenes.Look({"primary_color": "#E8B06A", "secondary_color": "#12100E", "font": "Inter"}, 1440, 1080, "vi")
    v = {"type": "shots", "shots": [{"type": "statement", "text": "Một"}, {"type": "trio", "items": [{"icon": "bulb", "label": "Hai"}], "cue": "hai"}]}
    html = scenes.scene_file(look, "b1", v, 10.0, lambda w, d: 6.0 if w == "hai" else d, 9.0, last=False)
    assert 'id="b1s0-shot"' in html and 'id="b1s1-shot"' in html
    # the second shot's own tweens are moved onto the beat timeline at its cue (6 s), never before it
    t = [float(x) for x in re.findall(r'tl\.fromTo\("#b1s1-i0".*, (\d+\.\d+)\);', html)]
    assert t and min(t) >= 6.0
    bad = {"type": "shots", "shots": [{"type": "question", "question": "?"}]}
    L = _mini()
    L["beats"][0]["visual"] = bad
    with pytest.raises(schema.LessonError):
        schema.validate(L)


def test_caption_groups_break_on_punctuation_without_orphans():
    wt = voice.word_times("Không nhờ may mắn. Cũng không nhờ một vị giám đốc hào nhoáng nào cả.", 6.0)
    g = build.caption_groups(wt, max_words=7)
    assert [w["word"] for w in g[0]] == ["Không", "nhờ", "may", "mắn."]
    assert all(len(x) > 1 for x in g) and sum(len(x) for x in g) == len(wt)


def test_align_falls_back_cleanly_without_whisper(tmp_path, monkeypatch):
    import builtins

    import numpy as np
    import soundfile as sf

    wav = tmp_path / "a.wav"
    sf.write(str(wav), np.zeros(24000, dtype="float32"), 24000)
    real = builtins.__import__

    def no_fw(name, *a, **k):
        if name.startswith("faster_whisper"):
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_fw)
    assert voice.align(wav, "Một hai ba.") is None


def test_gate_copy_lint_and_fonts(tmp_path):
    from vfactory.lesson import gate

    L = _mini()
    L["beats"][1]["narration"] = "Chúng ta ta hay nghĩ  rằng có 3 cách ."
    issues = gate.copy_lint(L)
    assert any("doubled" in x for x in issues) and any("digits" in x for x in issues)
    assert any("whitespace" in x for x in issues) and any("before punctuation" in x for x in issues)
    fc = gate.font_coverage({"beats": [{"narration": "Tốt là kẻ thù của vĩ đại", "visual": {"type": "statement", "text": "ồ ắ ữ"}}]})
    if fc.get("checked"):
        assert fc["missing"] == {}


def test_swap_inside_shots_is_struck_after_it_is_read():
    look = scenes.Look({"primary_color": "#E8B06A", "secondary_color": "#12100E", "font": "Inter"}, 1440, 1080, "vi")
    v = {"type": "shots", "shots": [{"type": "statement", "text": "A"},
                                    {"type": "swap", "from": {"label": "Cũ", "icon": "rocket"}, "to": {"label": "Mới", "icon": "sprout"}, "cue": "hai"}]}
    html = scenes.scene_file(look, "b1", v, 12.0, lambda w, d: 4.0 if w == "hai" else d, 11.0, last=False)
    t = float(re.search(r'tl\.fromTo\("#b1s1-x".*, (\d+\.\d+)\);', html).group(1))
    assert t >= 4.0 + 1.5  # the shot opens at 4 s; the strike comes only after the old idea has been read


def test_gate_vietnamese_false_positives():
    from vfactory.lesson import gate as g

    assert g.NAME_RE.findall("Chuỗi Walgreens và Kimberly-Clark.") == ["Walgreens", "Kimberly-Clark"]
    assert g._name_heard("Kimberly-Clark", "công ty Kimberly Clark")
    assert not g._name_heard("Walgreens", "một cửa hàng thuốc")
    L = {"meta": {"lang": "vi"}, "beats": [{"id": "b1", "narration": "Mãi mãi, năm năm, đó là là sai.", "visual": {"type": "statement", "text": "x"}}]}
    assert [x for x in g.copy_lint(L) if "doubled" in x] == ["b1: doubled word 'là là'"]


def test_gate_vietnamese_numbers():
    from vfactory.lesson import gate as g

    assert g.vi_number(1435) == "một nghìn bốn trăm ba mươi lăm"
    assert g.vi_number(1971) == "một nghìn chín trăm bảy mươi mốt"
    assert g.vi_number(105) == "một trăm lẻ năm"
    said = "Một nghìn bốn trăm ba mươi lăm công ty, năm hai nghìn lẻ một, ba mươi sáu phần trăm, sáu phẩy chín lần."
    assert g.misread_numbers(said, "1.435 công ty, năm 2001, 36%, 6,9 lần.") == []
    assert g.misread_numbers(said, "1 435 công ty, năm 2001, 36 %, 6 ,9 lần.") == []
    assert g.misread_numbers("hơn chín mươi nghìn đô mỗi tháng.", "hơn 90 .000 đô mỗi tháng.") == []
    assert g.misread_numbers("sinh năm một nghìn chín trăm hai mươi tư ở Omaha.", "sinh năm 1920, từ ở Omaha.") == []
    assert g.misread_numbers("Tháng sáu năm một nghìn chín trăm tám mươi sáu, Munger", "Tháng 6-1986, Manger") == []
    assert g.misread_numbers("đoán năm mươi năm mươi, điểm", "đoán 50-50, điểm") == []
    assert g.misread_numbers(said, "1, 4, 35 công ty, năm 2001, 36%, 6,9 lần.") == ["một nghìn bốn trăm ba mươi năm"]


def test_no_inter_700():
    """HyperFrames embeds Inter 700 without its Vietnamese glyphs (Ộ, Đ, Ờ… fall back to a serif): never ask for 700."""
    import re as _re
    from pathlib import Path as _P

    for f in ("scenes.py", "metaphors.py", "build.py"):
        src = (_P(__file__).parents[1] / "vfactory" / "lesson" / f).read_text()
        assert not _re.search(r"font-weight(:\s*|=\")700", src), f
