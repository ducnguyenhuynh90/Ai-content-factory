import json
import os
import stat

import pytest

from vfactory.editor import brand as B
from vfactory.editor import frame, pipeline, takes, workspace


def W(text, t, gap=0.08, wd=0.28):
    out = []
    for w in text.split():
        out.append({"word": w, "start": round(t, 3), "end": round(t + wd, 3), "prob": 0.95})
        t += wd + gap
    return out, t


def recording(lines):
    words, t = [], 0.5
    for text, pause in lines:
        ws, t = W(text, t)
        words += ws
        t += pause
    return words


def test_retake_keeps_complete_take_and_drops_restart_phrase():
    words = recording([("So the biggest mistake people make with um with video is", 1.2), ("let me do that again.", 1.5),
                       ("So the biggest mistake people make with video is waiting too long.", 0.9), ("You need a plan.", 0.5)])
    p = takes.plan(words)[0]
    first = p["decisions"][0]
    assert first["chosen"]["text"].endswith("waiting too long.")
    assert first["alternatives"] and not first["flagged"]
    assert [m["text"] for m in p["restart_markers"]] == ["let me do that again."]
    kept = " ".join(w["word"] for w in p["words_kept"])
    assert "again" not in kept and "um" not in kept.split()


def test_last_take_is_not_automatically_best():
    words = recording([("This tool saves you ten hours every week.", 1.0),
                       ("This tool saves you uh uh ten ten hours every", 1.0)])
    d = takes.plan(words)[0]["decisions"][0]
    assert d["chosen"]["text"] == "This tool saves you ten hours every week."


def test_low_confidence_is_flagged_when_wording_differs():
    words = recording([("Our app helps small teams ship faster than ever before.", 1.0),
                       ("Our app helps small teams ship better products than ever.", 1.0)])
    d = takes.plan(words)[0]["decisions"][0]
    assert d["alternatives"]
    assert d["flagged"] is True


def test_pauses_tightened_but_short_pauses_kept():
    words = recording([("First point here.", 2.0), ("Second point here.", 0.3), ("Third point.", 0.5)])
    p = takes.plan(words)[0]
    assert len(p["pauses_tightened"]) == 1 and p["pauses_tightened"][0]["gap"] > 1.9
    assert p["duration"] < (words[-1]["end"] - words[0]["start"]) - 1.0


def test_topic_split_on_marker_but_not_on_pause_alone():
    words = recording([("Lighting matters more than cameras.", 1.0), ("Okay, next video.", 4.0),
                       ("Microphones are the second upgrade.", 1.0)])
    assert len(takes.plan(words)) == 2
    words = recording([("Lighting matters more than cameras.", 5.0), ("And lighting is cheap to fix.", 1.0)])
    assert len(takes.plan(words)) == 1  # long pause, same topic: one video


def test_segments_are_frame_snapped():
    words = recording([("One two three four.", 1.5), ("Five six seven.", 0.2)])
    for s in takes.plan(words, fps=30)[0]["segments"]:
        assert abs(s["start"] * 30 - round(s["start"] * 30)) < 1e-6
        assert abs(s["end"] * 30 - round(s["end"] * 30)) < 1e-6


def test_workspace_protects_original(tmp_path):
    orig = tmp_path / "IMG_1.MOV"
    orig.write_bytes(b"original-bytes" * 100)
    before = orig.read_bytes()
    proj = workspace.new_project(orig, "My Topic", root=tmp_path / "VE")
    assert orig.read_bytes() == before
    copy = workspace.source_copy(proj)
    assert copy.read_bytes() == before
    assert not (copy.stat().st_mode & stat.S_IWUSR)  # read-only
    assert workspace.verify_original_untouched(proj)
    for bad in (orig, copy, tmp_path / "elsewhere.mp4"):
        with pytest.raises(workspace.WorkspaceError):
            workspace.guard_output(bad, proj)
    assert workspace.guard_output(proj / "final" / "x.mp4", proj)
    assert set(os.listdir(proj)) >= {"source", "working", "transcript", "assets", "preview", "final", "project.json"}


def test_cloud_folders_refused(tmp_path):
    assert workspace.is_cloud_synced("/Users/a/Library/Mobile Documents/com~apple~CloudDocs/x")
    assert workspace.is_cloud_synced("/Users/a/Dropbox/videos")
    assert workspace.is_cloud_synced("/home/a/VideoEditor") is None
    with pytest.raises(workspace.WorkspaceError):
        workspace.ensure_root(tmp_path / "Dropbox" / "VideoEditor")


def test_brand_never_invented_and_saved_on_request(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_EDITOR_CONFIG", str(tmp_path / "cfg"))
    assert B.load_brand() == {} and not B.brand_complete()
    with pytest.raises(ValueError):
        B.save_brand("red", "#000000", "Inter")
    B.save_brand("#ff5533", "#112233", "Montserrat")
    assert B.brand_complete() and B.load_brand()["primary_color"] == "#FF5533"
    B.add_taste("captions are too large", sets={"caption_size": 0.85})
    assert B.load_prefs()["caption_size"] == 0.85
    B.add_taste("for this video only use red", scope="project", sets={"caption_case": "upper"})
    assert B.load_prefs()["caption_case"] == "as-is"  # one-off feedback is not a global preference
    t = json.loads((tmp_path / "cfg" / "taste.json").read_text())
    assert t["rules"][0]["said"] == "captions are too large" and t["rules"][0]["from"] == "user"


def test_brand_discovery_and_broll_kit(tmp_path):
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / "DESIGN.md").write_text("Primary #FF0066, secondary #101010")
    kit = tmp_path / "proj" / "B-roll kit"
    kit.mkdir()
    (kit / "logo.png").write_bytes(b"x")
    (kit / "office.mp4").write_bytes(b"x")
    found = B.discover_brand([tmp_path])
    assert any(f["kind"] == "guide" and "#FF0066" in f["colors"] for f in found)
    k = B.find_broll_kit([tmp_path])
    assert k and k.name == "B-roll kit"
    idx = B.index_broll(k)
    assert idx["logos"] and idx["video"]


def test_reframe_never_upscales_past_limit():
    r = frame.plan_reframe(1920, 1080, 1080, 1920)
    assert (r.crop_w, r.crop_h) == (608, 1080) and r.out_h <= 1080 * 1.34 and r.warnings
    r = frame.plan_reframe(3840, 2160, 1080, 1920)
    assert (r.out_w, r.out_h) == (1080, 1920) and not r.warnings


def test_word_mapping_to_output_timeline():
    words = [{"word": "a", "start": 10.0, "end": 10.3}, {"word": "b", "start": 20.0, "end": 20.4}]
    segs = [{"start": 9.9, "end": 10.5}, {"start": 19.8, "end": 20.6}]
    m = pipeline.map_words(words, segs)
    assert m[0]["start"] == pytest.approx(0.1) and m[1]["start"] == pytest.approx(0.6 + 0.2)
