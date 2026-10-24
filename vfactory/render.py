"""Recipe -> finished film.

Order of operations (each one exists because the alternative fails silently):
  1. per-piece extract: trim, conform (cover-crop, fps), speed, push-in, grade,
     halation, vignette, 30 ms audio fades          -> work/pieces/*.mkv
  2. join: hard cuts via concat, designed transitions via xfade/acrossfade
                                                    -> work/joined.mkv
  3. overlays (titles, lower thirds, leaks), PTS-shifted to their window
  4. finishing: grain, letterbox, head/tail fades, captions LAST
  5. sound: dialogue + ducked music + designed SFX, two-pass loudnorm
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

from . import audio, captions, ffmpeg as ff, fonts, styles
from . import recipe as R
from .motion.cards import Chapter, EndCard, LightLeak, LowerThird
from .motion.titles import make_title

XFADE = {"dissolve": "fade", "dip": "fadeblack", "flash": "fadewhite", "whip": "smoothleft",
         "zoom": "zoomin", "slide": "smoothleft", "wipe": "wipeleft"}
WHOOSH_TRANSITIONS = {"whip", "zoom", "slide", "flash", "wipe"}


def log(msg: str) -> None:
    print(f"[vfactory] {msg}", flush=True)


def transition_duration(kind: str, look: styles.Look) -> float:
    return {
        "cut": 0.0,
        "dissolve": look.transition_dur if look.transition_dur >= 0.5 else 0.5,
        "dip": max(0.6, look.transition_dur),
        "flash": 0.3,
        "whip": 0.25,
        "zoom": 0.3,
        "slide": min(0.6, max(0.35, look.transition_dur)),
        "wipe": min(0.6, max(0.35, look.transition_dur)),
    }[kind]


# ---------------------------------------------------------------- planning

def plan(r: dict, look: styles.Look) -> list[dict]:
    """Ordered pieces with nominal durations and incoming transitions (no files yet)."""
    pieces: list[dict] = []

    def footage(seg: dict, role: str, i: int) -> dict:
        speed = float(seg.get("speed", 1.0))
        return {"kind": "footage", "role": role, "index": i, "source": seg["source"],
                "src_start": float(seg["start"]), "src_end": float(seg["end"]), "speed": speed,
                "dur": (float(seg["end"]) - float(seg["start"])) / speed,
                "transition": seg.get("transition", "cut"), "push": seg.get("push"), "beat": seg.get("beat", "")}

    for i, seg in enumerate(r["cold_open"]):
        p = footage(seg, "cold_open", i)
        p["transition"] = "cut" if i == 0 else p["transition"]
        pieces.append(p)

    title = r.get("title") or None
    mode = (title or {}).get("mode", "auto")
    if title and mode == "auto":
        mode = "card" if r["cold_open"] else "over"
    if title:
        title["mode"] = mode
    if title and mode == "card":
        pieces.append({"kind": "title_card", "role": "title", "dur": float(title.get("duration", look.title_hold)),
                       "transition": "cut"})  # smash cut from the cold open into the title

    for i, seg in enumerate(r["segments"]):
        p = footage(seg, "body", i)
        if i == 0:
            if pieces and pieces[-1]["kind"] == "title_card":
                p["transition"] = p["transition"] if p["transition"] != "cut" else "dip"
            elif pieces:  # out of the cold open, no title card
                p["transition"] = p["transition"] if p["transition"] != "cut" else look.section_transition
            else:
                p["transition"] = "cut"
        pieces.append(p)

    ending = r.get("ending")
    if ending:
        hold = float(ending.get("hold", look.endcard_hold))
        pieces.append({"kind": "end_card", "role": "ending", "dur": hold, "transition": "dip",
                       "transition_dur": look.tail_fade})
    # transition durations, clamped so no transition eats more than 45% of either neighbour
    for i, p in enumerate(pieces):
        if i == 0 or p["transition"] == "cut":
            p["tdur"] = 0.0
            continue
        d = p.get("transition_dur") or transition_duration(p["transition"], look)
        d = min(d, 0.45 * p["dur"], 0.45 * pieces[i - 1]["dur"])
        p["tdur"] = round(d, 3) if d >= 0.08 else 0.0
        if p["tdur"] == 0.0:
            p["transition"] = "cut"
    return pieces


def assign_times(pieces: list[dict]) -> float:
    t = 0.0
    for i, p in enumerate(pieces):
        if i:
            t -= p["tdur"]
        p["out_start"] = round(t, 4)
        t += p["dur"]
        p["out_end"] = round(t, 4)
    return t


# ---------------------------------------------------------------- piece rendering

def _hash(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


def picture_chain(look: styles.Look, W: int, H: int, fps: int, dur: float, push: float, speed: float) -> str:
    f = [f"setpts=(PTS-STARTPTS)/{speed:.5f}" if abs(speed - 1) > 1e-3 else "setpts=PTS-STARTPTS",
         f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}", "setsar=1"]
    if abs(push) > 1e-4:
        z = abs(push)
        prog = f"(t/{max(dur, 0.1):.3f})" if push > 0 else f"(1-t/{max(dur, 0.1):.3f})"
        f.append(f"scale=w='2*trunc({W}*(1+{z:.4f}*{prog})/2)':h='2*trunc({H}*(1+{z:.4f}*{prog})/2)':eval=frame:flags=bicubic")
        f.append(f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2")
    f.append(f"fps={fps}")
    if look.grade:
        f.append(look.grade)
    chain = ",".join(f)
    if look.halation > 0:
        sigma = max(4, int(min(W, H) * 0.02))
        chain += (f",split[hv0][hv1];[hv1]curves=all='0/0 0.62/0 1/1',gblur=sigma={sigma},"
                  f"colorbalance=rh=0.25:gh=0.02:bh=-0.1[hg];[hv0][hg]blend=all_mode=screen:all_opacity={look.halation * 0.6:.3f}")
    if look.vignette > 0:
        chain += f",vignette=angle={0.2 + 0.5 * look.vignette:.3f}"
    return chain + ",setsar=1,format=yuv420p"


def render_footage(p: dict, r: dict, look: styles.Look, info: ff.MediaInfo, out: Path, W: int, H: int, fps: int,
                   quality: dict) -> Path:
    src = r["sources"][p["source"]]
    seg_dur = p["src_end"] - p["src_start"]
    push = p["push"] if p["push"] is not None else (look.push_in if p["index"] % 2 == 0 else -look.push_in)
    chain = picture_chain(look, W, H, fps, p["dur"], float(push), p["speed"])
    gain = float((r.get("source_gain_db") or {}).get(p["source"], 0.0))
    d = p["dur"]
    args = ["-ss", f"{p['src_start']:.3f}", "-t", f"{seg_dur:.3f}", "-i", src]
    if info.has_audio:
        a = ["asetpts=PTS-STARTPTS"]
        sp = p["speed"]
        while sp > 2.0:
            a.append("atempo=2.0"); sp /= 2.0
        while sp < 0.5:
            a.append("atempo=0.5"); sp /= 0.5
        if abs(sp - 1) > 1e-3:
            a.append(f"atempo={sp:.5f}")
        a += [f"aresample={audio.SR}", "aformat=sample_fmts=fltp:channel_layouts=stereo", f"volume={gain}dB",
              "afade=t=in:st=0:d=0.03", f"afade=t=out:st={max(0, d - 0.03):.3f}:d=0.03"]
        amap = ["-filter_complex", f"[0:v]{chain}[v];[0:a]{','.join(a)}[a]", "-map", "[v]", "-map", "[a]"]
    else:
        args += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", f"anullsrc=r={audio.SR}:cl=stereo"]
        amap = ["-filter_complex", f"[0:v]{chain}[v]", "-map", "[v]", "-map", "1:a"]
    ff.run([*args, *amap, "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", quality["inter_preset"], "-crf", str(quality["inter_crf"]),
            "-g", str(fps), "-c:a", "pcm_s16le", str(out)])
    return out


def render_card(anim, out: Path) -> Path:
    tmp = out.with_suffix(".video.mp4")
    anim.render(tmp)
    ff.run(["-i", str(tmp), "-f", "lavfi", "-t", f"{anim.duration:.3f}", "-i", f"anullsrc=r={audio.SR}:cl=stereo",
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s16le", "-shortest", str(out)])
    tmp.unlink(missing_ok=True)
    return out


# ---------------------------------------------------------------- join

def join(pieces: list[dict], out: Path, fps: int, quality: dict) -> float:
    args, graph = [], []
    for i, p in enumerate(pieces):
        args += ["-i", p["file"]]
        graph.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={fps},settb=1/{fps},setsar=1,format=yuv420p[v{i}]")
        graph.append(f"[{i}:a]aresample={audio.SR},asetpts=PTS-STARTPTS[a{i}]")
    cv, ca, cur = "v0", "a0", pieces[0]["dur"]
    for i in range(1, len(pieces)):
        p = pieces[i]
        nv, na = f"vj{i}", f"aj{i}"
        if p["transition"] == "cut" or p["tdur"] <= 0:
            graph.append(f"[{cv}][{ca}][v{i}][a{i}]concat=n=2:v=1:a=1[{nv}c][{na}]")
            graph.append(f"[{nv}c]settb=1/{fps},setsar=1[{nv}]")  # xfade needs matching timebases downstream
            cur += p["dur"]
        else:
            d = p["tdur"]
            graph.append(f"[{cv}][v{i}]xfade=transition={XFADE[p['transition']]}:duration={d:.3f}:offset={cur - d:.3f}[{nv}]")
            graph.append(f"[{ca}][a{i}]acrossfade=d={d:.3f}:c1=qsin:c2=qsin[{na}]")
            cur += p["dur"] - d
        cv, ca = nv, na
    ff.run([*args, "-filter_complex", ";".join(graph), "-map", f"[{cv}]", "-map", f"[{ca}]",
            "-c:v", "libx264", "-preset", quality["inter_preset"], "-crf", str(quality["inter_crf"]), "-g", str(fps),
            "-c:a", "pcm_s16le", str(out)])
    return cur


# ---------------------------------------------------------------- main entry

def render(recipe_in, *, preview: bool = False, work_dir: str | Path | None = None, keep_work: bool = True) -> dict:
    t_start = time.time()
    r = R.load(recipe_in)
    look = styles.get(r["look"]).with_overrides(**(r.get("look_overrides") or {}))
    fmt = r["format"]
    W, H, fps = int(fmt["width"]), int(fmt["height"]), int(fmt["fps"])
    if preview:
        W, H = (W // 2) // 2 * 2, (H // 2) // 2 * 2
    quality = ({"inter_preset": "ultrafast", "inter_crf": 23, "final_preset": "veryfast", "final_crf": 24} if preview else
               {"inter_preset": "veryfast", "inter_crf": 12, "final_preset": "slow", "final_crf": 17})
    output = Path(r["output"])
    if preview:
        output = output.with_name(output.stem + "_preview" + output.suffix)
    work = Path(work_dir) if work_dir else output.parent / f"work_{output.stem}"
    (work / "pieces").mkdir(parents=True, exist_ok=True)
    (work / "overlays").mkdir(parents=True, exist_ok=True)

    infos = {k: ff.probe(v) for k, v in r["sources"].items()}
    for k, info in infos.items():
        if not info.has_video:
            raise R.RecipeError(f"source {k} has no video stream: {info.path}")

    pieces = plan(r, look)
    title = r.get("title")
    ending = r.get("ending")

    # 1. pieces --------------------------------------------------------
    anims = {}
    for i, p in enumerate(pieces):
        if p["kind"] == "footage":
            key = _hash([p, r["sources"][p["source"]], look.to_dict(), W, H, fps, quality, r.get("source_gain_db")])
            out = work / "pieces" / f"{i:03d}_{p['source']}_{key}.mkv"
            if not out.exists():
                log(f"piece {i:02d} {p['role']:9s} {p['source']} {p['src_start']:.2f}-{p['src_end']:.2f}")
                render_footage(p, r, look, infos[p["source"]], out, W, H, fps, quality)
        elif p["kind"] == "title_card":
            anim = make_title(look, W, H, fps, p["dur"], title["text"], title.get("kicker", ""), title.get("subtitle", ""), card=True,
                              anim=title.get("anim"))
            p["dur"] = anim.duration
            anims[i] = anim
            key = _hash(["title", title, look.to_dict(), W, H, fps, p["dur"]])
            out = work / "pieces" / f"{i:03d}_title_{key}.mkv"
            if not out.exists():
                log("title card")
                render_card(anim, out)
        else:
            anim = EndCard(look, W, H, fps, p["dur"], ending.get("title") or (title or {}).get("text", ""),
                           tagline=ending.get("tagline", ""), cta=ending.get("cta", ""), handle=ending.get("handle", ""),
                           credits=ending.get("credits"), logo=ending.get("logo"), layout=ending.get("layout"))
            anims[i] = anim
            key = _hash(["end", ending, title, look.to_dict(), W, H, fps, p["dur"]])
            out = work / "pieces" / f"{i:03d}_end_{key}.mkv"
            if not out.exists():
                log("end card")
                render_card(anim, out)
        p["file"] = str(out)
        p["dur"] = round(ff.probe(out).duration, 4)  # trust the file, not the plan
    total = assign_times(pieces)

    # 2. join ----------------------------------------------------------
    joined = work / "joined.mkv"
    log(f"joining {len(pieces)} pieces -> {total:.2f}s")
    join(pieces, joined, fps, quality)

    # 3. overlays + sfx events -------------------------------------------
    overlays: list[dict] = []
    sfx: list[dict] = []
    blackout: list[tuple[float, float]] = []
    body = [p for p in pieces if p["role"] == "body"]

    def add_overlay(anim, at: float, name: str):
        key = _hash([name, look.to_dict(), W, H, fps, anim.duration, getattr(anim, "title", ""), getattr(anim, "kicker", "")])
        f = work / "overlays" / f"{name}_{key}.mov"
        if not f.exists():
            anim.render(f)
        overlays.append({"file": str(f), "at": round(at, 3), "dur": anim.duration, "name": name})
        return anim

    for k, cw in enumerate(r.get("cutaways") or []):
        seg = body[min(int(cw.get("segment", 0)), len(body) - 1)]
        at = seg["out_start"] + seg["tdur"] + float(cw.get("offset", 0.4))
        cp = {"kind": "footage", "role": "cutaway", "index": k, "source": cw["source"], "src_start": float(cw["start"]),
              "src_end": float(cw["end"]), "speed": float(cw.get("speed", 1.0)), "push": cw.get("push"),
              "dur": (float(cw["end"]) - float(cw["start"])) / float(cw.get("speed", 1.0))}
        key = _hash([cp, r["sources"][cp["source"]], look.to_dict(), W, H, fps, quality])
        f = work / "overlays" / f"cutaway{k}_{key}.mkv"
        if not f.exists():
            log(f"cutaway {k} {cp['source']} {cp['src_start']:.2f}-{cp['src_end']:.2f} @ {at:.2f}s")
            render_footage(cp, r, look, infos[cp["source"]], f, W, H, fps, quality)
        overlays.append({"file": str(f), "at": round(at, 3), "dur": round(cp["dur"], 3), "name": f"cutaway{k}", "fade": 0.18})

    for i, p in enumerate(pieces):
        if p["kind"] == "title_card":
            blackout.append((p["out_start"], p["out_end"]))
            for h in anims[i].hits[:4]:
                if "hit" in look.sfx:
                    sfx.append({"kind": "hit", "at": p["out_start"] + h, "gain_db": -3 if h == anims[i].hits[0] else -8})
            if "riser" in look.sfx and p["out_start"] + anims[i].hits[0] > 2.3:
                sfx.append({"kind": "riser", "at": p["out_start"] + anims[i].hits[0], "gain_db": -8})
        if p["kind"] == "end_card":
            blackout.append((p["out_start"], p["out_end"]))
            if "hit" in look.sfx and anims[i].hits:
                sfx.append({"kind": "hit", "at": p["out_start"] + anims[i].hits[0], "gain_db": -10})
        if i and p["transition"] in WHOOSH_TRANSITIONS and "whoosh" in look.sfx:
            sfx.append({"kind": "whoosh", "at": p["out_start"] + p["tdur"] / 2, "gain_db": -6})
        if i and look.light_leaks and p["transition"] in {"dissolve", "flash", "dip", "whip"} and p["kind"] == "footage":
            n_leaks = sum(1 for o in overlays if o["name"].startswith("leak"))
            if n_leaks < 4:
                leak = LightLeak(W, H, fps, duration=max(1.0, p["tdur"] * 2.2), seed=i)
                add_overlay(leak, max(0.0, p["out_start"] - leak.duration * 0.35), f"leak{i}")

    if title and title.get("mode") == "over" and body:
        at = body[0]["out_start"] + (0.4 if body[0]["transition"] == "cut" else body[0]["tdur"])
        anim = make_title(look, W, H, fps, float(title.get("duration", look.title_hold)), title["text"],
                          title.get("kicker", ""), title.get("subtitle", ""), card=False, anim=title.get("anim"))
        add_overlay(anim, at, "title")
        blackout.append((at, at + anim.duration))
        for h in anim.hits[:4]:
            if "hit" in look.sfx:
                sfx.append({"kind": "hit", "at": at + h, "gain_db": -4 if h == anim.hits[0] else -9})
        if "riser" in look.sfx and at + anim.hits[0] > 2.3:
            sfx.append({"kind": "riser", "at": at + anim.hits[0], "gain_db": -9})
        if look.light_leaks:
            add_overlay(LightLeak(W, H, fps, duration=1.6, seed=99), at, "leak_title")

    for k, lt in enumerate(r["lower_thirds"]):
        if "at" in lt:
            at = float(lt["at"])
        else:
            seg = body[min(int(lt.get("segment", 0)), len(body) - 1)]
            at = seg["out_start"] + seg["tdur"] + float(lt.get("offset", 0.6))
        anim = LowerThird(look, W, H, fps, float(lt.get("duration", 4.0)), lt["name"], lt.get("role", ""), anim=lt.get("anim"))
        add_overlay(anim, at, f"lt{k}")
        if "tick" in look.sfx:
            sfx.append({"kind": "tick", "at": at + 0.05, "gain_db": -10})

    for k, ch in enumerate(r["chapters"]):
        seg = body[min(int(ch.get("segment", 0)), len(body) - 1)]
        at = seg["out_start"] + seg["tdur"] + 0.2
        anim = Chapter(look, W, H, fps, float(ch.get("duration", 2.8)), ch["text"], ch.get("number", ""))
        add_overlay(anim, at, f"chapter{k}")
        blackout.append((at, at + anim.duration))

    if not r.get("sfx", True):
        sfx = []
    sfx = _thin_sfx(sorted(sfx, key=lambda e: e["at"]), total)

    # 4. captions -------------------------------------------------------
    ass_file = None
    cap = r.get("captions") or {}
    words = []
    if cap.get("words"):
        words = captions.load_words(cap["words"])
    elif cap.get("transcribe"):
        for key, src in r["sources"].items():
            words += [{**w, "source": key} for w in captions.transcribe(src, work / "transcripts", cap.get("model", "small"))]
    if words:
        mapped = captions.map_words(words, pieces)
        ass_file = captions.build_ass(mapped, look, W, H, work / "captions.ass", blackout=blackout)

    # 5. sound ---------------------------------------------------------
    log("mixing sound")
    music = dict(r.get("music") or {})
    if music.get("file") and music.get("sync_downbeats") and body and "start" not in music:
        # Land a downbeat exactly where the body begins, so beat-length shots cut on the beat.
        b0 = body[0]["out_start"] + body[0]["tdur"]
        later = [d for d in music["sync_downbeats"] if d >= b0]
        music["start"] = round(later[0] - b0, 3) if later else 0.0
    sfx_wav = audio.build_sfx_track(sfx, total, work / "sfx.wav") if sfx else None
    any_dialogue = any(infos[p["source"]].has_audio for p in pieces if p["kind"] == "footage")
    mixed = audio.mix(str(joined), total, work / "mix.wav", music=music, sfx_wav=sfx_wav,
                      music_db=look.music_db, duck_db=look.duck_db, has_dialogue=any_dialogue,
                      music_fade_out=min(3.0, max(1.5, look.endcard_hold * 0.5)))

    # 6. finishing -------------------------------------------------------
    log(f"finishing -> {output.name}")
    args = ["-i", str(joined)]
    graph = []
    head_fade = 0.0 if look.transition_dur < 0.4 else 0.5
    base = "[0:v]" + (f"fade=t=in:st=0:d={head_fade}," if head_fade else "") + "format=yuv420p[b0]"
    graph.append(base)
    cur = "b0"
    for k, ov in enumerate(overlays, start=1):
        args += ["-i", ov["file"]]
        fade = ov.get("fade")
        pre = (f"format=yuva420p,fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={max(0, ov['dur'] - fade):.3f}:d={fade}:alpha=1,"
               if fade else "")
        graph.append(f"[{k}:v]{pre}setpts=PTS-STARTPTS+{ov['at']:.3f}/TB[o{k}]")
        graph.append(f"[{cur}][o{k}]overlay=eof_action=pass:format=auto[b{k}]")
        cur = f"b{k}"
    fin = []
    if look.grain > 0:
        g = look.grain if not preview else max(1, look.grain // 2)
        fin.append(f"noise=c0s={g}:c0f=t+u")
    if look.letterbox and W / H < look.letterbox - 0.01:
        bar = int(round((H - W / look.letterbox) / 2))
        fin.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")
    fin.append(f"fade=t=out:st={max(0, total - 0.4):.3f}:d=0.4")
    if ass_file:
        fin.append(f"ass='{_esc_path(ass_file)}':fontsdir='{_esc_path(fonts.FONT_DIR)}'")  # captions LAST
    fin.append("format=yuv420p")
    graph.append(f"[{cur}]{','.join(fin)}[vout]")
    a_idx = len(overlays) + 1
    args += ["-i", str(mixed)]
    output.parent.mkdir(parents=True, exist_ok=True)
    ff.run([*args, "-filter_complex", ";".join(graph), "-map", "[vout]", "-map", f"{a_idx}:a",
            "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", quality["final_preset"], "-crf", str(quality["final_crf"]),
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", *AAC_CONFIGS[0], "-b:a", "192k",
            "-movflags", "+faststart", str(output)])

    _fix_true_peak(output, Path(mixed))

    report = {
        "output": str(output), "duration": round(total, 3), "size": [W, H], "fps": fps, "look": look.name,
        "render_seconds": round(time.time() - t_start, 1),
        "timeline": [{k: p.get(k) for k in ("kind", "role", "source", "src_start", "src_end", "out_start", "out_end",
                                            "transition", "tdur", "beat")} for p in pieces],
        "overlays": [{k: o[k] for k in ("name", "at", "dur")} for o in overlays],
        "sfx": sfx, "captions": bool(ass_file),
    }
    (work / "report.json").write_text(json.dumps(report, indent=2))
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    log(f"done in {report['render_seconds']}s -> {output}")
    return report


AAC_CONFIGS = (["-aac_coder", "twoloop", "-cutoff", "18000"], ["-aac_coder", "fast"],
               ["-aac_coder", "twoloop", "-cutoff", "16000"])


def _fix_true_peak(video: Path, mix: Path, ceiling: float = -1.0) -> None:
    """ffmpeg's native AAC encoder can overshoot a limited master by 1-3 dB, unpredictably per
    configuration. Verify the delivered file; if it is over, re-encode the master mix with the other
    configurations and keep the first that measures under the ceiling; reduce gain only as a last resort."""
    tp = audio.measure(video).get("true_peak_dbfs")
    if tp is None or tp <= ceiling:
        return
    tmp = video.with_name(video.stem + "_tp" + video.suffix)
    tries = [(cfg, 0.0) for cfg in AAC_CONFIGS[1:]] + [(AAC_CONFIGS[0], ceiling - tp - 0.5)] * 2
    for cfg, gain in tries:
        ff.run(["-i", str(video), "-i", str(mix), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-af", f"volume={gain:.2f}dB", "-c:a", "aac", *cfg, "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", str(tmp)])
        new_tp = audio.measure(tmp).get("true_peak_dbfs")
        if new_tp is not None and new_tp <= ceiling:
            tmp.replace(video)
            log(f"true peak {tp:+.1f} dBTP after AAC; re-encoded ({' '.join(cfg)}, gain {gain:+.1f} dB) -> {new_tp:+.1f}")
            return
        if gain:
            tp = new_tp if new_tp is not None else tp
    tmp.unlink(missing_ok=True)
    log(f"warning: true peak still above {ceiling} dBTP after all encoder configurations")


def _thin_sfx(events: list[dict], total: float) -> list[dict]:
    """Fewer, better effects: at most ~8 per minute and never two within 0.4 s."""
    cap = max(4, int(8 * total / 60) + 2)
    out = []
    for e in events:
        if out and e["at"] - out[-1]["at"] < 0.4 and e["kind"] == out[-1]["kind"]:
            continue
        out.append(e)
    if len(out) > cap:
        priority = {"hit": 0, "riser": 1, "whoosh": 2, "tick": 3}
        keep = sorted(out, key=lambda e: (priority.get(e["kind"], 9), e["at"]))[:cap]
        out = sorted(keep, key=lambda e: e["at"])
    return out


def _esc_path(p) -> str:
    return str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def plan_preview(recipe_in) -> list[dict]:
    """Plan without rendering (for --dry-run): nominal timeline."""
    r = R.load(recipe_in)
    look = styles.get(r["look"])
    pieces = plan(r, look)
    assign_times(pieces)
    return pieces


__all__ = ["render", "plan", "plan_preview"]
