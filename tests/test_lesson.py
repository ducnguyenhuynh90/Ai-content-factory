import copy
import json
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
    assert {"title", "chart", "quote", "question", "list", "end", "stage"} <= seen
    for v in ({"type": "timeline", "events": [{"year": "1711", "text": "Founded"}]}, {"type": "principle", "n": 1, "name": "x"},
              {"type": "portrait", "name": "Isaac Newton"}):
        assert "__timelines" in scenes.scene_file(look, "zz", v, 6.0, lambda w, d: d, 5.0, last=False)
    assert look.fs(0.01) >= 28  # type floor


def test_every_stage_act_renders():
    from vfactory.lesson import stage
    look = scenes.Look({"font": "Inter"}, 1440, 1080)
    acts = [{"act": a, "at": 1.0} for a in stage.ACTS if a not in ("swap", "say", "count", "walk", "fly")] + [
        {"act": "swap", "asset": "Loudly crying face", "cue": "burst"}, {"act": "say", "text": "No, thanks!", "cue": "never"},
        {"act": "count", "from": 1000, "to": 185, "prefix": "£"}, {"act": "walk", "by": 0.2}, {"act": "fly", "to": [0.8, 0.3]}]
    for world in stage.WORLDS:
        v = {"type": "stage", "world": world, "caption": "Price is not value", "highlight": ["not"], "kicker": "Lesson 1",
             "actors": [{"id": "a", "asset": "Balloon", "do": acts}, {"id": "s", "asset": "Ewe", "repeat": 3, "enter": "slide-left"}]}
        schema._validate_stage("t", v)
        html = scenes.scene_file(look, "m1", v, 9.0, lambda w, d: d, 8.0, last=False)
        assert 'window.__timelines["m1"]' in html and "assets/img/balloon.png" in html and "assets/img/collision.png" in html
        assert html.count('id="m1-s') >= 3 and "repeat: -1" not in html and "nan" not in html.lower()
    assert stage.assets_used(v) >= {"Balloon", "Ewe", "Loudly crying face", "Collision"}


def test_stage_validation_catches_unknown_pictures_and_long_bubbles():
    v = {"type": "stage", "actors": [{"id": "a", "asset": "Hologram unicorn"}]}
    with pytest.raises(schema.LessonError, match="no picture"):
        schema._validate_stage("t", v)
    v = {"type": "stage", "actors": [{"id": "a", "asset": "Ewe", "do": [{"act": "say", "text": "this is far too many words"}]}]}
    with pytest.raises(schema.LessonError, match="4 words"):
        schema._validate_stage("t", v)


def test_asset_catalogue():
    from vfactory.lesson import assets
    assert len(assets.catalog()) > 1500 and assets.exists("man scientist") and not assets.exists("hologram")
    assert "Loudly crying face" in assets.search("crying")
    assert assets.catalog()["man scientist"] == "Man scientist/Default/3D/man_scientist_3d_default.png"


def test_lint_asks_for_pictures():
    L = _mini()
    L["beats"] += [{"id": f"s{i}", "act": "story", "narration": "And then it rose.", "visual": {"type": "statement", "text": "x"}}
                   for i in range(5)]
    L["beats"].append({"id": "p1", "act": "principle", "narration": "Lesson one.", "visual": {"type": "principle", "n": 1, "name": "x"}})
    w = schema.lint(L)["warnings"]
    assert any("no pictures" in x for x in w)
    assert any("p1: principle shown as words only" in x for x in w)
    assert any("text-only scenes in a row" in x for x in w)
    L["beats"][-1]["visual"] = {"type": "stage", "caption": "x", "actors": [{"id": "a", "asset": "Balloon"}]}
    L["beats"][6]["visual"] = {"type": "stage", "actors": [{"id": "s", "asset": "Ewe", "repeat": 4}]}
    w = schema.lint(L)["warnings"]
    assert not any("picture" in x or "text-only" in x for x in w)
    L["beats"][6]["visual"]["world"] = "unicorn"
    with pytest.raises(schema.LessonError):
        schema.validate(L)


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
