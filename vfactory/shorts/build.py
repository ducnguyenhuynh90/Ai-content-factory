"""short.json -> voiced, captioned, animated 9:16 MP4 (+ a no-music version, a cover, and a build report)."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import numpy as np

from .. import audio as A
from .. import ffmpeg as ff
from ..editor.enhance import mix_stems
from . import music, schema, voice
from . import render as R

SIZES = {"final": (1080, 1920, 30), "draft": (540, 960, 30)}
TAIL = 0.14            # breath after each line; TikTok pacing is tight
SFX_PER_MIN = 12       # designed sound on visible events only; more reads as a template


def lead_of(i: int, b: dict) -> float:
    return float(b.get("lead", 0.0 if i == 0 else 0.06))  # the hook speaks on frame 0


def plan(S: dict, durs: dict[str, float]) -> list[dict]:
    t, out = 0.0, []
    for i, b in enumerate(S["beats"]):
        v = b["visual"]
        lead, narr = lead_of(i, b), durs[b["id"]]
        d = lead + narr + TAIL if narr else float(v.get("hold", 1.5))
        if v["type"] == "question":
            d += float(v.get("think_seconds", 3.0)) + (1.3 if v.get("answer") else 0.2)
        if v["type"] == "end":
            d = max(d + 0.8, 2.5)
        if v["type"] == "list":
            d += 0.4
        d = max(d, float(v.get("min_seconds", 0.9)))
        out.append({"id": b["id"], "start": round(t, 3), "dur": round(d, 3), "lead": lead, "narr": round(narr, 3)})
        t += d
    return out


def narrate(S: dict, vo_dir: Path, log=print) -> tuple[dict, dict]:
    meta = S["meta"]
    lang = schema.lang_of(S)
    v_name = meta.get("voice", voice.VOICES[lang]["male"])
    durs, times = {}, {}
    for b in S["beats"]:
        p = vo_dir / f"{b['id']}.wav"
        text = b.get("narration", "").strip()
        if not text:
            durs[b["id"]], times[b["id"]] = 0.0, []
            continue
        if b.get("audio"):
            d, wt = voice.from_file(b["audio"], text, p)
        else:
            d, wt = voice.synth(text, p, b.get("voice", v_name), b.get("rate", meta.get("rate", "+0%")),
                                S.get("pronounce"), lang)
        durs[b["id"]], times[b["id"]] = d, wt
        log(f"  voice {b['id']}: {d:.1f}s")
    return durs, times


def build(short_path: str | Path, out_dir: str | Path | None = None, *, quality: str = "draft", force: bool = False,
          log=print) -> dict:
    t_start = time.time()
    short_path = Path(short_path)
    S = schema.load(short_path)
    rep = schema.lint(S)
    if rep["errors"] and not force:
        raise schema.ShortError("lint errors:\n- " + "\n- ".join(rep["errors"]))
    meta = S["meta"]
    lang = schema.lang_of(S)
    out = Path(out_dir or short_path.parent / "build")
    vo_dir = out / "vo"
    vo_dir.mkdir(parents=True, exist_ok=True)
    W, H, fps = SIZES[quality]
    ctx = R.Ctx(W, H, fps, R.theme(meta.get("theme", "night"), meta.get("theme_overrides")), lang)

    # 1. voice + timing
    durs, times = narrate(S, vo_dir, log)
    timing = plan(S, durs)
    total = round(timing[-1]["start"] + timing[-1]["dur"], 3)
    no_voice = voice.provider(meta.get("voice", "x-XX-xNeural")) == "none" and not any(b.get("audio") for b in S["beats"])

    # 2. scenes and their sound events
    end = S["beats"][-1]["visual"]
    if end["type"] == "end" and meta.get("disclaimer") and not end.get("disclaimer"):
        end["disclaimer"] = meta["disclaimer"]
    scenes = [R.Scene(ctx, b, tm["start"], tm["dur"], tm["lead"], tm["narr"], times[b["id"]])
              for b, tm in zip(S["beats"], timing)]
    sfx = []
    for k, sc in enumerate(scenes):
        for e in sc.scene_events():
            sfx.append({**e, "at": round(sc.start + e["at"], 3), "prio": 2})
        if k and scenes[k].v["type"] != scenes[k - 1].v["type"]:
            sfx.append({"kind": "whoosh", "at": round(sc.start + 0.02, 3), "gain_db": -12, "prio": 1})
        for fx in sc.beat.get("sfx", []):
            at = sc.cue(fx.get("cue"), float(fx.get("at", 0.0))) if fx.get("cue") else float(fx.get("at", 0.0))
            sfx.append({"kind": fx.get("kind", "hit"), "at": round(sc.start + at, 3), "gain_db": float(fx.get("gain_db", -4)), "prio": 3})
    sfx = thin_sfx(sfx, total)

    # 3. audio: narration track, score, effects -> two mixes
    sr = A.SR
    track = np.zeros(int(sr * (total + 1)), dtype="float32")
    for b, tm in zip(S["beats"], timing):
        if tm["narr"]:
            y = ff.read_audio_mono(vo_dir / f"{b['id']}.wav", sr)
            s = int((tm["start"] + tm["lead"]) * sr)
            track[s:s + len(y)] += y[: max(0, len(track) - s)]
    narr_wav = out / "narration.wav"
    A.write_wav(narr_wav, np.stack([track, track], axis=1)[: int(sr * total)])
    stems_v = [] if no_voice else [{"file": str(narr_wav), "role": "voice"}]
    if sfx:
        A.build_sfx_track(sfx, total, out / "sfx.wav")
        stems_v.append({"file": str(out / "sfx.wav"), "role": "sfx", "gain_db": -6})
    stems_m = list(stems_v)
    if meta.get("music", "curious") != "none":
        music.bed(total, out / "score.wav", meta.get("music", "curious"))
        # with a voice the mixer ducks the bed ~16 dB under it; without one the bed is the soundtrack
        stems_m.append({"file": str(out / "score.wav"), "role": "music", "gain_db": 4 if not no_voice else 16})
    mix = out / "mix.wav"
    mix_stems(stems_m, total, str(mix), voice_lufs=-15.0, target_lufs=-14.0)
    mix_nm = out / "mix_nomusic.wav"
    if stems_v:
        mix_stems(stems_v, total, str(mix_nm), voice_lufs=-15.0, target_lufs=-14.0)

    # 4. pictures
    name = short_path.parent.name if short_path.name in ("short.json", ".short.override.json") else short_path.stem
    target = out / f"{name}_9x16{'' if quality == 'final' else '_draft'}.mp4"
    log(f"  rendering {len(scenes)} scenes, {total:.1f}s, {W}x{H} -> {target.name}")
    render_video(ctx, scenes, timing, times, total, mix, target, S, quality)
    result = {"video": str(target), "duration": total, "size": [W, H], "timing": timing, "lint": rep, "sfx": sfx}
    if stems_v:
        nm = target.with_name(target.stem + "_nomusic.mp4")
        ff.run(["-i", str(target), "-i", str(mix_nm), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(nm)])
        result["video_nomusic"] = str(nm)
    # frame 0 is what the feed shows before the video starts: keep it as the thumbnail
    thumb = target.with_name(target.stem + "_frame0.png")
    ff.extract_frame(target, 0.0, thumb)
    result["frame0"] = str(thumb)
    result["loudness"] = A.measure(target)
    result["checks"] = checks(result, S, timing)
    result["render_seconds"] = round(time.time() - t_start, 1)
    (out / "timing.json").write_text(json.dumps({"total": total, "beats": timing, "words": times}, ensure_ascii=False, indent=1))
    (out / "build.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    return result


def thin_sfx(events: list[dict], total: float) -> list[dict]:
    """Keep the most meaningful effects within the per-minute budget; never two within 0.25 s."""
    budget = max(4, int(SFX_PER_MIN * total / 60))
    keep = []
    for e in sorted(events, key=lambda e: (-e["prio"], e["at"])):
        if len(keep) >= budget:
            break
        if all(abs(e["at"] - k["at"]) > 0.25 for k in keep) and 0 <= e["at"] < total:
            keep.append(e)
    return [{k: v for k, v in e.items() if k != "prio"} for e in sorted(keep, key=lambda e: e["at"])]


def render_video(ctx: R.Ctx, scenes: list[R.Scene], timing: list[dict], times: dict, total: float, mix: Path,
                 target: Path, S: dict, quality: str) -> None:
    W, H, fps = ctx.W, ctx.H, ctx.fps
    meta = S["meta"]
    words = []
    hidden = []
    cap_on = meta.get("captions", True)
    for sc, tm in zip(scenes, timing):
        default = sc.v["type"] not in ("hook", "question")
        if not cap_on or not sc.beat.get("captions", default):
            hidden.append((sc.start, sc.start + sc.dur))
            continue
        for w in times[sc.beat["id"]]:
            words.append({"word": w["word"], "start": sc.start + sc.lead + w["start"], "end": sc.start + sc.lead + w["end"]})
    caps = R.Captions(ctx, words, 4 if ctx.lang == "vi" else 3)
    bg = R.Background(ctx)
    series = None
    if meta.get("series"):
        label = meta["series"] + (f" · {'Phần' if ctx.lang == 'vi' else 'Part'} {meta['part']}" if meta.get("part") else "")
        series = R.pill(ctx, label.upper(), 26, fill=ctx.th["ink"], color=ctx.th["bg"])
    # grain is noise: without a ceiling it eats ~25 Mbps. TikTok re-encodes uploads; ~12-14 Mbps is plenty.
    preset, crf, rate = ("medium", "19", "14M") if quality == "final" else ("veryfast", "24", "4M")
    cmd = [ff.FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-i", str(mix), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", preset,
           "-crf", crf, "-maxrate", rate, "-bufsize", str(int(rate[:-1]) * 2) + "M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-shortest", "-movflags", "+faststart", str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    n = int(round(total * fps))
    k = 0
    try:
        for i in range(n):
            t = i / fps
            while k + 1 < len(scenes) and t >= scenes[k + 1].start:
                scenes[k].close()
                k += 1
            sc = scenes[k]
            lt = t - sc.start
            li = i - int(round(sc.start * fps))
            frame = bg.frame(t)
            layer = R.Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sc.draw(layer, lt, li)
            if k > 0 and lt < 0.16:  # punch-in cut: the new scene lands instead of appearing
                z = 1.0 + 0.07 * (1 - R.E.out_cubic(lt / 0.16))
                big = layer.resize((int(W * z), int(H * z)), R.Image.BILINEAR)
                layer = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W, (big.height - H) // 2 + H))
            frame.alpha_composite(layer)
            if series is not None and 0 < k < len(scenes) - 1 and not sc.is_media():
                R.put(frame, series, ctx.W * R.SAFE_L + series.width / 2, ctx.H * 0.075, 1.0, 0.9)
            caps.draw(frame, t, hidden)
            if meta.get("progress_bar", True):
                R.progress_bar(frame, t, total, ctx)
            if sc.v["type"] == "hook" and "punch" in sc.prep and "l2" in sc.prep:  # white flash on the punch frame
                dt = lt - sc.prep["punch"]
                if 0 <= dt < 0.1:
                    fl = R.Image.new("RGBA", (W, H), (255, 255, 255, int(110 * (1 - dt / 0.1))))
                    frame.alpha_composite(fl)
            proc.stdin.write(frame.convert("RGB").tobytes())
    finally:
        for sc in scenes:
            sc.close()
        if proc.stdin:
            proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        proc.wait()
    if proc.returncode != 0:
        raise ff.FFmpegError(f"encode failed: {err[-2000:]}")


def checks(result: dict, S: dict, timing: list[dict]) -> list[str]:
    """Delivery checks against TikTok specs and our own rules. Empty list = pass."""
    out = []
    info = ff.probe(result["video"])
    if (info.width, info.height) not in ((1080, 1920), (540, 960)):
        out.append(f"size {info.width}x{info.height} is not 9:16 1080x1920")
    if abs(info.duration - result["duration"]) > 0.3:
        out.append(f"duration {info.duration:.2f}s differs from plan {result['duration']:.2f}s")
    lo, hi = S["meta"].get("target_seconds", [20, 60])
    if result["duration"] > hi * 1.12:
        out.append(f"{result['duration']:.1f}s is over the {hi}s target: tighten")
    loud = result.get("loudness") or {}
    i = loud.get("integrated_lufs")
    try:
        if i is not None and not -16.5 <= float(i) <= -12.0:
            out.append(f"loudness {float(i):.1f} LUFS outside -16..-12 (TikTok plays around -14)")
    except (TypeError, ValueError):
        pass
    if timing[0]["lead"] > 0.25:
        out.append("hook voice starts after 0.25 s: the first word must be on frame 0-7")
    return out
