"""Local word-level transcription (Whisper), cached per source.

Backends, in order: faster-whisper (Python), then the `whisper` CLI (openai-whisper).
Nothing is uploaded. Lessons applied (HyperFrames captions guide, GhostEditor):
- transcribe the WHOLE recording, every take: the transcript is the edit map;
- word timestamps only; cut on word times, never segment times;
- never translate: multilingual models transcribe in the spoken language (`.en` models translate);
- Whisper invents words over silence ("Thank you."): drop words that sit inside detected silence.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .. import analyze


class TranscriptionUnavailable(RuntimeError):
    pass


def _faster_whisper(audio: str, model: str, language: str | None) -> dict:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise TranscriptionUnavailable("faster-whisper not installed (pip install faster-whisper)") from e
    try:
        m = WhisperModel(model, device="auto", compute_type="int8")
    except Exception as e:  # model download blocked / missing
        raise TranscriptionUnavailable(f"Whisper model '{model}' could not be loaded: {type(e).__name__}: {str(e)[:200]}. "
                                       "The first run downloads the model from huggingface.co; on an offline machine set "
                                       "VIDEO_EDITOR_WHISPER_MODEL to a local model directory.") from e
    segments, info = m.transcribe(audio, language=language, task="transcribe", word_timestamps=True,
                                  vad_filter=False, condition_on_previous_text=False)
    segs = []
    for s in segments:
        segs.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                     "words": [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3),
                                "prob": round(w.probability, 3)} for w in (s.words or [])]})
    return {"backend": "faster-whisper", "model": model, "language": info.language, "segments": segs}


def _whisper_cli(audio: str, model: str, language: str | None) -> dict:
    exe = shutil.which("whisper")
    if not exe:
        raise TranscriptionUnavailable("openai-whisper CLI not found")
    with tempfile.TemporaryDirectory() as td:
        cmd = [exe, audio, "--model", model, "--word_timestamps", "True", "--output_format", "json",
               "--output_dir", td, "--fp16", "False", "--task", "transcribe"]
        if language:
            cmd += ["--language", language]
        p = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if p.returncode != 0:
            raise TranscriptionUnavailable(p.stderr[-400:])
        data = json.loads(next(Path(td).glob("*.json")).read_text())
    segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip(),
             "words": [{"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3),
                        "prob": round(w.get("probability", 1.0), 3)} for w in s.get("words", [])]}
            for s in data.get("segments", [])]
    return {"backend": "whisper-cli", "model": model, "language": data.get("language"), "segments": segs}


def drop_silence_hallucinations(words: list[dict], silences: list[tuple[float, float]]) -> tuple[list[dict], list[dict]]:
    kept, dropped = [], []
    for w in words:
        dur = max(1e-3, w["end"] - w["start"])
        inside = sum(max(0.0, min(w["end"], b) - max(w["start"], a)) for a, b in silences)
        (dropped if inside / dur > 0.8 else kept).append(w)
    return kept, dropped


def transcribe(media: str | Path, out_dir: str | Path, model: str | None = None, language: str | None = None,
               words_override: str | Path | None = None) -> dict:
    """Write words.json, transcript.txt and transcript_timestamped.txt into out_dir; return the data."""
    import os

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "whisper_raw.json"
    model = model or os.environ.get("VIDEO_EDITOR_WHISPER_MODEL", "small")
    provided = out / "provided_words.json"
    if words_override:
        provided.write_text(Path(words_override).read_text())
    if provided.exists():
        raw_words = json.loads(provided.read_text())
        if isinstance(raw_words, dict):
            raw_words = next(iter(raw_words.values()))
        data = {"backend": "provided", "model": None, "language": language,
                "segments": [{"start": raw_words[0]["start"], "end": raw_words[-1]["end"],
                              "text": " ".join(w["word"] for w in raw_words), "words": raw_words}]}
    elif cache.exists():
        data = json.loads(cache.read_text())
    else:
        with tempfile.TemporaryDirectory() as td:
            wav = str(Path(td) / "audio.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", wav],
                           check=True, stdin=subprocess.DEVNULL)
            errors = []
            data = None
            for fn in (_faster_whisper, _whisper_cli):
                try:
                    data = fn(wav, model, language)
                    break
                except TranscriptionUnavailable as e:
                    errors.append(str(e))
            if data is None:
                raise TranscriptionUnavailable(" | ".join(errors))
        cache.write_text(json.dumps(data))
    words = [w for s in data["segments"] for w in s["words"] if w["word"]]
    silences = analyze.detect_silences(str(media), noise_db=-35, min_dur=0.6)
    words, dropped = drop_silence_hallucinations(words, silences)
    result = {"backend": data["backend"], "model": data.get("model"), "language": data.get("language"),
              "words": words, "dropped_in_silence": dropped}
    (out / "words.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    (out / "transcript.txt").write_text(_plain(words) + "\n")
    (out / "transcript_timestamped.txt").write_text(_timestamped(words) + "\n")
    return result


def _plain(words: list[dict]) -> str:
    text, line = [], []
    for w in words:
        line.append(w["word"])
        if w["word"][-1:] in ".?!":
            text.append(" ".join(line))
            line = []
    if line:
        text.append(" ".join(line))
    return "\n".join(text)


def fmt(t: float) -> str:
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m):02d}:{s:05.2f}"


def _timestamped(words: list[dict]) -> str:
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["start"] - cur[-1]["end"] > 0.6):
            out.append(f"[{fmt(cur[0]['start'])} - {fmt(cur[-1]['end'])}] {' '.join(x['word'] for x in cur)}")
            cur = []
        cur.append(w)
        if w["word"][-1:] in ".?!":
            out.append(f"[{fmt(cur[0]['start'])} - {fmt(cur[-1]['end'])}] {' '.join(x['word'] for x in cur)}")
            cur = []
    if cur:
        out.append(f"[{fmt(cur[0]['start'])} - {fmt(cur[-1]['end'])}] {' '.join(x['word'] for x in cur)}")
    return "\n".join(out)
