"""Render the cut: one decode of the protected source copy, one encode of the result.

- picture and voice are trimmed at the same frame-snapped instants (no drift across many cuts);
- 15 ms audio fades at every boundary (no clicks);
- per-segment static crop centred on the speaker (reframe without wobble or distortion);
- jump cuts between consecutive segments are hidden with an alternating ~8% punch-in when
  the source has the resolution for it (GhostEditor: shot-size change, not a zoom on every cut);
- correction filter and voice chain are applied once, after the concat.
"""

from __future__ import annotations

from pathlib import Path

from .. import audio as A
from .. import ffmpeg as ff
from .frame import FaceTrack, Reframe

QUALITY = {"draft": ("veryfast", 23), "final": ("slow", 16)}


def render_cut(src: str, segments: list[dict], out: str | Path, *, src_w: int, src_h: int, fps: float,
               reframe: Reframe, faces: FaceTrack | None, picture_filter: str = "", voice_chain: str = "",
               has_audio: bool = True, punch: str = "auto", quality: str = "draft", target_lufs: float = -14.0) -> dict:
    out = Path(out)
    work = out.with_suffix(".parts")
    work.mkdir(parents=True, exist_ok=True)
    n = len(segments)
    preset, crf = QUALITY[quality]
    headroom = min(src_w / reframe.crop_w, src_h / reframe.crop_h) if reframe.crop_w else 1.0
    can_punch = punch != "none" and (reframe.crop_h / max(reframe.out_h, 1)) >= 1.15
    graph = [f"[0:v]split={n}" + "".join(f"[vs{i}]" for i in range(n))]
    if has_audio:
        graph.append(f"[0:a]asplit={n}" + "".join(f"[as{i}]" for i in range(n)))
    decisions = []
    for i, s in enumerate(segments):
        a, b = float(s["start"]), float(s["end"])
        fc = faces.median_center(a, b) if faces else None
        cx, cy = (fc[0], fc[1]) if fc else (0.5, 0.42)
        zoom = 1.0
        if can_punch and i % 2 == 1 and _same_framing(segments, i):
            zoom = 1.08
        cw = int(round(reframe.crop_w / zoom / 2)) * 2
        ch = int(round(reframe.crop_h / zoom / 2)) * 2
        x = max(0, min(src_w - cw, int(round(cx * src_w - cw / 2)))) // 2 * 2
        # keep the eyes around 36% from the top of the frame
        y = max(0, min(src_h - ch, int(round(cy * src_h - ch * 0.36)))) // 2 * 2
        graph.append(f"[vs{i}]trim=start={a:.6f}:end={b:.6f},setpts=PTS-STARTPTS,crop={cw}:{ch}:{x}:{y},"
                     f"scale={reframe.out_w}:{reframe.out_h}:flags=lanczos,setsar=1,fps={fps}[v{i}]")
        if has_audio:
            d = b - a
            graph.append(f"[as{i}]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,"
                         f"afade=t=in:st=0:d=0.015,afade=t=out:st={max(0, d - 0.015):.4f}:d=0.015[a{i}]")
        decisions.append({"segment": i, "src": [round(a, 3), round(b, 3)], "crop": [cw, ch, x, y], "punch_in": zoom > 1})
    pairs = "".join(f"[v{i}][a{i}]" if has_audio else f"[v{i}]" for i in range(n))
    graph.append(f"{pairs}concat=n={n}:v=1:a={1 if has_audio else 0}" + ("[vc][ac]" if has_audio else "[vc]"))
    graph.append(f"[vc]{picture_filter + ',' if picture_filter else ''}format=yuv420p[vo]")
    maps = ["-map", "[vo]"]
    if has_audio:
        graph.append(f"[ac]{voice_chain or 'anull'},aresample={A.SR}[ao]")
        maps += ["-map", "[ao]"]
    inter = work / "cut.mkv"
    ff.run(["-i", src, "-filter_complex", ";".join(graph), *maps, "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-r", str(fps), *(["-c:a", "pcm_s16le"] if has_audio else []), str(inter)])
    if has_audio:
        wav = work / "voice.wav"
        ff.run(["-i", str(inter), "-vn", "-c:a", "pcm_s16le", str(work / "voice_raw.wav")])
        A.loudnorm(work / "voice_raw.wav", wav, target_lufs, -1.5)
        ff.run(["-i", str(inter), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                "-aac_coder", "twoloop", "-cutoff", "18000", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)])
    else:
        ff.run(["-i", str(inter), "-c:v", "copy", "-movflags", "+faststart", str(out)])
    return {"file": str(out), "duration": ff.probe(out).duration, "segments": decisions,
            "punch_ins": sum(1 for d in decisions if d["punch_in"]), "headroom": round(headroom, 2)}


def _same_framing(segments: list[dict], i: int) -> bool:
    """A cut between two pieces of one continuous camera take is a jump cut."""
    return i > 0 and segments[i]["start"] > segments[i - 1]["end"] - 1e-3
