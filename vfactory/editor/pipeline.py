"""One edit, end to end: protected copy -> transcript -> takes/pauses/topics -> reframe + correction
-> cut -> HyperFrames captions/graphics -> gates -> render -> QA -> edit report."""

from __future__ import annotations

import json
from pathlib import Path

from .. import analyze
from .. import audio as A
from .. import ffmpeg as ff
from . import brand as B
from . import cut, enhance, frame, report, takes, workspace
from . import hyperframes as H
from . import transcribe as T

STYLES = ("clean", "captions", "captions+graphics", "branded")
CTA_LINES = {
    "follow": ["Follow", "for more"], "comment": ["Tell me", "in the comments"], "share": ["Send this", "to a friend"],
    "buy": ["Get yours", "link in bio"], "sign up": ["Sign up", "link in bio"], "visit a link": ["Link", "in bio"],
    "watch another video": ["Watch", "part two"], "remember an idea": [],
}


class NeedsInput(RuntimeError):
    """Something only the director can decide (brand, platform...). The message says what to ask."""


def _target(platform: str) -> tuple[int, int]:
    key = platform.lower().replace(" ", "-").replace("instagram-reels", "reels").replace("youtube-shorts", "shorts")
    if key not in frame.PLATFORMS:
        raise NeedsInput(f"unknown platform '{platform}'. Known: {', '.join(frame.PLATFORMS)}")
    return frame.PLATFORMS[key]


def prepare(proj: Path, model: str | None = None, language: str | None = None, words: str | None = None,
            pace: str | None = None, split: bool = True) -> dict:
    """Transcribe and plan. Writes transcript/ and working/plan.json + plan.md. Safe to re-run (cached)."""
    proj = Path(proj)
    src = workspace.source_copy(proj)
    info = ff.probe(src)
    tr = T.transcribe(src, proj / "transcript", model=model, language=language, words_override=words)
    energy = []
    if info.has_audio:
        energy = list(analyze.rms_envelope(ff.read_audio_mono(src, 16000), 16000, 0.25))
    prefs = B.load_prefs()
    plans = takes.plan(tr["words"], energy=energy, pace=pace or prefs["pace"], fps=info.fps or 30, split=split)
    (proj / "working" / "plan.json").write_text(json.dumps(plans, indent=1, ensure_ascii=False, default=str))
    (proj / "working" / "plan.md").write_text(plan_markdown(plans, info.duration))
    return {"plans": plans, "transcript": tr, "info": info}


def plan_markdown(plans: list[dict], src_dur: float) -> str:
    L = [f"# Edit plan ({len(plans)} video{'s' if len(plans) > 1 else ''} found in {src_dur:.1f} s)", ""]
    for p in plans:
        L.append(f"## Part {p['part']}: “{p['title_hint']}…” → {p['duration']:.1f} s")
        for d in p["decisions"]:
            flag = "  ⚠ LOW CONFIDENCE — please choose" if d["flagged"] else ""
            L.append(f"- keep [{T.fmt(d['chosen']['start'])}] {d['chosen']['text']}{flag}")
            for a in d["alternatives"]:
                L.append(f"  - drop [{T.fmt(a['start'])}] {a['text']}")
        for m in p["restart_markers"]:
            L.append(f"- remove restart phrase [{T.fmt(m['start'])}] “{m['text']}”")
        L.append(f"- tighten {len(p['pauses_tightened'])} long pauses")
        L.append("")
    return "\n".join(L)


def map_words(words: list[dict], segments: list[dict]) -> list[dict]:
    out, t = [], 0.0
    for s in segments:
        for w in words:
            if w["start"] >= s["start"] - 1e-3 and w["end"] <= s["end"] + 0.05:
                out.append({"word": w["word"], "start": round(t + w["start"] - s["start"], 3),
                            "end": round(t + min(w["end"], s["end"]) - s["start"], 3)})
        t += s["end"] - s["start"]
    return out


