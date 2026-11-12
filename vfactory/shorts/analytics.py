"""The learning loop: TikTok Studio numbers -> what to make more of.

Import: TikTok Studio → Analytics → Content → (per video) or the "Download data" export, saved as CSV.
Column names differ by export and UI language, so we match aliases (English + Vietnamese). Anything we can't
read can be added by hand with `metrics add`.

Signals, in the order TikTok's recommender is generally understood to weigh them (and that we can act on):
  1. average % watched (avg watch time / duration) and full-watch rate  → hook + pacing
  2. shares and saves per 1k views                                       → value of the idea
  3. comments per 1k views                                               → the question / controversy
  4. follows per 1k views                                                → series + CTA
Views alone mostly measure distribution luck in the first hours; we rank on 1-4.
"""

from __future__ import annotations

import csv
import json
import re
import statistics as st
from datetime import date
from pathlib import Path

from . import channel as C

METRIC_COLS = ["slug", "video_id", "url", "title", "posted_at", "captured_at", "views", "avg_watch_s",
               "completion_pct", "likes", "comments", "shares", "saves", "follows"]
ALIASES = {
    "video_id": ["video id", "id video", "item id"],
    "url": ["video link", "link", "url", "liên kết"],
    "title": ["video title", "title", "tiêu đề", "mô tả", "description", "caption"],
    "posted_at": ["post time", "posted", "date posted", "create time", "thời gian đăng", "ngày đăng"],
    "views": ["total views", "video views", "views", "lượt xem", "tổng lượt xem"],
    "avg_watch_s": ["average watch time", "avg. watch time", "avg watch time", "thời gian xem trung bình"],
    "completion_pct": ["watched full video", "full video watched", "completion rate", "xem hết video", "tỷ lệ xem hết"],
    "likes": ["total likes", "likes", "lượt thích"],
    "comments": ["total comments", "comments", "bình luận"],
    "shares": ["total shares", "shares", "lượt chia sẻ", "chia sẻ"],
    "saves": ["total saves", "saves", "favorites", "lượt lưu", "yêu thích"],
    "follows": ["new followers", "followers gained", "follows", "người theo dõi mới"],
}


COUNTS = ("views", "likes", "comments", "shares", "saves", "follows")


