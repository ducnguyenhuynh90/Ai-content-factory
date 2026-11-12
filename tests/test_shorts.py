import copy
import json
import shutil
from pathlib import Path

import pytest

from vfactory.shorts import analytics, build, channel, schema, voice

EXAMPLE = Path(__file__).resolve().parents[1] / "shorts" / "examples" / "001-newton-bong-bong" / "short.json"


def test_example_short_is_lint_clean():
    S = schema.load(EXAMPLE)
    rep = schema.lint(S)
    assert rep["errors"] == [] and rep["warnings"] == []
    assert rep["stats"]["hook_seconds"] <= 3.2
    assert 30 <= rep["stats"]["est_seconds"] <= 60


def _mini():
    return {"meta": {"title": "T", "lang": "vi", "target_seconds": [3, 40], "hook_type": "story", "format": "story",
                     "caption": "c", "hashtags": ["#a", "#b", "#c"]},
            "sources": [{"id": "s1", "cite": "x"}],
            "beats": [{"id": "h1", "narration": "Năm 1720, Newton mất một gia tài.",
                       "visual": {"type": "hook", "lines": ["Newton", "mất gia tài"], "punch_cue": "mất"}, "sources": ["s1"]},
                      {"id": "b2", "narration": "Giá lên khoảng 1000 bảng.", "visual": {"type": "stat", "value": 1000, "label": "giá"},
                       "sources": ["s1"], "certainty": "estimate"},
                      {"id": "end", "narration": "Theo dõi để xem phần 2.", "visual": {"type": "end", "text": "Phần 2", "cta": "Theo dõi"}}]}


def test_lint_rules():
    S = _mini()
    assert schema.lint(S)["errors"] == []
    bad = copy.deepcopy(S)
    bad["beats"][0]["narration"] = "Xin chào các bạn, hôm nay chúng ta sẽ nói về một câu chuyện rất dài và thú vị về Newton."
    errs = schema.lint(bad)["errors"]
    assert any("preamble" in e for e in errs) and any("~3 s" in e for e in errs)
    bad = copy.deepcopy(S)
    bad["beats"][1]["narration"] = "Giá lên 1000 bảng."  # an estimate stated as fact
    assert any("certainty" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(S)
    bad["beats"][1]["visual"]["label"] = "một hai ba bốn năm sáu bảy tám chín mười"
    assert any("on-screen text" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(S)
    bad["beats"][0]["visual"]["type"] = "text"
    bad["beats"][0]["visual"]["text"] = "x"
    assert any("hook" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(S)
    bad["meta"]["pillar"] = "đầu tư"
    assert any("disclaimer" in e for e in schema.lint(bad)["errors"])
    bad = copy.deepcopy(S)
    bad["beats"][1]["narration"] = "Nhớ theo dõi kênh nhé, giá lên khoảng 1000 bảng."
    assert any("follow" in w for w in schema.lint(bad)["warnings"])


def test_validate_rejects_bad_visuals():
    S = _mini()
    S["beats"][1]["visual"] = {"type": "stat"}
    with pytest.raises(schema.ShortError):
        schema.validate(S)


def test_word_times_and_cues():
    t = voice.estimate_times("Tháng 9, bong bóng vỡ. Đến tháng 12.", 3.0)
    assert len(t) == 8 and t[0]["start"] == 0 and t[-1]["end"] <= 3.0
    assert t == sorted(t, key=lambda w: w["start"])
    assert voice.find_word(t, "vỡ") == t[4]["start"]
    assert voice.find_word(t, "bong bóng") == t[2]["start"]
    assert voice.find_word(t, "không-có", 9.9) == 9.9
    assert voice.provider("vi-VN-NamMinhNeural") == "edge" and voice.provider("none") == "none"
    assert voice.provider("kokoro:bm_george") == "kokoro"
    with pytest.raises(voice.VoiceUnavailable):
        voice.provider("robot")


def test_timing_plan_hook_on_frame_zero():
    S = _mini()
    tm = build.plan(S, {"h1": 2.0, "b2": 1.5, "end": 1.2})
    assert tm[0]["lead"] == 0.0 and tm[0]["start"] == 0.0
    assert all(abs(a["start"] + a["dur"] - b["start"]) < 1e-6 for a, b in zip(tm, tm[1:]))
    assert tm[-1]["dur"] >= 2.5  # end card holds long enough to read the CTA


def test_sfx_budget():
    ev = [{"kind": "pop", "at": i * 0.5, "gain_db": -6, "prio": 1} for i in range(60)]
    kept = build.thin_sfx(ev, 30.0)
    assert len(kept) <= 6 and all(b["at"] - a["at"] > 0.25 for a, b in zip(kept, kept[1:]))


def test_number_parsing():
    assert analytics._num("12.400", True) == 12400
    assert analytics._num("54.362") == pytest.approx(54.362)
    assert analytics._num("1,020", True) == 1020
    assert analytics._num("1.2K", True) == 1200
    assert analytics._num("0:21") == 21
    assert analytics._num("18,5%") == pytest.approx(18.5)


def test_channel_loop(tmp_path):
    root = channel.init(tmp_path / "kenh", "Kênh thử", "lịch sử", "vi", "@thu")
    sj = channel.new_short(root, "Thiên tài Newton và bong bóng")
    assert sj.parent.name == "001-thien-tai-newton-va-bong-bong"
    shutil.copy2(EXAMPLE, sj)
    (sj.parent / "build").mkdir()
    (sj.parent / "build" / "build.json").write_text(json.dumps({"duration": 50.0}))
    channel.log_post(root, {"slug": sj.parent.name, "title": "Người hiểu trọng lực", "url": "https://www.tiktok.com/@thu/video/123"})
    csv = tmp_path / "export.csv"
    csv.write_text("Video title,Video link,Total views,Average watch time,Total shares\n"
                   "Người hiểu trọng lực,https://www.tiktok.com/@thu/video/123,\"10,000\",20s,50\n"
                   "Khác,https://www.tiktok.com/@thu/video/9,10,1s,0\n", encoding="utf-8")
    r = analytics.import_export(root, csv)
    assert r["imported"] == 1 and r["unmatched"] == ["Khác"]
    ins = analytics.insights(root)
    row = ins["rows"][0]
    assert row["avg_pct"] == 40.0 and row["shares_1k"] == 5.0
    assert (root / "insights.md").exists()


def test_render_smoke(tmp_path):
    """A 3-scene short with no voice and no pictures: renders, right size, loudness in range."""
    S = _mini()
    S["meta"].update(voice="none", music="tense")
    p = tmp_path / "s" / "short.json"
    p.parent.mkdir()
    p.write_text(json.dumps(S, ensure_ascii=False))
    r = build.build(p, quality="draft", log=lambda *a: None)
    assert Path(r["video"]).exists() and r["size"] == [540, 960]
    assert r["checks"] == [], r["checks"]
    assert Path(r["frame0"]).exists()
