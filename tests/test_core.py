
import pytest

from vfactory import autoedit, captions, easing, recipe as R, styles
from vfactory.render import _thin_sfx, assign_times, plan


def test_easings_hit_endpoints():
    for name, fn in easing.EASINGS.items():
        assert fn(0.0) == pytest.approx(0.0, abs=1e-6), name
        assert fn(1.0) == pytest.approx(1.0, abs=1e-6), name


def test_progress_clamps():
    assert easing.progress(-1, 0, 2) == 0
    assert easing.progress(5, 0, 2) == 1
    assert easing.progress(1, 0, 2) == 0.5


def _recipe(**kw):
    r = {"sources": {"A": "/tmp/a.mp4", "B": "/tmp/b.mp4"},
         "segments": [{"source": "A", "start": 0, "end": 4}, {"source": "B", "start": 1, "end": 5, "transition": "dissolve"},
                      {"source": "A", "start": 6, "end": 9}],
         "title": {"text": "Hello"}, "ending": {"title": "Hello"}}
    r.update(kw)
    return R.normalize(r, __import__("pathlib").Path("/tmp"))


def test_recipe_validation():
    with pytest.raises(R.RecipeError):
        R.normalize({"sources": {"A": "x"}, "segments": [{"source": "Z", "start": 0, "end": 1}]}, __import__("pathlib").Path("."))
    with pytest.raises(R.RecipeError):
        R.normalize({"sources": {"A": "x"}, "segments": [{"source": "A", "start": 2, "end": 1}]}, __import__("pathlib").Path("."))
    with pytest.raises(R.RecipeError):
        R.normalize({"sources": {"A": "x"}, "segments": [{"source": "A", "start": 0, "end": 1, "transition": "spin"}]},
                    __import__("pathlib").Path("."))
    r = _recipe()
    assert r["format"]["width"] == 1920 and r["format"]["fps"] == 30


def test_plan_structure_with_cold_open():
    look = styles.get("prestige")
    r = _recipe(cold_open=[{"source": "B", "start": 10, "end": 13}])
    pieces = plan(r, look)
    kinds = [p["kind"] for p in pieces]
    assert kinds == ["footage", "title_card", "footage", "footage", "footage", "end_card"]
    assert pieces[1]["transition"] == "cut"          # smash cut into the title
    assert pieces[2]["transition"] == "dip"          # title fades into the body
    assert pieces[-1]["transition"] == "dip"         # body dips into the end card
    total = assign_times(pieces)
    expected = sum(p["dur"] for p in pieces) - sum(p["tdur"] for p in pieces)
    assert total == pytest.approx(expected)
    for a, b in zip(pieces, pieces[1:]):
        assert b["out_start"] == pytest.approx(a["out_end"] - b["tdur"])


def test_plan_title_over_without_cold_open():
    pieces = plan(_recipe(), styles.get("editorial"))
    assert [p["kind"] for p in pieces][0] == "footage"
    assert all(p["kind"] != "title_card" for p in pieces)


def test_transition_never_exceeds_neighbours():
    r = _recipe(segments=[{"source": "A", "start": 0, "end": 0.6}, {"source": "B", "start": 0, "end": 0.5, "transition": "dissolve"}])
    pieces = plan(r, styles.get("luxury"))
    for i, p in enumerate(pieces[1:], 1):
        assert p["tdur"] <= 0.45 * min(p["dur"], pieces[i - 1]["dur"]) + 1e-9


def test_caption_mapping_uses_output_timeline():
    pieces = [{"kind": "footage", "source": "A", "src_start": 10.0, "src_end": 14.0, "out_start": 3.0, "speed": 1.0},
              {"kind": "footage", "source": "A", "src_start": 20.0, "src_end": 22.0, "out_start": 7.0, "speed": 2.0}]
    words = [{"source": "A", "word": "hi", "start": 11.0, "end": 11.4},
             {"source": "A", "word": "cut", "start": 15.0, "end": 15.3},       # not in any piece -> dropped
             {"source": "A", "word": "fast", "start": 21.0, "end": 21.5}]
    m = captions.map_words(words, pieces)
    assert [w["word"] for w in m] == ["hi", "fast"]
    assert m[0]["start"] == pytest.approx(4.0)
    assert m[1]["start"] == pytest.approx(7.5)


def _words(text, t0=0.0, step=0.3):
    out = []
    for i, w in enumerate(text.split()):
        out.append({"word": w, "start": t0 + i * step, "end": t0 + i * step + 0.25})
    return out


