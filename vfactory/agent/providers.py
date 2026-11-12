"""Model providers behind one small interface.

    provider.complete(system, messages, *, json_schema=None, images=None, max_tokens=16000) -> str

`messages` is a list of {"role": "user"|"assistant", "content": str}; the conversation always ends with a user turn
(no assistant prefill). `images` are file paths (or raw bytes) attached to the last user turn; providers that cannot
see images ignore them and say so via `supports_images`. The return value is the model's text; JSON is parsed and
validated by the caller (pipeline), so a provider never has to guarantee it.

- AnthropicProvider: the official `anthropic` SDK (optional install: `pip install anthropic`). Streams every request
  and reads `.get_final_message()`, adaptive thinking, `output_config.effort`, prompt caching on the stable system
  prompt, structured outputs via `output_config.format`, and server-side refusal fallbacks (beta) by default.
- OpenAICompatProvider: any OpenAI-compatible Chat Completions endpoint over stdlib urllib (OpenAI, OpenRouter,
  Gemini's OpenAI endpoint, Ollama, LM Studio, vLLM, llama.cpp server).
- FakeProvider: scripted replies for tests and dry runs.

Credentials come from environment variables only; nothing here prints or logs a key.
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .jsonutil import all_required, strict_subset


class ProviderError(RuntimeError):
    """A provider failed in a way the caller should report (bad config, network, truncated output)."""


class RefusalError(ProviderError):
    """The model declined the request (Anthropic stop_reason "refusal"), after any configured fallback."""

    def __init__(self, message: str, category: str | None = None):
        super().__init__(message)
        self.category = category


class TruncatedError(ProviderError):
    """The reply hit max_tokens even after the provider retried with a larger budget."""


# ---------------------------------------------------------------------------------------------------------- images

MAX_IMAGE_EDGE = 1568  # long edge that vision models use without downscaling server-side
MAX_IMAGE_BYTES = 3_500_000


def load_image(img) -> tuple[str, str]:
    """(media_type, base64 data) for a path or bytes; large images are downscaled with Pillow (a core dependency)."""
    raw = Path(img).read_bytes() if not isinstance(img, (bytes, bytearray)) else bytes(img)
    media = _sniff(raw)
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if max(im.size) > MAX_IMAGE_EDGE or len(raw) > MAX_IMAGE_BYTES or media not in ("image/jpeg", "image/png"):
            im = im.convert("RGB")
            im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85)
            raw, media = buf.getvalue(), "image/jpeg"
    except Exception:  # noqa: BLE001 - not an image Pillow can open: send as-is and let the API judge
        pass
    return media, base64.standard_b64encode(raw).decode("ascii")


def _sniff(raw: bytes) -> str:
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "application/octet-stream"


# ---------------------------------------------------------------------------------------------------------- base

@dataclass
class Provider:
    name: str = "provider"
    model: str = ""
    supports_images: bool = False

    def complete(self, system: str, messages: list[dict], *, json_schema: dict | None = None, images=None,
                 max_tokens: int = 16000) -> str:
        raise NotImplementedError

    def check(self, network: bool = True) -> dict:
        """Reachability without spending tokens: {ok, detail}. Overridden per provider."""
        return {"ok": True, "detail": "no check"}

    def describe(self) -> str:
        return f"{self.name} ({self.model})"


# ---------------------------------------------------------------------------------------------------------- Anthropic

ANTHROPIC_DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MAX_OUTPUT = 128_000


@dataclass
class AnthropicProvider(Provider):
    """Claude through the official SDK. Opus 5.5 notes: thinking is always on (adaptive; disabling it is a 400), effort
    defaults to "medium" server-side, so we always send it ("high" for writing); no temperature/top_p; no prefill."""

    name: str = "anthropic"
    model: str = ANTHROPIC_DEFAULT_MODEL
    effort: str = "high"
    fallbacks: bool = True             # server-side refusal fallbacks ("default" routing), beta endpoint
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None
    timeout: float = 900.0
    max_retries: int = 3
    supports_images: bool = True
    structured: bool = True            # use output_config.format when the schema allows it
    _client: object = field(default=None, repr=False)

    def __post_init__(self):
        if self.effort not in EFFORTS:
            raise ProviderError(f"effort must be one of {EFFORTS}, got {self.effort!r}")

    # -- the request, built without the SDK so it can be inspected and tested offline
    def build_request(self, system: str, messages: list[dict], *, json_schema: dict | None = None, images=None,
                      max_tokens: int = 16000) -> dict:
        msgs = []
        for i, m in enumerate(messages):
            content: list[dict] = [{"type": "text", "text": m["content"]}]
            if images and i == len(messages) - 1 and m["role"] == "user":
                imgs = []
                for img in images:
                    media, data = load_image(img)
                    imgs.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
                content = imgs + content  # images before the text that asks about them
            msgs.append({"role": m["role"], "content": content})
        if len(msgs) > 1 and msgs[0]["role"] == "user":
            # repair turns resend the (large) first user turn: cache it too (2 of 4 breakpoints)
            msgs[0]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        if msgs and msgs[-1]["role"] != "user":
            raise ProviderError("the conversation must end with a user turn (assistant prefill is not supported)")
        req: dict = {
            "model": self.model,
            "max_tokens": int(max_tokens),
            # the stable, shared system prompt is cached; it never contains per-run data
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": msgs,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.effort},
        }
        if json_schema is not None and self.structured:
            strict = strict_subset(json_schema)
            if strict is not None:
                req["output_config"]["format"] = {"type": "json_schema", "schema": strict}
        if self.fallbacks:
            req["betas"] = [FALLBACK_BETA]
            req["fallbacks"] = "default"
        return req

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic  # optional dependency
            except ImportError as e:
                raise ProviderError("the 'anthropic' package is not installed: pip install anthropic "
                                    "(or pick another provider: --provider ollama|openai|openrouter|gemini|lmstudio)") from e
            kw: dict = {"timeout": self.timeout, "max_retries": self.max_retries}
            key = os.environ.get(self.api_key_env) if self.api_key_env else None
            if key:
                kw["api_key"] = key  # otherwise the SDK resolves ANTHROPIC_AUTH_TOKEN / `ant auth login` profiles
            if self.base_url:
                kw["base_url"] = self.base_url
            self._client = anthropic.Anthropic(**kw)
        return self._client

    def complete(self, system, messages, *, json_schema=None, images=None, max_tokens=16000) -> str:
        req = self.build_request(system, messages, json_schema=json_schema, images=images, max_tokens=max_tokens)
        msg = self._send(req)
        if msg.stop_reason == "max_tokens" and req["max_tokens"] < MAX_OUTPUT:
            req["max_tokens"] = min(MAX_OUTPUT, req["max_tokens"] * 2)  # thinking shares the budget: give it room
            msg = self._send(req)
        return self._text(msg, req)

    def _send(self, req: dict):
        client = self._get_client()
        r = dict(req)
        try:
            if "betas" in r:  # server-side fallbacks live on the beta endpoint
                with client.beta.messages.stream(**r) as stream:
                    return stream.get_final_message()
            with client.messages.stream(**r) as stream:
                return stream.get_final_message()
        except ProviderError:
            raise
        except Exception as e:  # noqa: BLE001 - mapped by the SDK's typed exception classes, most specific first
            raise _map_anthropic_error(e, self) from e

    @staticmethod
    def _text(msg, req) -> str:
        if msg.stop_reason == "refusal":
            det = getattr(msg, "stop_details", None)
            cat = getattr(det, "category", None) if det else None
            expl = getattr(det, "explanation", None) if det else None
            raise RefusalError(f"the model declined this request (category: {cat or 'unspecified'})"
                               f"{': ' + expl if expl else ''}. Rephrase the topic or run this stage with another model.",
                               category=cat)
        if msg.stop_reason == "max_tokens":
            raise TruncatedError(f"reply truncated at max_tokens={req['max_tokens']}: raise the stage's max_tokens "
                                 "or lower effort")
        # thinking and fallback blocks are skipped; with structured outputs the first text block is the JSON
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

    def check(self, network: bool = True) -> dict:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return {"ok": False, "detail": "SDK missing: pip install anthropic"}
        has_cred = any(os.environ.get(k) for k in (self.api_key_env, "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE") if k)
        has_cred = has_cred or (Path.home() / ".config" / "anthropic").exists()
        if not has_cred:
            return {"ok": False, "detail": f"no credentials: set {self.api_key_env} or run `ant auth login`"}
        if not network:
            return {"ok": True, "detail": "SDK and credentials present (not contacted)"}
        try:  # the Models API costs no tokens
            m = self._get_client().with_options(timeout=15.0, max_retries=0).models.retrieve(self.model)
            return {"ok": True, "detail": f"reachable; model {getattr(m, 'id', self.model)} available"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "detail": f"{type(e).__name__}: {str(e)[:160]}"}


def _map_anthropic_error(e: Exception, p: AnthropicProvider) -> Exception:
    try:
        import anthropic as A
    except ImportError:
        return e
    if isinstance(e, A.AuthenticationError):
        return ProviderError(f"Anthropic rejected the credentials (set {p.api_key_env} or run `ant auth login`)")
    if isinstance(e, A.NotFoundError):
        return ProviderError(f"model {p.model!r} not found for this key")
    if isinstance(e, A.BadRequestError):
        return ProviderError(f"Anthropic bad request: {getattr(e, 'message', e)}")
    if isinstance(e, A.RateLimitError):  # the SDK already retried max_retries times
        return ProviderError("Anthropic rate limit: retry later")
    if isinstance(e, A.APIStatusError):
        return ProviderError(f"Anthropic API error {e.status_code}: {getattr(e, 'message', e)}")
    if isinstance(e, A.APIConnectionError):
        return ProviderError(f"cannot reach the Anthropic API: {e}")
    return e


# ---------------------------------------------------------------------------------------------------------- OpenAI-compatible

PRESETS = {
    # name: (base_url, api key env var or "", supports images by default)
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", True),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", True),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", True),
    "ollama": ("http://localhost:11434/v1", "", False),
    "lmstudio": ("http://localhost:1234/v1", "", False),
    "vllm": ("http://localhost:8000/v1", "", False),
    "llamacpp": ("http://localhost:8080/v1", "", False),
}
JSON_MODES = ("schema", "schema_strict", "object", "none")
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


@dataclass
class OpenAICompatProvider(Provider):
    """POST {base_url}/chat/completions with the stdlib. `json_mode`: "schema" sends response_format json_schema
    (strict false: best effort, works on most servers), "schema_strict" (OpenAI strict mode), "object" sends
    {"type": "json_object"}, "none" relies on the prompt. Always validated by the caller anyway."""

    name: str = "openai"
    model: str = ""
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = ""
    json_mode: str = "schema"
    supports_images: bool = False
    timeout: float = 900.0             # local models on CPU are slow; a lesson.json can take minutes
    retries: int = 4
    max_tokens_field: str = "max_tokens"  # some OpenAI reasoning models want "max_completion_tokens"
    temperature: float | None = None   # sent only when set (Claude-side we never send it)
    extra_headers: dict = field(default_factory=dict)
    extra_body: dict = field(default_factory=dict)
    _opener: Callable | None = field(default=None, repr=False)  # injectable for tests (urllib.request.urlopen)
    _sleep: Callable = field(default=time.sleep, repr=False)

    def __post_init__(self):
        if self.json_mode not in JSON_MODES:
            raise ProviderError(f"json_mode must be one of {JSON_MODES}")
        if not self.model:
            raise ProviderError(f"provider {self.name!r} needs a model (--model or `model =` in agent.toml)")
        self.base_url = self.base_url.rstrip("/")

    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "vfactory-agent/0.1"}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if key:
                h["Authorization"] = f"Bearer {key}"
        h.update(self.extra_headers)
        return h

    def build_request(self, system: str, messages: list[dict], *, json_schema: dict | None = None, images=None,
                      max_tokens: int = 16000) -> dict:
        msgs: list[dict] = [{"role": "system", "content": system}]
        for i, m in enumerate(messages):
            if images and self.supports_images and i == len(messages) - 1 and m["role"] == "user":
                parts: list[dict] = [{"type": "text", "text": m["content"]}]
                for img in images:
                    media, data = load_image(img)
                    parts.append({"type": "image_url", "image_url": {"url": f"data:{media};base64,{data}"}})
                msgs.append({"role": "user", "content": parts})
            else:
                msgs.append({"role": m["role"], "content": m["content"]})
        body: dict = {"model": self.model, "messages": msgs, self.max_tokens_field: int(max_tokens)}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if json_schema is not None and self.json_mode != "none":
            if self.json_mode == "object":
                body["response_format"] = {"type": "json_object"}
            else:
                strict = strict_subset(json_schema)
                if strict is None:
                    body["response_format"] = {"type": "json_object"}  # open schema: ask for JSON, validate after
                else:
                    if self.json_mode == "schema_strict":
                        strict = all_required(strict)
                    body["response_format"] = {"type": "json_schema", "json_schema": {
                        "name": "stage_output", "schema": strict, "strict": self.json_mode == "schema_strict"}}
        body.update(self.extra_body)
        return body

    def _post(self, url: str, body: dict | None, method: str = "POST", timeout: float | None = None) -> dict:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        opener = self._opener or urllib.request.urlopen
        last = None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(url, data=data, method=method, headers=self.headers())
            try:
                with opener(req, timeout=timeout or self.timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = _err_body(e)
                if e.code in RETRY_STATUS and attempt < self.retries:
                    last = ProviderError(f"{self.name}: HTTP {e.code} {detail}")
                    self._sleep(_retry_after(e, attempt))
                    continue
                if e.code in (401, 403):
                    raise ProviderError(f"{self.name}: HTTP {e.code} (check {self.api_key_env or 'the API key'}): {detail}") from e
                raise ProviderError(f"{self.name}: HTTP {e.code}: {detail}") from e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = ProviderError(f"{self.name}: cannot reach {url}: {getattr(e, 'reason', e)}")
                if attempt < self.retries:
                    self._sleep(min(30.0, 2 ** attempt + random.random()))
                    continue
        raise last or ProviderError(f"{self.name}: request failed")

    def complete(self, system, messages, *, json_schema=None, images=None, max_tokens=16000) -> str:
        body = self.build_request(system, messages, json_schema=json_schema, images=images, max_tokens=max_tokens)
        resp = self._post(f"{self.base_url}/chat/completions", body)
        choice, text = _choice(resp, self.name)
        if choice.get("finish_reason") == "length":
            body[self.max_tokens_field] = int(body[self.max_tokens_field]) * 2
            resp = self._post(f"{self.base_url}/chat/completions", body)
            choice, text = _choice(resp, self.name)
            if choice.get("finish_reason") == "length":
                raise TruncatedError(f"{self.name}: reply truncated at {body[self.max_tokens_field]} tokens "
                                     "(raise max_tokens or the server's context size, e.g. Ollama num_ctx)")
        if choice.get("finish_reason") == "content_filter" or (not text and (choice.get("message") or {}).get("refusal")):
            raise RefusalError(f"{self.name}: the model declined: {(choice.get('message') or {}).get('refusal') or 'content filter'}")
        return text

    def check(self, network: bool = True) -> dict:
        if self.api_key_env and not os.environ.get(self.api_key_env):
            return {"ok": False, "detail": f"{self.api_key_env} is not set"}
        if not network:
            return {"ok": True, "detail": "configured (not contacted)"}
        try:  # listing models costs no tokens
            r = self._post(f"{self.base_url}/models", None, method="GET", timeout=10)
            ids = [m.get("id") for m in r.get("data", []) if isinstance(m, dict)]
            if ids and self.model not in ids and not any(i and i.endswith("/" + self.model) for i in ids):
                return {"ok": True, "detail": f"reachable, but model {self.model!r} not listed ({len(ids)} models)"}
            return {"ok": True, "detail": f"reachable ({len(ids)} models listed)"}
        except ProviderError as e:
            return {"ok": False, "detail": str(e)[:200]}


def _choice(resp: dict, name: str) -> tuple[dict, str]:
    if "error" in resp and not resp.get("choices"):
        raise ProviderError(f"{name}: {resp['error']}")
    try:
        choice = resp["choices"][0]
    except (KeyError, IndexError, TypeError) as e:
        raise ProviderError(f"{name}: unexpected response shape: {str(resp)[:200]}") from e
    content = (choice.get("message") or {}).get("content") or ""
    if isinstance(content, list):  # some servers return content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return choice, content


def _err_body(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8", "replace")[:300]
    except Exception:  # noqa: BLE001
        return ""


def _retry_after(e: urllib.error.HTTPError, attempt: int) -> float:
    ra = e.headers.get("Retry-After") if e.headers else None
    if ra and re.fullmatch(r"\d+(\.\d+)?", ra.strip()):
        return min(120.0, float(ra))
    return min(60.0, 2 ** attempt + random.random())


# ---------------------------------------------------------------------------------------------------------- fake

@dataclass
class FakeProvider(Provider):
    """Scripted replies. `script` is either a list (replies in call order) or a dict {stage: [replies]} keyed by the
    `[stage:NAME]` marker the pipeline puts at the top of every stage prompt. A reply is a string, a dict/list (sent as
    JSON), or a callable(system, messages, **kw) -> str|dict. Every call is recorded in `calls`."""

    name: str = "fake"
    model: str = "fake-1"
    script: object = None
    supports_images: bool = True
    calls: list = field(default_factory=list)

    def complete(self, system, messages, *, json_schema=None, images=None, max_tokens=16000) -> str:
        stage = stage_of(messages)
        self.calls.append({"stage": stage, "system": system, "messages": [dict(m) for m in messages],
                           "json_schema": json_schema, "images": list(images or []), "max_tokens": max_tokens})
        if isinstance(self.script, dict):
            queue = self.script.get(stage)
            if queue is None:
                raise ProviderError(f"FakeProvider has no reply scripted for stage {stage!r}")
        else:
            queue = self.script
        if not queue:
            raise ProviderError(f"FakeProvider ran out of replies (stage {stage!r})")
        reply = queue.pop(0) if len(queue) > 1 or not isinstance(self.script, dict) else queue[0]
        if callable(reply):
            reply = reply(system, messages, json_schema=json_schema, images=images)
        return reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)

    def check(self, network: bool = True) -> dict:
        return {"ok": True, "detail": "scripted"}


def stage_of(messages: list[dict]) -> str | None:
    for m in messages:
        hit = re.search(r"\[stage:([a-z_]+)\]", m.get("content", "") if isinstance(m.get("content"), str) else "")
        if hit:
            return hit.group(1)
    return None
