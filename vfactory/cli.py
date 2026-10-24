"""vfactory command line.

  vfactory looks                                   list the looks
  vfactory analyze FOOTAGE_DIR [--music M]         -> edit/analysis.json + analysis.md
  vfactory direct FOOTAGE_DIR --look L --title T   -> edit/recipe.json (heuristic first cut)
  vfactory render RECIPE [--preview]               -> final.mp4 + work/report.json
  vfactory qa VIDEO [--report work/report.json]    -> contact sheet + loudness/black checks
  vfactory auto FOOTAGE_DIR --look L --title T     analyze + direct + render + qa in one go
  vfactory demo [--look L|all]                     synthetic footage -> finished films
  vfactory title --look L --text T                 render just a title animation (.mov + stills)
  vfactory vision VIDEO [--detail balanced]        reading view for a video: report.md + labelled frames
  vfactory vision-timeline VIDEO START END         filmstrip + waveform drill-down around a moment
  vfactory trends "QUERY" [--days 30]              multi-source trend brief (Reddit, HN, YouTube, GitHub)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import analyze, autoedit, ffmpeg as ff, qa, styles
from . import recipe as R

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".mts"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _sources(folder: Path) -> dict[str, str]:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in VIDEO_EXT and not p.name.startswith(("final", "work_")))
    keys = {}
    for p in files:
        k = "".join(c if c.isalnum() else "_" for c in p.stem)[:24] or "clip"
        while k in keys:
            k += "_"
        keys[k] = str(p.resolve())
    return keys


def cmd_looks(a) -> int:
    for name, look in styles.LOOKS.items():
        print(f"{name:12s} {look.tagline}")
        print(f"{'':12s} type={look.type.display}/{look.type.kicker}  title={look.title_anim}  "
              f"grade={'yes' if look.grade else 'none'}  letterbox={look.letterbox}  grain={look.grain}  "
              f"transitions={'/'.join(dict.fromkeys(look.transitions))}")
    return 0


def _edit_dir(folder: Path) -> Path:
    d = folder / "edit"
    d.mkdir(exist_ok=True)
    return d


def cmd_analyze(a) -> int:
    folder = Path(a.footage)
    srcs = _sources(folder)
    if not srcs:
        print(f"no video files in {folder}", file=sys.stderr)
        return 2
    res = analyze.analyze_all(srcs, a.music)
    d = _edit_dir(folder)
    analyze.save(res, d / "analysis.json")
    (d / "analysis.md").write_text(analyze.summarize(res))
    print(analyze.summarize(res))
    return 0


def _direct(a) -> tuple[dict, Path]:
    folder = Path(a.footage)
    d = _edit_dir(folder)
    cache = d / "analysis.json"
    if cache.exists() and not getattr(a, "reanalyze", False):
        res = json.loads(cache.read_text())
    else:
        res = analyze.analyze_all(_sources(folder), a.music)
        analyze.save(res, cache)
        (d / "analysis.md").write_text(analyze.summarize(res))
    if a.music and not res.get("music"):
        res["music"] = asdict(analyze.analyze_music(a.music))
        analyze.save(res, cache)
    ending = {"title": a.title, "tagline": a.tagline or a.subtitle or "", "cta": a.cta or "", "handle": a.handle or "",
              "credits": [c.split("=", 1) for c in (a.credit or [])]}
    rec = autoedit.direct(res, look_name=a.look, title=a.title, kicker=a.kicker or "", subtitle=a.subtitle or "",
                          target=a.length, aspect=a.aspect, fps=a.fps, music=str(Path(a.music).resolve()) if a.music else None,
                          ending=ending)
    if a.words:
        rec["captions"] = {"words": str(Path(a.words).resolve())}
    rec["output"] = str((folder / f"final_{a.look}_{a.aspect.replace(':', 'x')}.mp4").resolve())
    path = d / f"recipe_{a.look}.json"
    R.dump(rec, path)
    return rec, path


def cmd_direct(a) -> int:
    rec, path = _direct(a)
    print(f"recipe -> {path}")
    from .render import plan_preview

    for p in plan_preview(path):
        print(f"  {p['out_start']:7.2f}s {p['kind']:10s} {p.get('source') or '':12s} {p.get('transition'):9s} {p.get('beat') or ''}")
    return 0


def cmd_render(a) -> int:
    from .render import render

    ff.VERBOSE = a.verbose
    rep = render(a.recipe, preview=a.preview)
    if not a.no_qa:
        res = qa.check(rep["output"], rep)
        _print_qa(res)
    return 0


def _print_qa(res: dict) -> None:
    print(f"QA: {'PASS' if res['passed'] else 'ISSUES'}  {res['duration']}s  {res['integrated_lufs']} LUFS  "
          f"TP {res['true_peak_dbfs']} dBFS")
    for i in res["issues"]:
        print("  ! " + i)
    print(f"  contact sheet: {res['contact_sheet']}")


def cmd_qa(a) -> int:
    rep = json.loads(Path(a.report).read_text()) if a.report else None
    _print_qa(qa.check(a.video, rep))
    return 0


def cmd_auto(a) -> int:
    from .render import render

    ff.VERBOSE = a.verbose
    rec, path = _direct(a)
    print(f"recipe -> {path}")
    rep = render(path, preview=a.preview)
    _print_qa(qa.check(rep["output"], rep))
    return 0


def cmd_demo(a) -> int:
    from . import demo
    from .render import render

    out = Path(a.out)
    media = demo.make_all(out / "footage")
    looks = list(styles.LOOKS) if a.look == "all" else [a.look]
    for look in looks:
        for mode in a.mode.split(","):
            if mode == "montage":
                srcs = {Path(p).stem: p for p in media["broll"]}
                res = analyze.analyze_all(srcs, media["music"])
                rec = autoedit.direct(res, look_name=look, title="The Long Road Home", kicker="A Northlight Film",
                                      subtitle="Nine days. One question.", aspect=a.aspect, music=media["music"],
                                      ending={"title": "The Long Road Home", "tagline": "In cinemas this winter",
                                              "cta": "Watch the trailer", "handle": "northlight.studio",
                                              "credits": [["Directed by", "Mai Tran"], ["Music by", "Leo Park"]]})
            else:
                srcs = {"talk": media["talk"], **{Path(p).stem: p for p in media["broll"][:2]}}
                res = analyze.analyze_all(srcs, media["music"])
                rec = autoedit.direct(res, look_name=look, title="What the Road Remembers", kicker="Episode 01",
                                      aspect=a.aspect, music=media["music"],
                                      lower_thirds=[{"segment": "first_voice", "offset": 0.4, "name": "Mai Tran", "role": "Director"}],
                                      ending={"title": "What the Road Remembers", "tagline": "New episodes every Friday",
                                              "cta": "Subscribe", "handle": "northlight.studio"})
                rec["captions"] = {"words": media["words"]}
            rec["output"] = str((out / f"demo_{mode}_{look}_{a.aspect.replace(':', 'x')}.mp4").resolve())
            rpath = out / f"recipe_{mode}_{look}.json"
            R.dump(rec, rpath)
            rep = render(rpath, preview=a.preview)
            _print_qa(qa.check(rep["output"], rep))
    return 0


def cmd_title(a) -> int:
    from .motion.titles import make_title

    look = styles.get(a.look)
    W, H = R.ASPECTS[a.aspect]
    anim = make_title(look, W, H, a.fps, a.duration, a.text, a.kicker or "", a.subtitle or "", card=a.card, anim=a.anim)
    out = Path(a.out or (f"title_{a.look}.mp4" if a.card else f"title_{a.look}.mov"))
    anim.render(out)
    for k, t in enumerate((anim.intro * 0.4, anim.intro + 0.2, anim.duration - anim.outro * 0.5)):
        anim.still(t, out.with_name(f"{out.stem}_{k}.png"))
    print(f"title -> {out} ({anim.duration:.2f}s, hits at {', '.join(f'{h:.2f}' for h in anim.hits)})")
    return 0


def cmd_vision(a) -> int:
    from . import vision

    cues = [vision.parse_time(x) for x in a.cues.split(",")] if a.cues else None
    res = vision.investigate(a.video, detail=a.detail, cues=cues, start=vision.parse_time(a.start) if a.start else None,
                             end=vision.parse_time(a.end) if a.end else None, width=a.width, words=a.words, out_dir=a.out)
    print(Path(res["report"]).read_text())
    return 0


def cmd_vision_timeline(a) -> int:
    from . import vision
    from .captions import load_words

    s, e = vision.parse_time(a.start), vision.parse_time(a.end)
    out = Path(a.out or Path(a.video).with_name(f"{Path(a.video).stem}_timeline_{s:.1f}-{e:.1f}.png"))
    vision.timeline_view(a.video, s, e, out, words=load_words(a.words) if a.words else None, n=a.n)
    print(out)
    return 0


def cmd_trends(a) -> int:
    from . import trends

    items = trends.load_items(a.from_json) if a.from_json else None
    res = trends.research(a.query, days=a.days, sources=a.sources.split(",") if a.sources else None,
                          subreddits=a.subreddit, items_in=items)
    j, m = trends.save(res, a.out)
    print(m.read_text())
    print(f"saved: {m}  {j}")
    return 0


def _direct_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("footage", help="folder with source clips")
    p.add_argument("--look", default="prestige", choices=list(styles.LOOKS))
    p.add_argument("--title", default=None)
    p.add_argument("--kicker", default=None, help="small overline, e.g. 'A Northlight Film'")
    p.add_argument("--subtitle", default=None)
    p.add_argument("--tagline", default=None)
    p.add_argument("--cta", default=None)
    p.add_argument("--handle", default=None)
    p.add_argument("--credit", action="append", help="'Directed by=Name' (repeatable)")
    p.add_argument("--music", default=None)
    p.add_argument("--words", default=None, help="word-timing JSON for captions")
    p.add_argument("--length", type=float, default=None, help="target body length in seconds (montage)")
    p.add_argument("--aspect", default="16:9", choices=list(R.ASPECTS))
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--reanalyze", action="store_true")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vfactory", description="AI video factory: footage -> studio-grade edit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("looks").set_defaults(fn=cmd_looks)
    p = sub.add_parser("analyze"); p.add_argument("footage"); p.add_argument("--music"); p.set_defaults(fn=cmd_analyze)
    p = sub.add_parser("direct"); _direct_args(p); p.set_defaults(fn=cmd_direct)
    p = sub.add_parser("render"); p.add_argument("recipe"); p.add_argument("--preview", action="store_true")
    p.add_argument("--no-qa", action="store_true"); p.add_argument("-v", "--verbose", action="store_true"); p.set_defaults(fn=cmd_render)
    p = sub.add_parser("qa"); p.add_argument("video"); p.add_argument("--report"); p.set_defaults(fn=cmd_qa)
    p = sub.add_parser("auto"); _direct_args(p); p.add_argument("--preview", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true"); p.set_defaults(fn=cmd_auto)
    p = sub.add_parser("demo"); p.add_argument("--look", default="prestige", choices=[*styles.LOOKS, "all"])
    p.add_argument("--mode", default="montage", help="montage,talk"); p.add_argument("--aspect", default="16:9", choices=list(R.ASPECTS))
    p.add_argument("--out", default="demo_out"); p.add_argument("--preview", action="store_true"); p.set_defaults(fn=cmd_demo)
    p = sub.add_parser("title"); p.add_argument("--look", default="prestige", choices=list(styles.LOOKS)); p.add_argument("--text", required=True)
    p.add_argument("--kicker"); p.add_argument("--subtitle"); p.add_argument("--anim", choices=["tracking_reveal", "mask_rise", "slam", "type_on", "serif_fade"])
    p.add_argument("--aspect", default="16:9", choices=list(R.ASPECTS)); p.add_argument("--fps", type=int, default=30)
    p.add_argument("--duration", type=float, default=4.5); p.add_argument("--card", action="store_true"); p.add_argument("--out")
    p.set_defaults(fn=cmd_title)
    p = sub.add_parser("vision"); p.add_argument("video"); p.add_argument("--detail", default="balanced", choices=["efficient", "balanced", "deep"])
    p.add_argument("--cues", help="comma-separated timestamps to always include (SS, MM:SS)")
    p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--width", type=int, default=640)
    p.add_argument("--words", help="word-timing JSON to include as transcript"); p.add_argument("--out"); p.set_defaults(fn=cmd_vision)
    p = sub.add_parser("vision-timeline"); p.add_argument("video"); p.add_argument("start"); p.add_argument("end")
    p.add_argument("--words"); p.add_argument("--n", type=int, default=8); p.add_argument("--out"); p.set_defaults(fn=cmd_vision_timeline)
    p = sub.add_parser("trends"); p.add_argument("query"); p.add_argument("--days", type=int, default=30)
    p.add_argument("--sources", help="comma list: reddit,hackernews,youtube,github"); p.add_argument("--subreddit", action="append")
    p.add_argument("--from-json", help="re-score a saved items file (offline)"); p.add_argument("--out", default="research")
    p.set_defaults(fn=cmd_trends)
    a = ap.parse_args(argv)
    return a.fn(a)