def edit(proj: Path, *, platform: str, cta: str | None, style: str, part: int | None = None, quality: str = "draft",
         prepared: dict | None = None) -> list[dict]:
    proj = Path(proj)
    if style not in STYLES:
        raise NeedsInput(f"style must be one of {STYLES}")
    brand = B.load_brand()
    prefs = B.load_prefs()
    if style != "clean" and not B.brand_complete(brand):
        raise NeedsInput("brand identity is not set: ask once for primary colour, secondary colour and font, "
                         "then `python -m vfactory.editor brand set ...`")
    W, Hh = _target(platform)
    meta = workspace.load(proj)
    src = str(workspace.source_copy(proj))
    prep = prepared or prepare(proj)
    info = prep["info"]
    plans = [p for p in prep["plans"] if part is None or p["part"] == part]
    faces = frame.track_faces(src, info.duration, info.width, info.height)
    (proj / "working" / "faces.json").write_text(json.dumps(faces.to_dict()))
    rf = frame.plan_reframe(info.width, info.height, W, Hh)
    pic = enhance.picture_correction(enhance.measure_picture(src, info.duration))
    silences = analyze.detect_silences(src) if info.has_audio else []
    aud = enhance.measure_audio(src, silences) if info.has_audio else None
    results = []
    for p in plans:
        name = f"{workspace.slug(p['title_hint'] or 'part')[:32]}_p{p['part']}_{workspace.slug(platform)}"
        warnings = list(rf.warnings) + list(pic.warnings)
        if any(d["flagged"] for d in p["decisions"]):
            warnings.append("some take choices were low-confidence: see working/plan.md and confirm")
        if faces.coverage < 0.3:
            warnings.append(f"face found in only {faces.coverage:.0%} of frames: reframe used the centre")
        cut_path = workspace.guard_output(proj / "working" / f"{name}_cut.mp4", proj)
        c = cut.render_cut(src, p["segments"], cut_path, src_w=info.width, src_h=info.height, fps=round(info.fps or 30),
                           reframe=rf, faces=faces, picture_filter=pic.filter, voice_chain=aud.chain if aud else "",
                           has_audio=info.has_audio, punch=prefs.get("jump_cuts", "auto"), quality=quality)
        dur = c["duration"]
        out_dir = proj / ("final" if quality == "final" else "preview")
        out = workspace.guard_output(out_dir / f"{name}{'' if quality == 'final' else '_draft'}.mp4", proj)
        graphics = "none (clean cut)"
        hf_summary = None
        if style == "clean":
            out.write_bytes(Path(c["file"]).read_bytes())
        else:
            words = map_words(p["words_kept"], p["segments"])
            fc = faces.median_center()
            band = frame.caption_band(rf.out_w, rf.out_h, fc[1] if fc else None, fc[2] if fc else None)
            cards = []
            total = dur
            if style in ("captions+graphics", "branded") and cta and CTA_LINES.get(cta.lower(), ["Follow", "for more"]):
                lines = CTA_LINES.get(cta.lower(), [cta])
                cards.append({"id": "cta", "start": dur, "duration": 2.6, "lines": lines, "exit": False})
                total = dur + 2.6
            hf_dir = proj / "working" / f"hf_{name}"
            H.build_project(hf_dir, width=rf.out_w, height=rf.out_h, duration=total, fps=round(info.fps or 30),
                            plate=c["file"], words=words, brand=brand, prefs=prefs, band=band, cards=cards)
            mids = [w["start"] + 0.2 for w in words[:: max(1, len(words) // 4)]][:4] + ([dur + 1.5] if cards else [])
            hf_summary = H.gates(hf_dir, mids)
            H.render(hf_dir, out, quality)
            graphics = f"HyperFrames captions ({prefs.get('caption_words', 3)} words/group, brand font {brand['font']}, " \
                       f"accent {brand.get('caption_accent', brand['primary_color'])})" + (f"; CTA card “{' '.join(cards[0]['lines'])}”" if cards else "")
        m = A.measure(out)
        final_info = ff.probe(out)
        untouched = workspace.verify_original_untouched(proj)
        if not untouched:
            warnings.append("ORIGINAL FILE CHANGED OR MISSING since import (not by this editor): check it")
        data = {
            "output_name": name, "original_filename": meta["original_filename"], "source_copy": meta["source_copy"],
            "platform": platform, "cta": cta, "style": style, "aspect": f"{rf.out_w}:{rf.out_h}",
            "resolution": f"{final_info.width}x{final_info.height}", "duration": final_info.duration,
            "source_duration": info.duration, "final_path": str(out), "decisions": p["decisions"],
            "restart_markers": p["restart_markers"], "pauses_tightened": p["pauses_tightened"],
            "picture": {"verdict": pic.verdict, "corrections": pic.corrections},
            "reframe": f"{info.width}x{info.height} -> crop {rf.crop_w}x{rf.crop_h} -> {rf.out_w}x{rf.out_h}",
            "punch_ins": c["punch_ins"], "audio": {"notes": aud.notes if aud else ["no audio track"]},
            "loudness_lufs": m.get("integrated_lufs"), "true_peak_dbtp": m.get("true_peak_dbfs"),
            "graphics": graphics, "hyperframes": hf_summary and {"lint": hf_summary["lint"], "check_ok": hf_summary["check"]["ok"]},
            "warnings": warnings, "original_untouched": untouched,
        }
        jp, mp = report.write(proj, name, data)
        meta.setdefault("outputs", []).append({"file": str(out), "report": str(mp), "quality": quality})
        workspace.save(proj, meta)
        results.append({**data, "report": str(mp)})
    return results
