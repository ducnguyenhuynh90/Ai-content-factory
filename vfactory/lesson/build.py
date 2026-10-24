"""lesson.json -> narrated, animated lesson video (HyperFrames, default 4:3 1440x1080)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .. import audio as A
from .. import ffmpeg as ff
from ..editor import brand as B
from ..editor import hyperframes as H
from ..editor.enhance import mix_stems
from . import music, schema, voice
from .scenes import Look, scene_file

ASPECTS = {"4:3": (1440, 1080), "16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
LEAD, TAIL = 0.45, 0.65  # seconds of picture before / after each narration line


def brand() -> dict:
    b = B.load_brand()
    if not B.brand_complete(b):
        b = {"primary_color": "#FF4F00", "secondary_color": "#0E0E0E", "font": "Inter"}
    return {**b, "text_color": "#F2EDE4"}


def grain_png(path: Path, size: int = 384, seed: int = 1) -> Path:
    from PIL import Image

    rng = np.random.default_rng(seed)
    g = rng.normal(128, 40, (size, size)).clip(0, 255).astype("uint8")
    a = np.full((size, size), 255, dtype="uint8")
    Image.fromarray(np.stack([g, g, g, a], axis=-1), "RGBA").save(path)
    return path


def plan_timing(L: dict, durs: dict[str, float]) -> list[dict]:
    t, out = 0.0, []
    for b in L["beats"]:
        v = b["visual"]
        narr = durs[b["id"]]
        d = LEAD + narr + TAIL
        if v["type"] == "question":
            ans = len(v.get("answer", "").split())
            d += float(v.get("think_seconds", 4.0)) + ((0.9 + 0.5 + 0.3 * ans) if ans else 0.4)  # answer readable
        if v["type"] == "title":
            d = max(d, 4.5)
        if v["type"] == "end":
            d = max(d + 1.5, 6.0)
        if v["type"] in ("chart", "timeline", "list", "compare"):
            d += 0.8  # let the viewer read the finished graphic
        out.append({"id": b["id"], "start": round(t, 3), "dur": round(d, 3), "narr": narr})
        t += d
    return out


def build(lesson_path: str | Path, out_dir: str | Path | None = None, *, force: bool = False, render: str | None = "draft",
          log=print) -> dict:
    lesson_path = Path(lesson_path)
    L = schema.load(lesson_path)
    rep = schema.lint(L)
    if rep["errors"] and not force:
        raise schema.LessonError("lint errors:\n- " + "\n- ".join(rep["errors"]))
    meta = L["meta"]
    W, Hh = ASPECTS.get(meta.get("aspect", "4:3"), ASPECTS["4:3"])
    out = Path(out_dir or lesson_path.parent / "build")
    proj = out / "hf"
    vo_dir = out / "vo"
    for d in (proj / "compositions", proj / "assets", vo_dir):
        d.mkdir(parents=True, exist_ok=True)
    # 1. narration
    v_name, speed = meta.get("voice", "bm_george"), float(meta.get("speed", 0.95))
    durs, times = {}, {}
    for b in L["beats"]:
        p = vo_dir / f"{b['id']}.wav"
        durs[b["id"]] = voice.synth(b["narration"], p, v_name, speed, pronounce=L.get("pronounce"))
        times[b["id"]] = voice.word_times(b["narration"], durs[b["id"]])
        log(f"  voice {b['id']}: {durs[b['id']]:.1f}s")
    timing = plan_timing(L, durs)
    total = round(timing[-1]["start"] + timing[-1]["dur"], 3)
    # 2. narration track + score -> mix
    sr = voice.SR
    track = np.zeros(int(sr * (total + 1)), dtype="float32")
    import soundfile as sf

    for tm in timing:
        y, _ = sf.read(str(vo_dir / f"{tm['id']}.wav"), dtype="float32")
        s = int((tm["start"] + LEAD) * sr)
        track[s:s + len(y)] += y[: max(0, len(track) - s)]
    narr_wav = out / "narration.wav"
    sf.write(str(narr_wav), track[: int(sr * total)], sr)
    bed = music.bed(total, out / "score.wav", mood=meta.get("music", "reflective"))
    mix_stems([{"file": str(narr_wav), "role": "voice"}, {"file": str(bed), "role": "music", "gain_db": -3}],
                    total, str(proj / "assets" / "mix.wav"), voice_lufs=-16.0, target_lufs=-16.0)
    # 3. scenes
    look = Look(brand(), W, Hh)
    H.ensure_gsap(proj / "assets" / "vendor")
    grain_png(proj / "assets" / "grain.png")
    hosts = []
    for i, (b, tm) in enumerate(zip(L["beats"], timing)):
        sid = b["id"]
        wt = times[sid]

        def cue(word: str, default: float, wt=wt) -> float:
            if not word:
                return default
            return LEAD + voice.find_word(wt, word, default - LEAD)

        (proj / "compositions" / f"{sid}.html").write_text(
            scene_file(look, sid, b["visual"], tm["dur"], cue, LEAD + tm["narr"], last=i == len(L["beats"]) - 1))
        hosts.append(f'<div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
                     f'data-start="{tm["start"]:.3f}" data-duration="{tm["dur"]:.3f}" data-track-index="{10 + i % 2}" '
                     f'data-track-kind="graphics" data-width="{W}" data-height="{Hh}" style="z-index:10"></div>')
    series = meta.get("series", "")
    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={Hh}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {Hh}px; overflow: hidden; background: {look.bg}; }}
      #bg {{ background: radial-gradient(120% 90% at 30% 20%, #1c1a18 0%, {look.bg} 60%, #050505 100%); }}
      #glow {{ background: radial-gradient(closest-side, {look.accent}22, transparent); }}
      #grain {{ background-image: url('assets/grain.png'); background-repeat: repeat; opacity: 0.06; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{Hh}" data-fps="30">
      <div id="bg" class="clip" data-start="0" data-duration="{total:.3f}" data-track-index="0" data-layout-ignore style="z-index:0"></div>
      <div id="glow" class="clip" data-start="0" data-duration="{total:.3f}" data-track-index="1" data-layout-ignore style="z-index:1"></div>
      <div id="grain" class="clip" data-start="0" data-duration="{total:.3f}" data-track-index="2" data-layout-ignore style="z-index:30"></div>
      <div id="chrome" data-composition-id="chrome" data-composition-src="compositions/chrome.html" data-start="0" data-duration="{total:.3f}" data-track-index="3" data-track-kind="graphics" data-width="{W}" data-height="{Hh}" style="z-index:20"></div>
      {chr(10).join('      ' + h for h in hosts)}
      <audio id="mix" class="clip" src="assets/mix.wav" data-start="0" data-duration="{total:.3f}" data-track-index="5" data-volume="1"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#glow", {{ opacity: 0.4 }}, {{ opacity: 0.9, duration: {total / 2:.2f}, ease: "sine.inOut" }}, 0);
      tl.fromTo("#glow", {{ opacity: 0.9 }}, {{ opacity: 0.4, duration: {total / 2:.2f}, ease: "sine.inOut", immediateRender: false }}, {total / 2:.2f});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (proj / "compositions" / "chrome.html").write_text(f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    #chrome-rail {{ position: absolute; left: {look.px(0.05)}px; top: {look.px(0.045)}px; font-family: '{brand()['font']}';
      font-weight: 700; font-size: {look.fs(0.026)}px; letter-spacing: 0.28em; text-transform: uppercase; color: {look.muted}; }}
    #chrome-prog {{ position: absolute; left: 0; bottom: 0; width: {W}px; height: 6px; background: {look.accent}; transform-origin: 0 50%; }}
  </style>
  <div id="root" data-composition-id="chrome" data-width="{W}" data-height="{Hh}">
    <div id="chrome-rail">{series}</div>
    <div id="chrome-prog" data-layout-ignore></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#chrome-prog", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total:.2f}, ease: "none" }}, 0);
    // the title and end cards carry the series name themselves: the rail shows only in between
    tl.fromTo("#chrome-rail", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6, ease: "power2.out" }}, {timing[0]['dur']:.2f});
    tl.fromTo("#chrome-rail", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.5, ease: "power2.in", immediateRender: false }}, {timing[-1]['start'] - 0.2:.2f});
    window.__timelines["chrome"] = tl;
  </script>
</template>
""")
    (proj / "index.html").write_text(index)
    (proj / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "assets": "assets"}}, indent=2))
    (out / "timing.json").write_text(json.dumps({"total": total, "beats": timing}, indent=1))
    result = {"project": str(proj), "duration": total, "lint": rep, "timing": timing}
    # 4. gates (+ snapshots at the middle of every scene) and render
    mids = [tm["start"] + min(tm["dur"] - 0.3, max(1.2, tm["dur"] * 0.6)) for tm in timing]
    log(f"  checking {len(timing)} scenes, {total:.1f}s")
    result["gates"] = H.gates(proj, mids)
    if render:
        name = Path(lesson_path).parent.name
        target = out / f"{name}_{meta.get('aspect', '4:3').replace(':', 'x')}{'' if render == 'final' else '_draft'}.mp4"
        log(f"  rendering ({render}) -> {target}")
        H.render(proj, target, render)
        info = ff.probe(target)
        result.update(video=str(target), video_info={"w": info.width, "h": info.height, "duration": info.duration},
                      loudness=A.measure(target))
    (out / "build.json").write_text(json.dumps({k: v for k, v in result.items() if k != "gates"}, indent=1, default=str))
    return result


