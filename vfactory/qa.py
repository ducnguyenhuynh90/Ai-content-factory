"""Self-evaluation before anyone else sees the film.

Measures what can be measured (black/frozen frames, loudness, duration) and
builds contact sheets so a director — human or model — can look at every cut,
the first and last seconds, and the title frames without watching frame dumps.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

from . import audio, ffmpeg as ff, fonts


def check(video: str | Path, report: dict | None = None, out_dir: str | Path | None = None) -> dict:
    video = Path(video)
    out_dir = Path(out_dir or video.parent / f"qa_{video.stem}")
    out_dir.mkdir(parents=True, exist_ok=True)
    info = ff.probe(video)
    res: dict = {"file": str(video), "duration": round(info.duration, 3), "size": [info.width, info.height],
                 "fps": round(info.fps, 3), "issues": [], "notes": []}
    log = ff.run_log(["-i", str(video), "-vf", "blackdetect=d=0.7:pix_th=0.06,freezedetect=n=0.002:d=2.5", "-an", "-f", "null", "-"])
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
    intended = []
    if report:
        for p in report.get("timeline", []):
            if p.get("transition") == "dip":
                intended.append((p["out_start"] - 0.2, p["out_start"] + p.get("tdur", 0) + 0.2))
        intended.append((report["duration"] - 1.0, report["duration"] + 1))
    for a, b in blacks:
        if not any(x <= a and b <= y for x, y in intended):
            res["issues"].append(f"unexpected black {a:.2f}-{b:.2f}s")
    freezes = re.findall(r"freeze_start: ([\d.]+)", log)
    for f in freezes:
        res["notes"].append(f"static picture from {float(f):.2f}s (fine for cards; check if footage)")
    loud = audio.measure(video)
    res.update(loud)
    if loud["integrated_lufs"] is not None and not (-16.5 <= loud["integrated_lufs"] <= -12.5):
        res["issues"].append(f"loudness {loud['integrated_lufs']} LUFS (target -14)")
    if loud["true_peak_dbfs"] is not None and loud["true_peak_dbfs"] > -0.5:
        res["issues"].append(f"true peak {loud['true_peak_dbfs']} dBFS (ceiling -1)")
    if report and abs(report["duration"] - info.duration) > 0.25:
        res["issues"].append(f"duration {info.duration:.2f}s differs from plan {report['duration']:.2f}s")
    times = sample_times(info.duration, report)
    res["contact_sheet"] = str(contact_sheet(video, times, out_dir / "contact.png"))
    res["passed"] = not res["issues"]
    (out_dir / "qa.json").write_text(json.dumps(res, indent=2))
    return res


def sample_times(duration: float, report: dict | None) -> list[tuple[float, str]]:
    ts = [(0.3, "open"), (min(1.5, duration / 4), "open+")]
    if report:
        for p in report["timeline"][1:]:
            c = p["out_start"] + p.get("tdur", 0) / 2
            ts += [(max(0, c - 0.25), f"pre {p['transition']}"), (c + 0.35, f"post {p['transition']}")]
        for o in report.get("overlays", []):
            if o["name"] == "title" or o["name"].startswith(("lt", "cutaway", "chapter")):
                ts.append((o["at"] + min(o["dur"] * 0.5, 2.2), o["name"]))
    else:
        ts += [(duration * k / 10, "") for k in range(1, 10)]
    ts += [(duration - 1.6, "end"), (duration - 0.6, "end+")]
    ts = sorted({round(t, 2): lab for t, lab in ts if 0 <= t < duration}.items())
    return ts[:48]


def contact_sheet(video: Path, times: list[tuple[float, str]], out: Path, cols: int = 6, tile_w: int = 320) -> Path:
    tiles = []
    tmp = out.parent / "_f.jpg"
    font = fonts.get("jetbrains-mono", 13)
    for t, label in times:
        try:
            ff.extract_frame(video, t, tmp, width=tile_w)
            im = Image.open(tmp).convert("RGB")
        except ff.FFmpegError:
            continue
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width, 18], fill=(0, 0, 0))
        d.text((4, 2), f"{t:6.2f}s {label}", font=font, fill=(255, 255, 255))
        tiles.append(im)
    tmp.unlink(missing_ok=True)
    if not tiles:
        return out
    th = tiles[0].height
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w + (cols + 1) * 4, rows * th + (rows + 1) * 4), (24, 24, 24))
    for i, im in enumerate(tiles):
        sheet.paste(im, (4 + (i % cols) * (tile_w + 4), 4 + (i // cols) * (th + 4)))
    sheet.save(out)
    return out
