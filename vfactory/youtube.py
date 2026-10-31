"""Schedule lesson videos on YouTube (YouTube Data API v3, standard library only).

    python -m vfactory.youtube whoami
    python -m vfactory.youtube schedule PLAN.json [--limit N] [--dry-run]

Credentials come from the environment (never from a file in the repo): YT_CLIENT_ID, YT_CLIENT_SECRET,
YT_REFRESH_TOKEN (get them once with scripts/youtube_auth.py on your own computer).

PLAN.json is a list of {"lesson", "video", "thumbnail", "publish_at"} (publish_at: RFC 3339, e.g.
"2026-10-31T19:00:00+07:00"). Each video is uploaded as private with status.publishAt, so YouTube publishes it at that
time; title, description and tags come from the lesson's meta.youtube. Uploaded ids are written to
PLAN.json.done so a rerun skips them; --limit N uploads at most N new videos (an upload costs 1,600 of the default
10,000 daily quota units, so about 6 a day), and a quota error stops the run cleanly so the next day's run resumes. Note: videos uploaded from an API project that has not passed YouTube's audit
stay private (publishAt does not make them public) until the project is audited.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
CHUNK = 8 * 1024 * 1024


def token() -> str:
    try:
        body = urllib.parse.urlencode({"client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
                                       "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    except KeyError as e:
        sys.exit(f"missing environment variable {e}: add YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN as secrets")
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body))["access_token"]


def call(tok: str, method: str, url: str, body: bytes | None = None, ctype: str = "application/json", headers=None):
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": ctype, **(headers or {})})
    return urllib.request.urlopen(req)


def whoami(tok: str) -> list[dict]:
    r = json.load(call(tok, "GET", f"{API}/channels?part=snippet,statistics&mine=true"))
    return [{"id": c["id"], "title": c["snippet"]["title"], "subscribers": c["statistics"].get("subscriberCount")}
            for c in r.get("items", [])]


def metadata(lesson: dict, publish_at: str) -> dict:
    y, m = lesson["meta"].get("youtube", {}), lesson["meta"]
    title = y.get("title") or m["title"]
    if len(title) > 100:
        raise ValueError(f"title over 100 characters: {title}")
    return {"snippet": {"title": title, "description": y.get("description", "")[:5000], "tags": y.get("tags", []),
                        "categoryId": "27", "defaultLanguage": "vi", "defaultAudioLanguage": "vi"},
            "status": {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True}}


def upload(tok: str, video: Path, meta: dict) -> str:
    size = video.stat().st_size
    start = call(tok, "POST", f"{UPLOAD}/videos?uploadType=resumable&part=snippet,status", json.dumps(meta).encode(),
                 "application/json; charset=UTF-8", {"X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    loc = start.headers["Location"]
    with open(video, "rb") as f:
        sent = 0
        while sent < size:
            chunk = f.read(CHUNK)
            end = sent + len(chunk) - 1
            try:
                r = call(tok, "PUT", loc, chunk, "video/mp4", {"Content-Range": f"bytes {sent}-{end}/{size}"})
                return json.load(r)["id"]
            except urllib.error.HTTPError as e:
                if e.code != 308:  # 308 = chunk accepted, keep going
                    raise
            sent = end + 1
    raise RuntimeError("upload ended without a video id")


def set_thumbnail(tok: str, vid: str, png: Path) -> None:
    call(tok, "POST", f"{UPLOAD}/thumbnails/set?videoId={vid}", png.read_bytes(), "image/png")


def schedule(plan_path: str, dry: bool, limit: int | None = None) -> None:
    plan = json.loads(Path(plan_path).read_text())
    done_p = Path(plan_path + ".done")
    done = json.loads(done_p.read_text()) if done_p.exists() else {}
    tok = None if dry else token()
    new = 0
    for item in plan:
        lesson = json.loads(Path(item["lesson"]).read_text())
        meta = metadata(lesson, item["publish_at"])
        key = item["lesson"]
        if key in done:
            print(f"skip (already uploaded as {done[key]}): {meta['snippet']['title']}")
            continue
        if limit is not None and new >= limit:
            print(f"limit {limit} reached; the rest waits for the next run")
            break
        new += 1
        print(f"{item['publish_at']}  {meta['snippet']['title']}")
        if dry:
            continue
        try:
            vid = upload(tok, Path(item["video"]), meta)
        except urllib.error.HTTPError as e:
            if e.code == 403 and b"quota" in e.read().lower():
                print("daily upload quota reached; rerun after midnight Pacific time")
                break
            raise
        try:
            set_thumbnail(tok, vid, Path(item["thumbnail"]))
        except urllib.error.HTTPError as e:  # custom thumbnails need a verified channel
            print(f"  thumbnail not set ({e.code}): upload it in Studio")
        done[key] = vid
        done_p.write_text(json.dumps(done, indent=1))
        print(f"  uploaded https://youtu.be/{vid}")


def main():
    a = sys.argv[1:]
    if a[:1] == ["whoami"]:
        for c in whoami(token()):
            print(f"{c['title']}  (id {c['id']}, {c['subscribers']} subscribers)")
    elif a[:1] == ["schedule"] and len(a) >= 2:
        limit = int(a[a.index("--limit") + 1]) if "--limit" in a else None
        schedule(a[1], "--dry-run" in a, limit)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
