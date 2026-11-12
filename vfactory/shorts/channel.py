"""A channel workspace: the bible every script is written against, the post ledger and the learnings loop.

<channel>/
  channel.json     niche, audience, language, voice, look, pillars, hashtags, cadence, rules
  learnings.md     what the numbers taught us (written by `insights`, edited by the person)
  ideas.md         backlog of concepts from trend research
  posts.csv        one row per published short: slug, url, video_id, posted_at, title
  metrics.csv      one row per (video, capture date): views, avg watch, completion, likes, shares...
  shorts/NNN-slug/short.json (+ script.md, build/, publish/)

It lives OUTSIDE this repo (default ~/TikTokChannels/<name>); only examples are committed here.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

DEFAULT_ROOT = Path.home() / "TikTokChannels"
POSTS_COLS = ["slug", "title", "url", "video_id", "posted_at", "format", "hook_type", "pillar", "duration"]


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48] or "short"


def template(name: str, niche: str, lang: str = "vi", handle: str = "") -> dict:
    vi = lang.startswith("vi")
    return {
        "name": name,
        "handle": handle,
        "niche": niche,
        "lang": lang,
        "audience": "người 18-34 tò mò, xem trên điện thoại, thường tắt tiếng" if vi else "curious 18-34 viewers, phone, often sound-off",
        "promise": "Mỗi video: một câu chuyện có thật, một bài học dùng được, dưới 60 giây." if vi else
                   "Every video: one true story, one usable lesson, under 60 seconds.",
        "pillars": ["lịch sử", "tâm lý học", "tiền & đầu tư"] if vi else ["history", "psychology", "money"],
        "voice": "vi-VN-NamMinhNeural" if vi else "en-US-AndrewMultilingualNeural",
        "rate": "+8%",
        "theme": "night",
        "theme_overrides": {},
        "music": "curious",
        "target_seconds": [25, 50],
        "base_hashtags": ["#kienthuc", "#lichsu"] if vi else ["#history", "#learnontiktok"],
        "series": "",
        "cta": "Theo dõi để xem phần tiếp" if vi else "Follow for part 2",
        "cadence": {"per_week": 5, "slots": ["11:30", "20:00"], "timezone": "Asia/Ho_Chi_Minh" if vi else "UTC"},
        "rules": [
            "Không bịa số liệu, trích dẫn hay sự kiện; mọi con số có nguồn." if vi else "No invented facts, quotes or numbers.",
            "Không dùng hình/giọng giả mạo người thật." if vi else "No generated likeness or voice of a real person.",
            "Tài chính/sức khỏe: chỉ nguyên tắc, không khuyến nghị mua bán; luôn có miễn trừ." if vi else
            "Finance/health: principles only, never tips; always a disclaimer.",
        ],
        "avoid_topics": [],
        "disclaimer": "",
    }


def init(path: str | Path, name: str, niche: str, lang: str = "vi", handle: str = "") -> Path:
    root = Path(path).expanduser()
    (root / "shorts").mkdir(parents=True, exist_ok=True)
    cj = root / "channel.json"
    if not cj.exists():
        cj.write_text(json.dumps(template(name, niche, lang, handle), ensure_ascii=False, indent=2))
    for f, body in (("learnings.md", f"# Learnings — {name}\n\n_Written by `insights` after each analytics import; "
                                      "edit freely. The agent reads this before every new script._\n"),
                    ("ideas.md", f"# Ideas — {name}\n\n"),):
        if not (root / f).exists():
            (root / f).write_text(body)
    if not (root / "posts.csv").exists():
        with open(root / "posts.csv", "w", newline="") as fh:
            csv.writer(fh).writerow(POSTS_COLS)
    return root


def load(path: str | Path) -> dict:
    p = Path(path).expanduser()
    p = p / "channel.json" if p.is_dir() else p
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def find_channel(start: str | Path) -> Path | None:
    """The channel folder that contains `start` (a short.json or its folder)."""
    p = Path(start).expanduser().resolve()
    for d in [p, *p.parents]:
        if (d / "channel.json").exists():
            return d
    return None


def next_number(root: Path) -> int:
    nums = [int(m.group(1)) for d in (root / "shorts").glob("*") if (m := re.match(r"(\d+)-", d.name))]
    return max(nums, default=0) + 1


def new_short(root: str | Path, title: str, slug: str | None = None) -> Path:
    """Scaffold shorts/NNN-slug/short.json from the channel bible. The agent then writes the beats."""
    root = Path(root).expanduser()
    ch = load(root)
    d = root / "shorts" / f"{next_number(root):03d}-{slug or slugify(title)}"
    d.mkdir(parents=True, exist_ok=False)
    vi = str(ch.get("lang", "vi")).startswith("vi")
    S = {
        "meta": {
            "title": title, "lang": ch.get("lang", "vi"), "pillar": (ch.get("pillars") or [""])[0], "format": "story",
            "hook_type": "", "target_seconds": ch.get("target_seconds", [25, 50]), "theme": ch.get("theme", "night"),
            "theme_overrides": ch.get("theme_overrides", {}), "voice": ch.get("voice", "vi-VN-NamMinhNeural"),
            "rate": ch.get("rate", "+8%"), "music": ch.get("music", "curious"), "series": ch.get("series", ""),
            "caption": "", "hashtags": list(ch.get("base_hashtags", [])), "cover_text": "",
            "disclaimer": ch.get("disclaimer", ""), "handle": ch.get("handle", ""),
        },
        "sources": [],
        "beats": [
            {"id": "h1", "narration": "", "visual": {"type": "hook", "lines": ["", ""], "punch_cue": ""}},
            {"id": "end", "narration": "", "visual": {"type": "end", "text": "", "cta": ch.get("cta", ""),
                                                       "handle": ch.get("handle", "")}},
        ],
        "pronounce": {},
    }
    (d / "short.json").write_text(json.dumps(S, ensure_ascii=False, indent=1))
    return d / "short.json"


def read_posts(root: Path) -> list[dict]:
    p = root / "posts.csv"
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def log_post(root: Path, row: dict) -> None:
    rows = [r for r in read_posts(root) if r.get("slug") != row.get("slug")]
    rows.append({k: row.get(k, "") for k in POSTS_COLS})
    with open(root / "posts.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, POSTS_COLS)
        w.writeheader()
        w.writerows(rows)
