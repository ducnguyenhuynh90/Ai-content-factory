"""python -m vfactory.shorts <command>

  init      <channel_dir> --name N --niche "..." [--lang vi] [--handle @x]   create a channel workspace
  new       <channel_dir> --title "..." [--slug s]                           scaffold shorts/NNN-slug/short.json
  lint      <short.json>                                                     TikTok rules -> script.md (approval view)
  build     <short.json> [--final] [--voice V] [--out DIR] [--force]         voice, captions, animation, mix -> mp4
  batch     <channel_dir> [--final] [--only-new]                             build every short in the channel
  package   <short.json>                                                     cover, caption, hashtags, checklist
  log-post  <short.json> --url URL [--video-id ID] [--posted-at ISO]         record a published post
  metrics   import <channel_dir> <export.csv> | add <channel_dir> <slug> --views N ...
  insights  <channel_dir>                                                    rank videos, what to make more of
  voices    [--lang vi]                                                      list neural voices (edge-tts)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def _p(*a):
    print(*a, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vfactory.shorts", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("dir"); s.add_argument("--name", required=True); s.add_argument("--niche", default="")
    s.add_argument("--lang", default="vi"); s.add_argument("--handle", default="")
    s = sub.add_parser("new"); s.add_argument("dir"); s.add_argument("--title", required=True); s.add_argument("--slug")
    s = sub.add_parser("lint"); s.add_argument("short")
    s = sub.add_parser("build"); s.add_argument("short"); s.add_argument("--final", action="store_true")
    s.add_argument("--voice"); s.add_argument("--out"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("batch"); s.add_argument("dir"); s.add_argument("--final", action="store_true")
    s.add_argument("--only-new", action="store_true"); s.add_argument("--voice")
    s = sub.add_parser("package"); s.add_argument("short")
    s = sub.add_parser("log-post"); s.add_argument("short"); s.add_argument("--url", required=True)
    s.add_argument("--video-id", default=""); s.add_argument("--posted-at", default="")
    s = sub.add_parser("metrics"); ms = s.add_subparsers(dest="mcmd", required=True)
    m = ms.add_parser("import"); m.add_argument("dir"); m.add_argument("file")
    m = ms.add_parser("add"); m.add_argument("dir"); m.add_argument("slug")
    for k in ("views", "avg_watch_s", "completion_pct", "likes", "comments", "shares", "saves", "follows"):
        m.add_argument("--" + k.replace("_", "-"), dest=k)
    s = sub.add_parser("insights"); s.add_argument("dir")
    s = sub.add_parser("voices"); s.add_argument("--lang", default="vi")
    a = ap.parse_args(argv)

    from . import analytics, channel, schema

    if a.cmd == "init":
        root = channel.init(a.dir, a.name, a.niche, a.lang, a.handle)
        _p(f"channel ready: {root}\n  edit {root / 'channel.json'} (niche, audience, pillars, voice, theme, hashtags)")
    elif a.cmd == "new":
        _p(channel.new_short(a.dir, a.title, a.slug))
    elif a.cmd == "lint":
        S = schema.load(a.short)
        rep = schema.lint(S)
        md = Path(a.short).with_name("script.md")
        md.write_text(schema.script_markdown(S))
        for e in rep["errors"]:
            _p("ERROR  ", e)
        for w in rep["warnings"]:
            _p("warning", w)
        _p(json.dumps(rep["stats"], ensure_ascii=False), "->", md)
        return 1 if rep["errors"] else 0
    elif a.cmd == "build":
        return _build(a.short, a.final, a.voice, a.out, a.force)
    elif a.cmd == "batch":
        root = Path(a.dir).expanduser()
        rc = 0
        for sj in sorted((root / "shorts").glob("*/short.json")) if (root / "shorts").exists() else sorted(root.glob("*/short.json")):
            bj = sj.parent / "build" / "build.json"
            if a.only_new and bj.exists() and bj.stat().st_mtime > sj.stat().st_mtime:
                continue
            _p(f"== {sj.parent.name}")
            rc |= _build(str(sj), a.final, a.voice, None, False)
        return rc
    elif a.cmd == "package":
        from .package import package
        kit = package(a.short)
        _p(Path(a.short).parent / "publish" / "post.md")
        _p(kit["caption"])
    elif a.cmd == "log-post":
        S = schema.load(a.short)
        root = channel.find_channel(a.short)
        if not root:
            _p("this short is not inside a channel folder (no channel.json above it)")
            return 1
        bj = Path(a.short).parent / "build" / "build.json"
        dur = json.loads(bj.read_text()).get("duration", "") if bj.exists() else ""
        m = S["meta"]
        channel.log_post(root, {"slug": Path(a.short).parent.name, "title": m.get("caption") or m.get("title", ""), "url": a.url,
                                "video_id": a.video_id or _video_id(a.url), "posted_at": a.posted_at or datetime.now().isoformat(timespec="minutes"),
                                "format": m.get("format", ""), "hook_type": m.get("hook_type", ""), "pillar": m.get("pillar", ""),
                                "duration": dur})
        _p(f"logged in {root / 'posts.csv'}")
    elif a.cmd == "metrics":
        if a.mcmd == "import":
            r = analytics.import_export(a.dir, a.file)
            _p(f"imported {r['imported']} rows" + (f"; unmatched (log-post them first): {r['unmatched']}" if r["unmatched"] else ""))
        else:
            analytics.add(a.dir, a.slug, **{k: getattr(a, k) for k in ("views", "avg_watch_s", "completion_pct", "likes",
                                                                          "comments", "shares", "saves", "follows")})
            _p("added")
    elif a.cmd == "insights":
        _p(analytics.insights(a.dir)["markdown"])
    elif a.cmd == "voices":
        from .voice import VOICES
        try:
            import asyncio

            import edge_tts  # type: ignore
            vs = asyncio.run(edge_tts.list_voices())
            for v in vs:
                if v["Locale"].lower().startswith(a.lang.lower()):
                    _p(v["ShortName"], v["Gender"])
        except Exception as e:  # offline or not installed
            _p(f"(could not list voices: {e})")
            for g, v in VOICES.get(a.lang[:2], VOICES["en"]).items():
                _p(v, g)
    return 0


def _video_id(url: str) -> str:
    import re
    m = re.search(r"/video/(\d+)", url)
    return m.group(1) if m else ""


def _build(short: str, final: bool, voice: str | None, out: str | None, force: bool) -> int:
    from . import build, schema
    from .voice import VoiceUnavailable

    sp = Path(short)
    if voice:  # one-off override without touching the file the person approved
        S = json.loads(sp.read_text(encoding="utf-8"))
        S["meta"]["voice"] = voice
        tmp = sp.with_name(".short.override.json")
        tmp.write_text(json.dumps(S, ensure_ascii=False))
        target = tmp
    else:
        target = sp
    try:
        r = build.build(target, out or sp.parent / "build", quality="final" if final else "draft", force=force, log=_p)
    except schema.ShortError as e:
        _p(f"not built: {e}")
        return 1
    except VoiceUnavailable as e:
        _p(f"voice unavailable: {e}\n  try --voice none (music + captions only) or record the beats (beat 'audio': path)")
        return 2
    finally:
        if voice:
            target.unlink(missing_ok=True)
    _p(json.dumps({k: r.get(k) for k in ("video", "video_nomusic", "duration", "loudness", "checks", "render_seconds")},
                  ensure_ascii=False, indent=1))
    return 1 if r["checks"] else 0


if __name__ == "__main__":
    sys.exit(main())