def test_chunk_absorbs_orphans_and_breaks_on_sentences():
    ch = captions.chunk(_words("Every film starts with a question. Ours was simple."), max_words=5)
    texts = [" ".join(w["word"] for w in c) for c in ch]
    assert texts[0] == "Every film starts with a question."
    assert texts[1] == "Ours was simple."


def test_chunk_breaks_on_pause():
    ws = _words("one two") + _words("three four", t0=2.0)
    assert len(captions.chunk(ws, max_words=6)) == 2


def test_ass_written(tmp_path):
    look = styles.get("hype")
    out = captions.build_ass(_words("hello big world"), look, 1080, 1920, tmp_path / "c.ass")
    text = out.read_text()
    assert "Archivo Black" in text and "Dialogue:" in text
    assert captions.build_ass(_words("hi there"), look, 1080, 1920, tmp_path / "d.ass", blackout=[(0, 5)]).read_text().count("Dialogue") == 0


def test_sfx_thinning_caps_density():
    ev = [{"kind": "whoosh", "at": i * 0.5} for i in range(60)] + [{"kind": "hit", "at": 3.0}]
    out = _thin_sfx(sorted(ev, key=lambda e: e["at"]), total=30.0)
    assert len(out) <= max(4, int(8 * 30 / 60) + 2)
    assert any(e["kind"] == "hit" for e in out)  # hits outrank whooshes


def _analysis(kind="broll"):
    def src(path, n_shots):
        shots = [{"start": i * 4.0, "end": i * 4.0 + 4.0, "motion": 0.01 * (i + 1), "sharpness": 0.1, "contrast": 0.2,
                  "brightness": 0.4, "score": 0.3 + 0.1 * i, "peak": i * 4.0 + 2.0} for i in range(n_shots)]
        return {"path": path, "duration": 4.0 * n_shots, "width": 1920, "height": 1080, "fps": 30, "has_audio": True,
                "kind": "broll", "speech_ratio": 0.0, "silences": [], "speech": [], "shots": shots,
                "energy": [], "interest": [0.5] * int(4 * 4.0 * n_shots)}
    a = {"sources": {"A": src("/x/a.mp4", 5), "B": src("/x/b.mp4", 5)},
         "music": {"path": "/x/m.wav", "duration": 60, "bpm": 120.0, "beats": [], "downbeats": [0.5 + 2 * i for i in range(30)],
                   "drop": 16.5, "energy": []}}
    if kind == "talk":
        t = src("/x/t.mp4", 1)
        t.update(kind="talk", duration=30.0, speech=[(1.0, 4.0), (5.0, 9.5), (11.0, 18.0), (19.0, 27.0)],
                 energy=[0.1] * 120, speech_ratio=0.8, interest=[0.5] * 120)
        a["sources"]["T"] = t
    return a


def test_autoedit_montage_arc_and_validity():
    rec = autoedit.direct(_analysis(), look_name="blockbuster", title="T", music="/x/m.wav")
    r = R.normalize(rec, __import__("pathlib").Path("/"))
    beats = [s["beat"] for s in r["segments"]]
    assert beats[0] == "OPEN" and beats[-1] == "RESOLVE"
    assert r["cold_open"], "montage should open cold"
    for a, b in zip(r["segments"], r["segments"][1:]):
        assert (a["source"], a["start"]) != (b["source"], b["start"]), "same shot twice in a row"
    assert r["music"]["sync_downbeats"]


def test_autoedit_talk_has_cutaways_and_voice_spine():
    rec = autoedit.direct(_analysis("talk"), look_name="documentary", title="T",
                          lower_thirds=[{"segment": "first_voice", "name": "N"}])
    assert any(s["beat"] == "VOICE" for s in rec["segments"])
    assert rec["segments"][0]["beat"] == "ESTABLISH"
    assert isinstance(rec["lower_thirds"][0]["segment"], int)
    assert rec["segments"][rec["lower_thirds"][0]["segment"]]["beat"] == "VOICE"
    for c in rec["cutaways"]:
        assert rec["segments"][c["segment"]]["beat"] == "VOICE"


def test_every_look_is_complete():
    for name, look in styles.LOOKS.items():
        assert look.title_anim in __import__("vfactory.motion.titles", fromlist=["TITLE_ANIMS"]).TITLE_ANIMS
        assert set(look.transitions) <= R.TRANSITIONS
        assert look.min_shot < look.max_shot
