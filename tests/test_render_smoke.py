"""End-to-end: tiny synthetic clips through the whole pipeline (a few seconds)."""

import subprocess

import pytest

from vfactory import ffmpeg as ff, qa, recipe as R, vision
from vfactory.render import render


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("clips")
    out = {}
    for name, src in (("a", "testsrc2=s=320x180:r=30"), ("b", "smptebars=s=320x180:r=30")):
        p = d / f"{name}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-t", "4", "-i", src, "-f", "lavfi", "-t", "4",
                        "-i", "sine=frequency=330:sample_rate=48000", "-shortest", "-pix_fmt", "yuv420p", str(p)],
                       check=True, stdin=subprocess.DEVNULL)
        out[name] = str(p)
    return d, out


def test_full_render(clips):
    d, c = clips
    rec = {"look": "blockbuster", "format": {"width": 320, "height": 180, "fps": 30}, "sources": c,
           "title": {"text": "Smoke Test", "kicker": "CI"},
           "cold_open": [{"source": "b", "start": 0, "end": 1.2}],
           "segments": [{"source": "a", "start": 0, "end": 2}, {"source": "b", "start": 1, "end": 3, "transition": "whip"},
                        {"source": "a", "start": 2, "end": 3.5, "transition": "dissolve"}],
           "cutaways": [{"segment": 0, "offset": 0.3, "source": "b", "start": 2.0, "end": 3.0}],
           "lower_thirds": [{"segment": 0, "name": "Ada", "role": "Engineer", "duration": 2.5}],
           "captions": {"words": [{"source": "a", "word": "hello", "start": 0.2, "end": 0.6}]},
           "ending": {"title": "Smoke Test", "cta": "Subscribe", "hold": 3.0},
           "output": str(d / "final.mp4")}
    R.dump(rec, d / "r.json")
    rep = render(d / "r.json")
    info = ff.probe(rep["output"])
    assert info.width == 320 and info.height == 180 and info.has_audio
    assert abs(info.duration - rep["duration"]) < 0.25
    res = qa.check(rep["output"], rep)
    assert res["true_peak_dbfs"] <= -0.9
    v = vision.investigate(rep["output"], detail="efficient", out_dir=d / "vision")
    assert v["frames"] and (d / "vision" / "report.md").exists()
