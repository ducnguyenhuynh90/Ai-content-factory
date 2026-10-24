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
                       "visual": {"type": "title", "title": "T"}, "sources": ["s1"]},
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
