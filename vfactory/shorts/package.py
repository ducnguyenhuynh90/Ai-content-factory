"""Publish kit: everything the person needs to post by hand in under a minute.

publish/
  cover.jpg      1080x1920 cover; text kept inside the centre 3:4 that the TikTok profile grid shows
  post.md        caption + hashtags (copy-paste), pinned comment with sources, the posting checklist
  post.json      the same, machine-readable (for a scheduler or the TikTok Content Posting API)

We never auto-post: posting needs the person's account and judgement. The Content Posting API needs an approved
developer app; until then the person uploads, and `log-post` records the URL for analytics.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from . import channel as C
from . import render as R
from . import schema

CAPTION_MAX = 2200  # keep well under TikTok's limit; only the first ~80 characters show before "more"


def caption_text(S: dict) -> str:
    meta = S["meta"]
    tags = " ".join(dict.fromkeys(meta.get("hashtags", [])))
    parts = [meta.get("caption", "").strip()]
    if meta.get("disclaimer"):
        parts.append(meta["disclaimer"])
    parts.append(tags)
    return "\n\n".join(p for p in parts if p)[:CAPTION_MAX]


def pinned_comment(S: dict) -> str:
    srcs = S.get("sources", [])
    if not srcs:
        return ""
    vi = schema.lang_of(S) == "vi"
    head = "Nguồn:" if vi else "Sources:"
    return head + " " + " | ".join(s["cite"].split(",")[0] + (f" ({s['url']})" if s.get("url") else "") for s in srcs[:4])


def cover(S: dict, out: Path) -> Path:
    meta = S["meta"]
    ctx = R.Ctx(1080, 1920, 30, R.theme(meta.get("theme", "night"), meta.get("theme_overrides")), schema.lang_of(S))
    img = R.Background(ctx).frame(0.0)
    hook = S["beats"][0]["visual"]
    text = meta.get("cover_text") or " ".join(hook.get("lines", [])) or meta.get("title", "")
    pic = hook.get("picture")
    y_text = ctx.H * 0.5
    if pic:
        try:
            p = R.picture(pic, int(ctx.W * 0.38))
            R.put(img, p, ctx.W / 2, ctx.H * 0.32)
            y_text = ctx.H * 0.56
        except Exception:  # a missing picture must not block the kit
            pass
    for sp in R.block(ctx, text, R.DISPLAY, None, 170, ctx.W / 2, y_text, max_w=ctx.W * 0.84, max_lines=3, upper=True,
                      highlight=hook.get("highlight") or meta.get("cover_highlight")):
        R.put(img, sp.img, sp.x, sp.y)
    if meta.get("series"):
        label = meta["series"] + (f" · {meta['part']}" if meta.get("part") else "")
        pl = R.pill(ctx, label.upper(), 34, fill=ctx.th["accent"], color=ctx.th["on_accent"])
        R.put(img, pl, ctx.W / 2, ctx.H * 0.14)
    img.convert("RGB").save(out, quality=92)
    return out


def checklist(S: dict, build: dict, ch: dict) -> list[str]:
    vi = schema.lang_of(S) == "vi"
    slots = ", ".join((ch.get("cadence") or {}).get("slots", [])) or ("11:30, 20:00" if vi else "your audience's peak hours")
    nm = Path(build.get("video_nomusic", "")).name
    if vi:
        items = [
            f"Tải lên `{Path(build['video']).name}` (đã có nhạc gốc, an toàn bản quyền)"
            + (f" — hoặc `{nm}` rồi thêm âm thanh đang thịnh hành trong app ở âm lượng 5-10 %" if nm else ""),
            "Dán caption + hashtag từ mục dưới; chọn `cover.jpg` làm ảnh bìa.",
            "Bật nhãn **Nội dung do AI tạo** (giọng đọc/hình ảnh tạo bằng AI) trong Cài đặt khác.",
            "Ghim bình luận nguồn (mục bên dưới) ngay sau khi đăng.",
            f"Khung giờ đăng của kênh: {slots}. Trả lời 10 bình luận đầu trong 60 phút.",
            f"Sau khi đăng: `python -m vfactory.shorts log-post <short.json> --url <link>`; sau 48-72 giờ nhập số liệu.",
        ]
    else:
        items = [
            f"Upload `{Path(build['video']).name}` (original score, copyright-safe)"
            + (f" — or `{nm}` and add a trending sound in-app at 5-10 % volume" if nm else ""),
            "Paste the caption + hashtags below; pick `cover.jpg` as the cover.",
            "Turn on the **AI-generated content** label (AI voice/visuals) under More options.",
            "Pin the sources comment below right after posting.",
            f"Channel posting slots: {slots}. Reply to the first 10 comments within an hour.",
            "After posting: `python -m vfactory.shorts log-post <short.json> --url <link>`; import metrics after 48-72 h.",
        ]
    return items


def package(short_path: str | Path, out_dir: str | Path | None = None) -> dict:
    short_path = Path(short_path)
    S = schema.load(short_path)
    bdir = short_path.parent / "build"
    bj = bdir / "build.json"
    if not bj.exists():
        raise FileNotFoundError(f"no build yet: run `python -m vfactory.shorts build {short_path} --final` first")
    build = json.loads(bj.read_text())
    root = C.find_channel(short_path)
    ch = C.load(root) if root else {}
    out = Path(out_dir or short_path.parent / "publish")
    out.mkdir(parents=True, exist_ok=True)
    cov = cover(S, out / "cover.jpg")
    shutil.copy2(build["frame0"], out / "frame0.png") if build.get("frame0") and Path(build["frame0"]).exists() else None
    kit = {
        "slug": short_path.parent.name,
        "video": build["video"], "video_nomusic": build.get("video_nomusic"),
        "duration": build["duration"], "cover": str(cov),
        "caption": caption_text(S), "pinned_comment": pinned_comment(S),
        "checklist": checklist(S, build, ch),
        "meta": {k: S["meta"].get(k) for k in ("title", "format", "hook_type", "pillar", "series", "part")},
        "ai_generated_label": True,
        "draft_warning": "draft" in Path(build["video"]).name,
    }
    (out / "post.json").write_text(json.dumps(kit, ensure_ascii=False, indent=1))
    vi = schema.lang_of(S) == "vi"
    md = [f"# {S['meta'].get('title', '')}", "",
          f"**Video:** `{build['video']}` ({build['duration']:.1f}s)" + ("  ⚠ bản nháp — build `--final` trước khi đăng" if kit["draft_warning"] else ""),
          f"**Cover:** `{cov}`", "",
          "## Caption" if not vi else "## Caption (copy)", "```", kit["caption"], "```", ""]
    if kit["pinned_comment"]:
        md += ["## Pinned comment" if not vi else "## Bình luận ghim", "```", kit["pinned_comment"], "```", ""]
    md += ["## Checklist", *[f"- [ ] {c}" for c in kit["checklist"]], ""]
    (out / "post.md").write_text("\n".join(md))
    return kit
