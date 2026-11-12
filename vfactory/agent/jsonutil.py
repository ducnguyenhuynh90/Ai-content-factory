"""JSON helpers for model output: tolerant extraction, a small stdlib JSON-Schema validator, and the conversion of a
stage schema into the strict subset that provider-side structured outputs accept.

The validator covers the keywords the stage schemas use: type (incl. lists of types), properties, required,
additionalProperties (bool or schema), items, enum, const, minItems, maxItems, minLength, maxLength, minimum, maximum,
pattern, anyOf. Error messages name the JSON path so they can be fed back to a model verbatim.
"""

from __future__ import annotations

import copy
import json
import re

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


class JSONExtractError(ValueError):
    pass


def extract_json(text: str):
    """The first complete JSON object (or array) in a model reply. Strips <think>…</think> blocks (reasoning models
    served over OpenAI-compatible endpoints) and Markdown code fences; tolerates prose before and after."""
    if text is None:
        raise JSONExtractError("empty reply")
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fence = re.search(r"```(?:json|JSON)?\s*\n(.*?)\n```", t, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass  # fall through to the brace scan over the whole text
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start = next((i for i, c in enumerate(t) if c in "{["), None)
    if start is None:
        raise JSONExtractError("no JSON object found in the reply")
    span = _balanced(t, start)
    if span is None:
        raise JSONExtractError("the JSON object is not closed (reply truncated?)")
    try:
        return json.loads(t[start:span])
    except json.JSONDecodeError as e:
        raise JSONExtractError(f"invalid JSON: {e.msg} at line {e.lineno} column {e.colno}") from e


def _balanced(t: str, start: int) -> int | None:
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        c = t[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def _is_type(x, t: str) -> bool:
    if t == "integer":
        return isinstance(x, int) and not isinstance(x, bool)
    if t == "number":
        return isinstance(x, (int, float)) and not isinstance(x, bool)
    return isinstance(x, _TYPES[t])


def validate(data, schema: dict, path: str = "$", max_errors: int = 40) -> list[str]:
    """Validate `data` against `schema`; returns a list of human-readable errors (empty = valid)."""
    errors: list[str] = []
    _validate(data, schema, path, errors)
    return errors[:max_errors]


def _validate(x, s: dict, path: str, errors: list[str]) -> None:
    if not s:
        return
    if "anyOf" in s:
        branches = []
        for sub in s["anyOf"]:
            e: list[str] = []
            _validate(x, sub, path, e)
            if not e:
                break
            branches.append(e)
        else:
            errors.append(f"{path}: matches none of the allowed shapes ({'; '.join(b[0] for b in branches if b)})")
        return
    t = s.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(x, tt) for tt in ts):
            errors.append(f"{path}: expected {' or '.join(ts)}, got {type(x).__name__}")
            return
    if "const" in s and x != s["const"]:
        errors.append(f"{path}: must be {s['const']!r}")
    if "enum" in s and x not in s["enum"]:
        errors.append(f"{path}: {x!r} is not one of {s['enum']}")
    if isinstance(x, str):
        if "minLength" in s and len(x) < s["minLength"]:
            errors.append(f"{path}: shorter than {s['minLength']} characters")
        if "maxLength" in s and len(x) > s["maxLength"]:
            errors.append(f"{path}: {len(x)} characters, max {s['maxLength']}")
        if "pattern" in s and not re.search(s["pattern"], x):
            errors.append(f"{path}: does not match /{s['pattern']}/")
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        if "minimum" in s and x < s["minimum"]:
            errors.append(f"{path}: {x} < minimum {s['minimum']}")
        if "maximum" in s and x > s["maximum"]:
            errors.append(f"{path}: {x} > maximum {s['maximum']}")
    if isinstance(x, list):
        if "minItems" in s and len(x) < s["minItems"]:
            errors.append(f"{path}: {len(x)} items, need at least {s['minItems']}")
        if "maxItems" in s and len(x) > s["maxItems"]:
            errors.append(f"{path}: {len(x)} items, at most {s['maxItems']}")
        if "items" in s:
            for i, y in enumerate(x):
                _validate(y, s["items"], f"{path}[{i}]", errors)
    if isinstance(x, dict):
        props = s.get("properties", {})
        for r in s.get("required", []):
            if r not in x:
                errors.append(f"{path}: missing required field '{r}'")
        for k, y in x.items():
            if k in props:
                _validate(y, props[k], f"{path}.{k}", errors)
            else:
                ap = s.get("additionalProperties", True)
                if ap is False:
                    errors.append(f"{path}: unexpected field '{k}'")
                elif isinstance(ap, dict):
                    _validate(y, ap, f"{path}.{k}", errors)


# keywords the providers' constrained decoders do not take; we keep checking them client-side
_UNSUPPORTED = ("minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems", "pattern", "description_long")


def strict_subset(schema: dict) -> dict | None:
    """The schema as Anthropic/OpenAI structured outputs accept it: every object closed (additionalProperties false)
    and numeric/length/array-size constraints removed (still enforced by `validate`). Returns None when the schema
    has an open object (free-form keys), which constrained decoding cannot express; the caller then relies on the
    prompt + validation + repair loop instead."""
    s = copy.deepcopy(schema)

    def walk(n) -> bool:
        if not isinstance(n, dict):
            return True
        for k in _UNSUPPORTED:
            n.pop(k, None)
        t = n.get("type")
        if t == "object" or (isinstance(t, list) and "object" in t):
            ap = n.get("additionalProperties", True)
            if ap is not False or not n.get("properties"):
                return False
        ok = True
        for k in ("properties",):
            for v in (n.get(k) or {}).values():
                ok = walk(v) and ok
        if isinstance(n.get("items"), dict):
            ok = walk(n["items"]) and ok
        for v in n.get("anyOf", []) or []:
            ok = walk(v) and ok
        return ok

    return s if walk(s) else None


def all_required(schema: dict) -> dict:
    """OpenAI strict mode wants every property listed in `required` (optional ones typed nullable). Used only when a
    provider is configured with json_mode = "schema_strict"."""
    s = copy.deepcopy(schema)

    def walk(n):
        if isinstance(n, dict):
            if isinstance(n.get("properties"), dict):
                req = set(n.get("required", []))
                for k, v in n["properties"].items():
                    if k not in req and isinstance(v, dict) and "type" in v:
                        t = v["type"] if isinstance(v["type"], list) else [v["type"]]
                        if "null" not in t:
                            v["type"] = t + ["null"]
                n["required"] = list(n["properties"])
                for v in n["properties"].values():
                    walk(v)
            if isinstance(n.get("items"), dict):
                walk(n["items"])
            for v in n.get("anyOf", []) or []:
                walk(v)
    walk(s)
    return s
