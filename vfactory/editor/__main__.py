"""python -m vfactory.editor <command>

  doctor                         verify every tool, skill and config (the setup checklist)
  new FILE [--name N]            create a project with a protected copy of FILE
  prepare PROJECT [--words W]    transcribe + plan takes/pauses/topics -> working/plan.md
  edit PROJECT --platform P --style S [--cta C] [--final] [--part N]
  brand show | brand set --primary #RRGGBB --secondary #RRGGBB --font NAME [--logo PATH]
  brand discover [DIR...]        look for existing brand guides, logos, fonts, B-roll kits
  pref KEY VALUE                 save a stable preference (pace, caption_size, caption_words, ...)
  taste "what they said" [--set key=value] [--scope global|project]
  test [--out DIR]               7 s 9:16 branded caption test through lint/check/snapshot/render
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import brand as B
from . import pipeline, workspace


def _ver(cmd: list[str]) -> str | None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        return (p.stdout or p.stderr).strip().splitlines()[0] if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def doctor(check_whisper: bool = True) -> dict:
    res: dict = {}
    ffv = _ver(["ffmpeg", "-version"])
    res["ffmpeg"] = {"ok": bool(ffv), "version": ffv}
    nv = _ver(["node", "--version"])
    major = int(re.sub(r"[^\d.]", "", nv or "0").split(".")[0] or 0) if nv else 0
    res["node"] = {"ok": major >= 22, "version": nv, "need": ">=22 (HyperFrames)"}
    res["npm"] = {"ok": bool(_ver(["npm", "--version"])), "version": _ver(["npm", "--version"])}
    res["npx"] = {"ok": bool(_ver(["npx", "--version"])), "version": _ver(["npx", "--version"])}
    res["git"] = {"ok": bool(_ver(["git", "--version"])), "version": _ver(["git", "--version"])}
    w = {"ok": False}
    try:
        import faster_whisper  # type: ignore

        w["package"] = f"faster-whisper {faster_whisper.__version__}"
        if check_whisper:
            import os

            from faster_whisper import WhisperModel  # type: ignore

            model = os.environ.get("VIDEO_EDITOR_WHISPER_MODEL", "small")
            try:
                WhisperModel(model, device="cpu", compute_type="int8")
                w.update(ok=True, model=model)
            except Exception as e:
                w["error"] = f"model '{model}' unavailable: {type(e).__name__}: {str(e)[:160]}"
    except ImportError:
        w["error"] = "faster-whisper not installed"
    res["whisper"] = w
    hv = _ver(["npx", "--yes", "hyperframes", "--version"])
    res["hyperframes"] = {"ok": bool(hv), "version": hv}
    chrome = _ver(["npx", "--yes", "hyperframes", "browser", "path"])
    res["chrome"] = {"ok": bool(chrome and Path(chrome.split()[-1]).exists()), "path": chrome}
    skills = Path.home() / ".claude" / "skills"
    hfs = {n: (skills / n / "SKILL.md").is_file() for n in ("hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use")}
    res["hyperframes_skills"] = {"ok": all(hfs.values()), **hfs}
    ve = skills / "video-editor" / "SKILL.md"
    res["video_editor_skill"] = {"ok": ve.is_file(), "path": str(ve)}
    b = B.load_brand()
    res["brand"] = {"ok": B.brand_complete(b), "path": str(B.config_dir() / "brand.json"),
                    "values": {k: b.get(k) for k in B.BRAND_KEYS}}
    root = workspace.default_root()
    res["workspace"] = {"ok": workspace.is_cloud_synced(root) is None, "path": str(root),
                        "cloud": workspace.is_cloud_synced(root)}
    res["ok"] = all(v.get("ok") for k, v in res.items() if isinstance(v, dict))
    return res


def test_composition(out_dir: Path) -> dict:
    """A 7 s vertical caption test in the saved brand: lint -> check -> snapshot -> render, then verify the file."""
    from . import hyperframes as H

    b = B.load_brand()
    if not B.brand_complete(b):
        raise pipeline.NeedsInput("brand not set")
    proj = Path(out_dir) / "hf_test_7s"
    if proj.exists():
        shutil.rmtree(proj)
    words, t = [], 2.15
    for w in "Your raw recording becomes a finished reel.".split():
        words.append({"word": w, "start": round(t, 2), "end": round(t + 0.3, 2)})
        t += 0.36
    H.build_project(proj, width=1080, height=1920, duration=7.0, background=(b["secondary_color"], "#0B0B0F"),
                    words=words, brand=b, prefs=B.load_prefs(), band=(0.60, 0.69),
                    cards=[{"id": "hook", "start": 0, "duration": 2.0, "lines": ["Pipeline", "test"], "kicker": "video editor"},
                           {"id": "cta", "start": 4.4, "duration": 2.6, "lines": ["Ready", "to edit"], "exit": False}])
    g = H.gates(proj, [0.0, 2.6, 3.6, 6.5])
    draft = H.render(proj, proj / "test_draft.mp4", "draft")
    final = H.render(proj, Path(out_dir) / "video-editor-test_7s_9x16.mp4", "final")
    from .. import ffmpeg as ff

    info = ff.probe(final)
    return {"project": str(proj), "lint": g["lint"], "check": {k: (v["ok"], v["errors"], v["warnings"]) for k, v in g["check"]["sections"].items()},
            "snapshots": g["snapshot"].get("contactSheets"), "draft": str(draft), "final": str(final),
            "final_info": {"width": info.width, "height": info.height, "duration": info.duration, "bytes": final.stat().st_size}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m vfactory.editor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("doctor"); p.add_argument("--no-whisper", action="store_true")
    p = sub.add_parser("new"); p.add_argument("file"); p.add_argument("--name"); p.add_argument("--root")
    p = sub.add_parser("prepare"); p.add_argument("project"); p.add_argument("--words"); p.add_argument("--model")
    p.add_argument("--language"); p.add_argument("--pace", choices=["tight", "natural", "relaxed"]); p.add_argument("--no-split", action="store_true")
    p = sub.add_parser("edit"); p.add_argument("project"); p.add_argument("--platform", required=True)
    p.add_argument("--style", required=True, choices=pipeline.STYLES); p.add_argument("--cta"); p.add_argument("--part", type=int)
    p.add_argument("--final", action="store_true"); p.add_argument("--words")
    p = sub.add_parser("brand"); p.add_argument("action", choices=["show", "set", "discover"]); p.add_argument("dirs", nargs="*")
    p.add_argument("--primary"); p.add_argument("--secondary"); p.add_argument("--font"); p.add_argument("--logo")
    p.add_argument("--caption-accent"); p.add_argument("--text-color")
    p = sub.add_parser("pref"); p.add_argument("key"); p.add_argument("value")
    p = sub.add_parser("taste"); p.add_argument("said"); p.add_argument("--set", action="append", default=[])
    p.add_argument("--scope", default="global", choices=["global", "project"])
    p = sub.add_parser("test"); p.add_argument("--out")
    a = ap.parse_args(argv)

    if a.cmd == "doctor":
        r = doctor(not a.no_whisper)
        for k, v in r.items():
            if isinstance(v, dict):
                print(f"[{'x' if v.get('ok') else ' '}] {k:20s} {json.dumps({x: y for x, y in v.items() if x != 'ok'}, ensure_ascii=False)}")
        print("ALL OK" if r["ok"] else "NOT READY")
        return 0 if r["ok"] else 1
    if a.cmd == "new":
        proj = workspace.new_project(a.file, a.name, a.root)
        print(proj)
        return 0
    if a.cmd == "prepare":
        r = pipeline.prepare(Path(a.project), a.model, a.language, a.words, a.pace, not a.no_split)
        print((Path(a.project) / "working" / "plan.md").read_text())
        return 0
    if a.cmd == "edit":
        try:
            prep = pipeline.prepare(Path(a.project), words=a.words) if a.words else None
            res = pipeline.edit(Path(a.project), platform=a.platform, cta=a.cta, style=a.style, part=a.part,
                                quality="final" if a.final else "draft", prepared=prep)
        except pipeline.NeedsInput as e:
            print(f"NEEDS INPUT: {e}", file=sys.stderr)
            return 3
        for r in res:
            print(f"{r['final_path']}\n  {r['duration']:.2f}s {r['resolution']} ({r['aspect']})  report: {r['report']}")
            for w in r["warnings"]:
                print("  ! " + w)
        return 0
    if a.cmd == "brand":
        if a.action == "show":
            print(json.dumps(B.load_brand(), indent=2))
        elif a.action == "set":
            if not (a.primary and a.secondary and a.font):
                print("brand set needs --primary, --secondary and --font", file=sys.stderr)
                return 2
            print(B.save_brand(a.primary, a.secondary, a.font, logo=a.logo, caption_accent=a.caption_accent,
                               text_color=a.text_color))
        else:
            roots = a.dirs or [str(Path.cwd()), str(Path.home() / ".claude" / "skills")]
            print(json.dumps(B.discover_brand(roots), indent=1))
            kit = B.find_broll_kit(roots)
            print("B-roll kit:", kit, json.dumps(B.index_broll(kit), indent=1) if kit else "")
        return 0
    if a.cmd == "pref":
        v: object = a.value
        if a.value.lower() in ("true", "false"):
            v = a.value.lower() == "true"
        elif re.fullmatch(r"-?\d+(\.\d+)?", a.value):
            v = float(a.value) if "." in a.value else int(a.value)
        print(B.save_pref(a.key, v))
        return 0
    if a.cmd == "taste":
        sets = dict(s.split("=", 1) for s in a.set)
        print(B.add_taste(a.said, sets=sets, scope=a.scope))
        return 0
    if a.cmd == "test":
        out = Path(a.out) if a.out else workspace.ensure_root() / "tests"
        out.mkdir(parents=True, exist_ok=True)
        print(json.dumps(test_composition(out), indent=1))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
