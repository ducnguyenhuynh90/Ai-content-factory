"""Edit decision log: what was cut, kept, corrected and why, for every substantial edit."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .transcribe import fmt


def write(proj: Path, name: str, data: dict) -> tuple[Path, Path]:
    final = proj / "final"
    final.mkdir(exist_ok=True)
    jp, mp = final / f"{name}.edit.json", final / f"{name}.edit.md"
    jp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    mp.write_text(markdown(data))
    return jp, mp


def markdown(d: dict) -> str:
    L = [f"# Edit report: {d.get('output_name', '')}", f"_{datetime.now().isoformat(timespec='seconds')}_", "",
         f"- **Source:** {d.get('original_filename')} (copy: `{d.get('source_copy')}`)",
         f"- **Platform:** {d.get('platform')} · **CTA:** {d.get('cta') or '—'} · **Style:** {d.get('style')}",
         f"- **Output:** {d.get('resolution')} ({d.get('aspect')}), {d.get('duration', 0):.2f} s, from "
         f"{d.get('source_duration', 0):.2f} s of recording",
         f"- **Final file:** `{d.get('final_path')}`", ""]
    L.append("## Takes")
    for dec in d.get("decisions", []):
        mark = " ⚠ low confidence" if dec.get("flagged") else ""
        L.append(f"- idea {dec['idea']}: kept [{fmt(dec['chosen']['start'])}–{fmt(dec['chosen']['end'])}] "
                 f"“{dec['chosen']['text']}” ({dec['reason']}){mark}")
        for a in dec.get("alternatives", []):
            L.append(f"  - rejected [{fmt(a['start'])}–{fmt(a['end'])}] “{a['text']}”")
    if d.get("restart_markers"):
        L.append("- restart phrases removed: " + "; ".join(f"[{fmt(m['start'])}] “{m['text']}”" for m in d["restart_markers"]))
    L += ["", "## Dead time"]
    pauses = d.get("pauses_tightened", [])
    L.append(f"- {len(pauses)} long pauses tightened ({sum(p['gap'] - p['kept'] for p in pauses):.1f} s removed); "
             f"pauses under the threshold kept as natural rhythm")
    L += ["", "## Picture", f"- verdict: {d.get('picture', {}).get('verdict')}"]
    L += [f"- {c}" for c in d.get("picture", {}).get("corrections", [])] or ["- no correction needed"]
    L += [f"- reframe: {d.get('reframe')}", f"- jump-cut punch-ins: {d.get('punch_ins', 0)}", "", "## Sound"]
    L += [f"- {n}" for n in d.get("audio", {}).get("notes", [])]
    L.append(f"- delivered loudness {d.get('loudness_lufs')} LUFS, true peak {d.get('true_peak_dbtp')} dBTP")
    L += ["", "## Captions and graphics", f"- {d.get('graphics') or 'none'}", "", "## Warnings"]
    L += [f"- {w}" for w in d.get("warnings", [])] or ["- none"]
    L += ["", "Watch the final video once from beginning to end before posting."]
    return "\n".join(L) + "\n"
