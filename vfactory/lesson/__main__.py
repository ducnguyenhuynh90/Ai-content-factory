"""python -m vfactory.lesson <command>

  new DIR --title T [--series S] [--topic investing] [--angle history|person|concept]   scaffold a lesson.json
  lint LESSON.json                 learning-science + fact checks; writes script.md (the approval view)
  build LESSON.json [--draft|--final|--no-render] [--force]   voice -> scenes -> mix -> check -> render
  gate LESSON.json --out BUILD_DIR [--no-check] [--no-listen]   objective checks + evidence for the video-gatekeeper
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import build, schema

TEMPLATE = {
    "meta": {"series": "", "title": "", "subtitle": "", "topic": "investing", "angle": "history", "audience": "curious beginners",
             "aspect": "4:3", "target_minutes": [3, 5], "voice": "bm_george", "speed": 0.95, "music": "reflective",
             "disclaimer": "Educational content only, not financial advice.", "learning_goals": []},
    "sources": [],
    "principles": [],
    "beats": [
        {"id": "b01", "act": "hook", "narration": "", "visual": {"type": "title", "title": "", "kicker": ""}},
    ],
    "pronounce": {},
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m vfactory.lesson")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("dir"); p.add_argument("--title", required=True); p.add_argument("--series", default="")
    p.add_argument("--topic", default="investing"); p.add_argument("--angle", default="history")
    p = sub.add_parser("lint"); p.add_argument("lesson")
    p = sub.add_parser("build"); p.add_argument("lesson"); p.add_argument("--out")
    g = p.add_mutually_exclusive_group(); g.add_argument("--final", action="store_true"); g.add_argument("--no-render", action="store_true")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("gate"); p.add_argument("lesson"); p.add_argument("--out", required=True)
    p.add_argument("--no-check", action="store_true"); p.add_argument("--no-listen", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "gate":
        from . import gate

        r = gate.run(a.lesson, a.out, check=not a.no_check, listen=not a.no_listen)
        print(json.dumps({k: r[k] for k in ("verdict", "fails", "warnings", "evidence")}, ensure_ascii=False, indent=1))
        return 0 if r["verdict"] != "block" else 3
    if a.cmd == "new":
        d = Path(a.dir)
        d.mkdir(parents=True, exist_ok=True)
        t = json.loads(json.dumps(TEMPLATE))
        t["meta"].update(title=a.title, series=a.series, topic=a.topic, angle=a.angle)
        (d / "lesson.json").write_text(json.dumps(t, indent=2))
        print(d / "lesson.json")
        return 0
    if a.cmd == "lint":
        L = schema.load(a.lesson)
        rep = schema.lint(L)
        md = Path(a.lesson).with_name("script.md")
        md.write_text(build.script_markdown(L))
        print(json.dumps(rep["stats"], indent=1))
        for e in rep["errors"]:
            print("ERROR  " + e)
        for w in rep["warnings"]:
            print("warn   " + w)
        print(f"approval view: {md}")
        return 1 if rep["errors"] else 0
    if a.cmd == "build":
        mode = None if a.no_render else ("final" if a.final else "draft")
        try:
            r = build.build(a.lesson, a.out, force=a.force, render=mode)
        except schema.LessonError as e:
            print(str(e), file=sys.stderr)
            return 2
        print(json.dumps({k: r[k] for k in ("project", "duration", "video", "video_info", "loudness") if k in r}, indent=1))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