def _num(v, count: bool = False) -> float | None:
    """Parse '12,400', '12.400' (vi, counts only), '1.2K', '21.3s', '0:21', '18.2%'. Durations and percentages
    use '.' as the decimal point; only whole-number counts read '12.400' as twelve thousand four hundred."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower().replace(" ", "").replace(" ", "")
    if not s or s in ("-", "--", "n/a"):
        return None
    mult = 1.0
    if s.endswith("k"):
        mult, s = 1e3, s[:-1]
    elif s.endswith("m"):
        mult, s = 1e6, s[:-1]
    if re.fullmatch(r"\d+(:\d+){1,2}", s):  # 0:12 or 0:00:12
        parts = [float(x) for x in s.split(":")]
        return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
    s = s.rstrip("s%")
    if count and re.fullmatch(r"\d{1,3}(\.\d{3})+", s):  # 1.234.567 (vi thousands)
        s = s.replace(".", "").replace(",", ".")
    s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s) else s.replace(",", ".")
    try:
        return float(s) * mult
    except ValueError:
        return None


def _match(header: str) -> str | None:
    h = header.strip().lower()
    for key, names in ALIASES.items():
        if h in names:
            return key
    for key, names in ALIASES.items():
        if any(n in h for n in names):
            return key
    return None


def read_export(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        try:
            import openpyxl  # type: ignore
        except ImportError as e:
            raise RuntimeError("save the export as CSV, or pip install openpyxl") from e
        ws = openpyxl.load_workbook(path, read_only=True).active
        rows = [[("" if c is None else str(c)) for c in r] for r in ws.iter_rows(values_only=True)]
    else:
        text = path.read_text(encoding="utf-8-sig")
        dialect = csv.Sniffer().sniff(text[:2000], delimiters=",;\t") if text else csv.excel
        rows = list(csv.reader(text.splitlines(), dialect))
    hi = next((i for i, r in enumerate(rows) if sum(_match(c) is not None for c in r) >= 2), None)
    if hi is None:
        raise ValueError(f"no recognisable header in {path} (need e.g. 'Video title', 'Total views')")
    keys = [_match(c) for c in rows[hi]]
    out = []
    for r in rows[hi + 1:]:
        rec = {}
        for k, v in zip(keys, r):
            if k and v not in ("", None) and k not in rec:
                rec[k] = v
        if rec.get("views") is not None or rec.get("title"):
            out.append(rec)
    return out


def _link(rec: dict, posts: list[dict]) -> str | None:
    vid = str(rec.get("video_id", "")).strip()
    url = str(rec.get("url", "")).strip()
    for p in posts:
        if vid and vid in (p.get("video_id", ""), p.get("url", "")):
            return p["slug"]
        if url and p.get("url") and (url in p["url"] or p["url"] in url):
            return p["slug"]
    t = re.sub(r"\W+", " ", str(rec.get("title", "")).lower()).strip()
    for p in posts:
        pt = re.sub(r"\W+", " ", p.get("title", "").lower()).strip()
        if t and pt and (t[:40] in pt or pt[:40] in t):
            return p["slug"]
    return None


def import_export(root: str | Path, path: str | Path) -> dict:
    root = Path(root).expanduser()
    posts = C.read_posts(root)
    recs = read_export(path)
    today = date.today().isoformat()
    rows, unmatched = [], []
    for r in recs:
        slug = r.get("slug") or _link(r, posts)
        if not slug:
            unmatched.append(r.get("title") or r.get("url") or r.get("video_id"))
            continue
        row = {"slug": slug, "captured_at": today}
        for k in METRIC_COLS:
            if k in r and k not in row:
                row[k] = r[k]
        rows.append(row)
    _append(root, rows)
    return {"imported": len(rows), "unmatched": unmatched}


def add(root: str | Path, slug: str, **vals) -> None:
    _append(Path(root).expanduser(), [{"slug": slug, "captured_at": date.today().isoformat(),
                                       **{k: v for k, v in vals.items() if v is not None}}])


def _append(root: Path, rows: list[dict]) -> None:
    p = root / "metrics.csv"
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, METRIC_COLS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def latest(root: Path) -> dict[str, dict]:
    p = root / "metrics.csv"
    if not p.exists():
        return {}
    out = {}
    with open(p, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["slug"] not in out or r.get("captured_at", "") >= out[r["slug"]].get("captured_at", ""):
                out[r["slug"]] = r
    return out


def _short_meta(root: Path, slug: str) -> dict:
    d = root / "shorts" / slug
    meta = {}
    sj = d / "short.json"
    if sj.exists():
        meta = json.loads(sj.read_text(encoding="utf-8")).get("meta", {})
    bj = d / "build" / "build.json"
    if bj.exists():
        meta["duration"] = json.loads(bj.read_text()).get("duration")
    return meta


def score(root: str | Path) -> list[dict]:
    root = Path(root).expanduser()
    posts = {p["slug"]: p for p in C.read_posts(root)}
    out = []
    for slug, m in latest(root).items():
        meta = _short_meta(root, slug)
        p = posts.get(slug, {})
        dur = _num(meta.get("duration")) or _num(p.get("duration"))
        views = _num(m.get("views"), True) or 0
        aw = _num(m.get("avg_watch_s"))
        k = 1000 / views if views else 0
        row = {
            "slug": slug, "views": int(views), "duration": dur,
            "format": meta.get("format") or p.get("format", ""), "hook_type": meta.get("hook_type") or p.get("hook_type", ""),
            "pillar": meta.get("pillar") or p.get("pillar", ""),
            "avg_watch_s": aw, "avg_pct": round(100 * aw / dur, 1) if aw and dur else None,
            "full_pct": _num(m.get("completion_pct")),
            "shares_1k": round((_num(m.get("shares"), True) or 0) * k, 2) if views else None,
            "saves_1k": round((_num(m.get("saves"), True) or 0) * k, 2) if views else None,
            "comments_1k": round((_num(m.get("comments"), True) or 0) * k, 2) if views else None,
            "follows_1k": round((_num(m.get("follows"), True) or 0) * k, 2) if views else None,
        }
        out.append(row)
    return out


def _med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 2) if xs else None


def insights(root: str | Path) -> dict:
    """Rank videos, compare groups (format, hook type, pillar, length) against the channel median."""
    root = Path(root).expanduser()
    rows = score(root)
    if not rows:
        return {"rows": [], "markdown": "No metrics yet: `metrics import` a TikTok Studio CSV or `metrics add` by hand.\n"}
    base = {k: _med(r[k] for r in rows) for k in ("avg_pct", "full_pct", "shares_1k", "saves_1k", "comments_1k", "follows_1k")}
    for r in rows:
        bucket = r["duration"]
        r["length"] = "" if not bucket else "<25s" if bucket < 25 else "25-45s" if bucket < 45 else "45-75s" if bucket < 75 else "75s+"
    groups = {}
    for dim in ("hook_type", "format", "pillar", "length"):
        g = {}
        for r in rows:
            if r[dim]:
                g.setdefault(r[dim], []).append(r)
        groups[dim] = {k: {"n": len(v), "avg_pct": _med(x["avg_pct"] for x in v), "shares_1k": _med(x["shares_1k"] for x in v),
                           "follows_1k": _med(x["follows_1k"] for x in v)} for k, v in g.items()}
    recs = []
    for dim, g in groups.items():
        for k, s in g.items():
            if s["n"] < 2 or base["avg_pct"] is None or s["avg_pct"] is None:
                continue
            d = s["avg_pct"] - base["avg_pct"]
            if abs(d) >= 5:
                recs.append(f"{'More' if d > 0 else 'Less'} {dim} = **{k}**: median watched {s['avg_pct']}% vs channel "
                            f"{base['avg_pct']}% (n={s['n']})")
    weak_hooks = [r["slug"] for r in rows if r["avg_watch_s"] is not None and r["avg_watch_s"] < 3.0]
    if weak_hooks:
        recs.append(f"Hook not holding (avg watch < 3 s): {', '.join(weak_hooks)} — rewrite the first line/frame, "
                    "check that the hook matches the cover and caption")
    ranked = sorted(rows, key=lambda r: (r["avg_pct"] or 0) + 4 * (r["shares_1k"] or 0) + 2 * (r["follows_1k"] or 0), reverse=True)
    md = ["# Channel insights", f"_{date.today().isoformat()} · {len(rows)} videos · ranked on watched % + shares + follows, not views_", "",
          "## Channel medians", *[f"- {k}: {v}" for k, v in base.items()], "",
          "## Videos", "| slug | views | len | watched % | full % | shares/1k | saves/1k | comments/1k | follows/1k | hook | format |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in ranked:
        md.append(f"| {r['slug']} | {r['views']} | {r['duration'] or ''} | {r['avg_pct'] or ''} | {r['full_pct'] or ''} | "
                  f"{r['shares_1k'] or ''} | {r['saves_1k'] or ''} | {r['comments_1k'] or ''} | {r['follows_1k'] or ''} | "
                  f"{r['hook_type']} | {r['format']} |")
    md += ["", "## By group (median)"]
    for dim, g in groups.items():
        if g:
            md.append(f"- **{dim}**: " + "; ".join(f"{k} n={s['n']} watched {s['avg_pct']}% shares/1k {s['shares_1k']}" for k, s in g.items()))
    md += ["", "## What to do next", *([f"- {r}" for r in recs] or ["- Not enough videos per group yet (need ≥ 2 each): keep tagging format and hook_type."])]
    md += ["", "_Small samples lie: treat a difference as a hypothesis to test in the next 3-5 videos, not a law._"]
    text = "\n".join(md) + "\n"
    (root / "insights.md").write_text(text)
    (root / "insights.json").write_text(json.dumps({"rows": ranked, "baseline": base, "groups": groups, "recommendations": recs},
                                                   ensure_ascii=False, indent=1))
    if recs:
        with open(root / "learnings.md", "a", encoding="utf-8") as fh:
            fh.write(f"\n## {date.today().isoformat()} (from insights, {len(rows)} videos)\n" + "\n".join(f"- {r}" for r in recs) + "\n")
    return {"rows": ranked, "baseline": base, "groups": groups, "recommendations": recs, "markdown": text}
