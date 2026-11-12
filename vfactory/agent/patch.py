"""Patch-style edits to lesson.json (the critique and fix stages never rewrite the whole file).

An op is {"op": "replace"|"add"|"remove"|"test", "path": "/beats/@b07/narration", "value": ..., "value_json": "..."}
- `path` is a JSON Pointer (RFC 6901); a segment "@ID" selects the element of a list whose "id" is ID, so ops stay
  correct when beats are inserted or removed ("/beats/@b07/visual/caption"). "-" appends to a list.
- `value_json` (a JSON string) may replace `value`: providers' strict structured outputs cannot express "any JSON
  value", but they can express a string.
Ops apply to a copy, all or nothing.
"""

from __future__ import annotations

import copy
import json

OPS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["replace", "add", "remove", "test"]},
            "path": {"type": "string", "pattern": "^/"},
            "value_json": {"type": "string"},
            "why": {"type": "string"},
        },
        "required": ["op", "path"],
        "additionalProperties": False,
    },
}


class PatchError(ValueError):
    pass


def _unescape(seg: str) -> str:
    return seg.replace("~1", "/").replace("~0", "~")


def _index(container, seg: str, path: str, for_add: bool = False):
    if isinstance(container, list):
        if seg.startswith("@"):
            want = seg[1:]
            for i, x in enumerate(container):
                if isinstance(x, dict) and str(x.get("id")) == want:
                    return i
            raise PatchError(f"{path}: no element with id {want!r}")
        if seg == "-" and for_add:
            return len(container)
        try:
            i = int(seg)
        except ValueError as e:
            raise PatchError(f"{path}: {seg!r} is not a list index") from e
        if not (0 <= i < len(container) + (1 if for_add else 0)):
            raise PatchError(f"{path}: index {i} out of range ({len(container)} items)")
        return i
    if isinstance(container, dict):
        return seg
    raise PatchError(f"{path}: cannot descend into a {type(container).__name__}")


def _walk(doc, path: str):
    if not path.startswith("/"):
        raise PatchError(f"path must start with '/': {path!r}")
    segs = [_unescape(s) for s in path.split("/")[1:]]
    parent = doc
    for seg in segs[:-1]:
        k = _index(parent, seg, path)
        try:
            parent = parent[k]
        except (KeyError, IndexError) as e:
            raise PatchError(f"{path}: '{seg}' does not exist") from e
    return parent, segs[-1]


def op_value(op: dict):
    if "value" in op:
        return op["value"]
    if "value_json" in op:
        try:
            return json.loads(op["value_json"])
        except json.JSONDecodeError as e:
            raise PatchError(f"{op.get('path')}: value_json is not valid JSON ({e.msg})") from e
    raise PatchError(f"{op.get('path')}: '{op.get('op')}' needs value or value_json")


def apply_ops(doc: dict, ops: list[dict]) -> dict:
    """Return a patched deep copy; raises PatchError (nothing applied) on the first bad op."""
    out = copy.deepcopy(doc)
    for n, op in enumerate(ops):
        kind, path = op.get("op"), op.get("path", "")
        try:
            parent, last = _walk(out, path)
            if kind == "remove":
                k = _index(parent, last, path)
                if isinstance(parent, dict) and k not in parent:
                    raise PatchError(f"{path}: nothing to remove")
                del parent[k]
            elif kind == "replace":
                k = _index(parent, last, path)
                if isinstance(parent, dict) and k not in parent:
                    parent[k] = op_value(op)  # lenient: replacing a missing key adds it
                else:
                    parent[k] = op_value(op)
            elif kind == "add":
                k = _index(parent, last, path, for_add=True)
                if isinstance(parent, list):
                    parent.insert(k, op_value(op))
                else:
                    parent[k] = op_value(op)
            elif kind == "test":
                k = _index(parent, last, path)
                if parent[k] != op_value(op):
                    raise PatchError(f"{path}: test failed")
            else:
                raise PatchError(f"op {n}: unknown op {kind!r}")
        except PatchError as e:
            raise PatchError(f"op {n} ({kind} {path}): {e}") from e
    return out
