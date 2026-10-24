"""Workspace and original-file protection.

Rules: originals are never modified, moved, renamed or deleted; every project works on a
read-only copy inside a local (not cloud-synced) workspace; the original's path and hash are
recorded so the relationship is never lost.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from datetime import date, datetime
from pathlib import Path

SUBDIRS = ("source", "working", "transcript", "assets", "preview", "final")

# Path fragments that mean "this folder is synced to a cloud service".
CLOUD_MARKERS = (
    "Library/Mobile Documents", "iCloud Drive", "iCloudDrive", "Library/CloudStorage",
    "Dropbox", "Google Drive", "GoogleDrive", "My Drive", "OneDrive", "Box Sync", "pCloud", "MEGA",
    "Nextcloud", "Sync.com",
)


class WorkspaceError(RuntimeError):
    pass


def is_cloud_synced(path: str | Path) -> str | None:
    """Return the matching cloud marker if `path` lives in a synced folder, else None."""
    p = str(Path(path).expanduser().resolve())
    for m in CLOUD_MARKERS:
        if f"/{m}/" in p + "/" or p.endswith("/" + m):
            return m
    return None


def default_root() -> Path:
    env = os.environ.get("VIDEO_EDITOR_HOME")
    if env:
        return Path(env).expanduser()
    home = Path.home()
    # Desktop/Documents are often iCloud-synced on macOS; prefer a plain folder in the home directory.
    return home / "VideoEditor"


def ensure_root(root: str | Path | None = None, allow_cloud: bool = False) -> Path:
    r = Path(root).expanduser() if root else default_root()
    marker = is_cloud_synced(r)
    if marker and not allow_cloud:
        raise WorkspaceError(f"{r} is inside a cloud-synced folder ({marker}); choose a local folder or pass allow_cloud")
    (r / "projects").mkdir(parents=True, exist_ok=True)
    return r


def slug(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return (s[:max_len].rstrip("-")) or "video"


def sha256(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def new_project(original: str | Path, name: str | None = None, root: str | Path | None = None,
                allow_cloud: bool = False, today: date | None = None) -> Path:
    """Create a project and copy the original in read-only. The original is only ever read."""
    original = Path(original).expanduser().resolve()
    if not original.is_file():
        raise WorkspaceError(f"original not found: {original}")
    r = ensure_root(root, allow_cloud)
    base = f"{(today or date.today()).isoformat()}_{slug(name or original.stem)}"
    proj = r / "projects" / base
    n = 2
    while proj.exists():
        proj = r / "projects" / f"{base}-{n}"
        n += 1
    for d in SUBDIRS:
        (proj / d).mkdir(parents=True)
    digest = sha256(original)
    copy = proj / "source" / f"original_{slug(original.stem)}{original.suffix.lower()}"
    shutil.copy2(original, copy)
    if sha256(copy) != digest:
        raise WorkspaceError("copy verification failed (hash mismatch)")
    copy.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # read-only: tools cannot overwrite it by accident
    meta = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "original_path": str(original),
        "original_filename": original.name,
        "original_sha256": digest,
        "original_size": original.stat().st_size,
        "source_copy": str(copy.relative_to(proj)),
        "outputs": [],
    }
    (proj / "project.json").write_text(json.dumps(meta, indent=2))
    return proj


def load(proj: str | Path) -> dict:
    return json.loads((Path(proj) / "project.json").read_text())


def save(proj: str | Path, meta: dict) -> None:
    (Path(proj) / "project.json").write_text(json.dumps(meta, indent=2))


def source_copy(proj: str | Path) -> Path:
    return Path(proj) / load(proj)["source_copy"]


def verify_original_untouched(proj: str | Path) -> bool:
    """True when the original still exists with the hash recorded at import."""
    meta = load(proj)
    p = Path(meta["original_path"])
    return p.is_file() and p.stat().st_size == meta["original_size"] and sha256(p) == meta["original_sha256"]


def guard_output(path: str | Path, proj: str | Path) -> Path:
    """Refuse any output path that is the original or outside the project."""
    path = Path(path).resolve()
    meta = load(proj)
    if path == Path(meta["original_path"]).resolve():
        raise WorkspaceError("refusing to write over the original file")
    if Path(proj).resolve() not in path.parents:
        raise WorkspaceError(f"refusing to write outside the project: {path}")
    if path == (Path(proj) / meta["source_copy"]).resolve():
        raise WorkspaceError("refusing to write over the protected source copy")
    return path
