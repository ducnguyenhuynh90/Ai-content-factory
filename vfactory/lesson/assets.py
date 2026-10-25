"""Picture assets for stage scenes: Microsoft Fluent Emoji, 3D style (MIT licence).

1,594 characters, animals, faces and objects a four-year-old recognises (a balloon, sheep, a piggy bank, a
crying face). `data/fluent_3d.tsv` lists every name; images are fetched on first use from the project's
GitHub repository and cached in ~/.cache/vfactory/fluent. Nothing is uploaded.
"""

from __future__ import annotations

import re
import shutil
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

CATALOG = Path(__file__).with_name("data") / "fluent_3d.tsv"
CACHE = Path.home() / ".cache" / "vfactory" / "fluent"
BASE = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/"
CREDIT = "Illustrations: Fluent Emoji © Microsoft, MIT licence"
LICENSE = """MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


class AssetError(LookupError):
    pass


@lru_cache(maxsize=1)
def catalog() -> dict[str, str]:
    """{name: path inside assets/<name>/3D/} with names matched case-insensitively."""
    out = {}
    for line in CATALOG.read_text().splitlines():
        name, rel = line.split("\t")
        out[name.lower()] = f"{name}/3D/{rel}" if not rel.startswith("Default/") else f"{name}/Default/3D/{rel[8:]}"
    return out


def exists(name: str) -> bool:
    return name.lower() in catalog()


def search(word: str, limit: int = 20) -> list[str]:
    """Names containing every word of the query: search("sad face") -> ["Sad but relieved face", ...]."""
    ws = word.lower().split()
    names = [line.split("\t")[0] for line in CATALOG.read_text().splitlines()]
    return [n for n in names if all(w in n.lower() for w in ws)][:limit]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fetch(name: str) -> Path:
    rel = catalog().get(name.lower())
    if not rel:
        hint = search(name.split()[0]) if name.split() else []
        raise AssetError(f"no picture called {name!r}" + (f"; similar: {', '.join(hint[:8])}" if hint else ""))
    dst = CACHE / f"{slug(name)}.png"
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    CACHE.mkdir(parents=True, exist_ok=True)
    url = BASE + urllib.parse.quote(rel)
    try:
        with urllib.request.urlopen(url, timeout=30) as r, open(dst.with_suffix(".part"), "wb") as f:
            shutil.copyfileobj(r, f)
    except OSError as e:
        raise AssetError(f"could not download {name!r} from raw.githubusercontent.com ({e}); "
                         f"allow that host or place the PNG at {dst}") from e
    dst.with_suffix(".part").rename(dst)
    return dst


def install(names: set[str], proj: Path) -> dict[str, str]:
    """Copy the pictures a project uses into <proj>/assets/img; returns {name: src relative to index.html}."""
    out_dir = proj / "assets" / "img"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "LICENSE-fluentui-emoji.txt").write_text(LICENSE)
    srcs = {}
    for n in sorted(names):
        p = fetch(n)
        shutil.copy2(p, out_dir / p.name)
        srcs[n] = f"assets/img/{p.name}"
    return srcs