def script_markdown(L: dict) -> str:
    """The approval view: beat table, principles, facts and sources."""
    rows = ["| # | act | narration | on screen |", "|---|---|---|---|"]
    for b in L["beats"]:
        v = b["visual"]
        screen = v.get("title") or v.get("text") or v.get("name") or v.get("question") or v.get("label") or v["type"]
        flag = f" _({b['certainty']})_" if b.get("certainty") in ("disputed", "attributed", "estimate") else ""
        rows.append(f"| {b['id']} | {b['act']} | {b['narration']}{flag} | {v['type']}: {screen} |")
    rep = schema.lint(L)
    out = [f"# {L['meta']['title']}", f"_{L['meta'].get('series', '')} · {rep['stats']['words']} words · "
           f"~{rep['stats']['est_minutes']} min · {L['meta'].get('aspect', '4:3')}_", "",
           "## Learning goals", *[f"- {g}" for g in L["meta"].get("learning_goals", [])], "",
           "## Principles", *[f"{i + 1}. **{p['name']}** — {p.get('line', '')}" for i, p in enumerate(L.get("principles", []))], "",
           "## Script", *rows, "", "## Sources", *[f"- [{s['id']}] {s['cite']}" + (f" — {s['url']}" if s.get('url') else '')
                                                     for s in L.get("sources", [])], "",
           "## Lint", *[f"- ERROR: {e}" for e in rep["errors"]], *[f"- warning: {w}" for w in rep["warnings"]]]
    return "\n".join(out) + "\n"
