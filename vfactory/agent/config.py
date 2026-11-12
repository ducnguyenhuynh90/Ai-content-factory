"""agent.toml + CLI flags -> one provider per stage.

Search order: --config PATH, $VFACTORY_AGENT_CONFIG, ./agent.toml, ~/.config/vfactory/agent.toml. Missing file = defaults
(Claude via the anthropic SDK for every stage).

    [defaults]
    provider = "claude"          # a [providers.NAME] entry, a preset (ollama, lmstudio, openrouter, gemini, openai,
                                 # vllm, llamacpp), "anthropic" or "fake"
    runs_dir = "runs"
    fix_rounds = 3
    repair_tries = 3
    critique_rounds = 1
    lint_mode = "auto"           # auto | strict | shadow (see pipeline.lint_lesson)
    vision_review = true
    build = true
    profile = "full"             # full | compact (smaller prompts for small local models)

    [providers.claude]
    type = "anthropic"
    model = "claude-opus-5-5"
    effort = "high"

    [providers.local]
    type = "openai"
    preset = "ollama"
    model = "qwen3:32b"
    profile = "compact"

    [stages]
    idea = "local"
    critique = { provider = "claude", effort = "xhigh" }

CLI flags --provider/--model/--base-url/--api-key-env/--effort override the providers for every stage; --stage
NAME=PROVIDER overrides one stage. Keys are never stored here: only the NAME of the environment variable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .providers import (ANTHROPIC_DEFAULT_MODEL, PRESETS, AnthropicProvider, FakeProvider, OpenAICompatProvider,
                        Provider, ProviderError)

STAGES = ("idea", "research", "spine", "beats", "lesson", "critique", "build", "gate", "fix", "package")
MODEL_STAGES = ("idea", "research", "spine", "beats", "lesson", "critique", "gate", "fix", "package")

DEFAULTS = {
    "provider": "anthropic",
    "runs_dir": "runs",
    "fix_rounds": 3,
    "repair_tries": 3,
    "critique_rounds": 1,
    "lint_mode": "auto",
    "vision_review": True,
    "build": True,
    "profile": "full",
    "max_images": 4,
    "end_narration": "Còn bạn, bạn muốn tập sau về khung tư duy nào? Để lại bình luận cho mình nhé. Hẹn gặp bạn ở tập sau.",
}

# output budgets per stage (thinking shares max_tokens on Claude; streaming makes large values safe)
MAX_TOKENS = {"idea": 16000, "research": 32000, "spine": 16000, "beats": 32000, "lesson": 64000, "critique": 32000,
              "gate": 16000, "fix": 32000, "package": 16000}


@dataclass
class Config:
    defaults: dict = field(default_factory=lambda: dict(DEFAULTS))
    providers: dict = field(default_factory=dict)   # name -> dict
    stages: dict = field(default_factory=dict)      # stage -> name | dict
    source: str | None = None
    cli: dict = field(default_factory=dict)         # provider/model/base_url/api_key_env/effort/stage overrides

    def get(self, key, default=None):
        return self.defaults.get(key, DEFAULTS.get(key, default))

    # ---- per-stage provider spec
    def stage_spec(self, stage: str) -> dict:
        """The merged provider settings for a stage (no secrets)."""
        cli = self.cli
        override = (cli.get("stage") or {}).get(stage)
        if override:
            ref = override
            extra: dict = {}
        elif cli.get("provider") or cli.get("model") or cli.get("base_url"):
            ref, extra = cli.get("provider") or self.get("provider"), {}
        else:
            s = self.stages.get(stage)
            if isinstance(s, dict):
                ref, extra = s.get("provider", self.get("provider")), {k: v for k, v in s.items() if k != "provider"}
            else:
                ref, extra = s or self.get("provider"), {}
        spec = self._resolve(ref)
        spec.update(extra)
        for k in ("model", "base_url", "api_key_env", "effort"):
            if cli.get(k):
                spec[k] = cli[k]
        if spec.get("type") == "anthropic":
            spec.setdefault("model", ANTHROPIC_DEFAULT_MODEL)
            spec.setdefault("effort", "high")  # Opus 5.5 defaults to medium server-side; writing wants high
        spec.setdefault("profile", self.get("profile"))
        spec["max_tokens"] = int(spec.get("max_tokens") or MAX_TOKENS.get(stage, 16000))
        return spec

    def _resolve(self, ref: str) -> dict:
        if ref in self.providers:
            spec = dict(self.providers[ref])
            spec.setdefault("label", ref)
        elif ref in PRESETS:
            spec = {"type": "openai", "preset": ref, "label": ref}
        elif ref in ("anthropic", "claude"):
            spec = {"type": "anthropic", "label": "anthropic"}
        elif ref == "fake":
            spec = {"type": "fake", "label": "fake"}
        elif ref == "openai-compat":
            spec = {"type": "openai", "label": ref}
        else:
            raise ProviderError(f"unknown provider {ref!r}: define [providers.{ref}] in agent.toml or use one of "
                                f"anthropic, fake, {', '.join(PRESETS)}")
        if spec.get("type") == "openai" and spec.get("preset"):
            base, env, img = PRESETS[spec["preset"]]
            spec.setdefault("base_url", base)
            spec.setdefault("api_key_env", env)
            spec.setdefault("supports_images", img)
        return spec


def load(path: str | Path | None = None, cli: dict | None = None) -> Config:
    cands = [path, os.environ.get("VFACTORY_AGENT_CONFIG"), "agent.toml",
             Path.home() / ".config" / "vfactory" / "agent.toml"]
    cfg = Config(cli=dict(cli or {}))
    for c in cands:
        if c and Path(c).is_file():
            try:
                import tomllib  # Python 3.11+
            except ImportError:  # Python 3.10
                try:
                    import tomli as tomllib  # type: ignore
                except ImportError as e:
                    raise ProviderError("reading agent.toml on Python 3.10 needs `pip install tomli` "
                                        "(or use CLI flags only)") from e
            data = tomllib.loads(Path(c).read_text())
            cfg.defaults.update(data.get("defaults", {}))
            cfg.providers = data.get("providers", {})
            cfg.stages = data.get("stages", {})
            cfg.source = str(c)
            break
        if c is path and path:
            raise ProviderError(f"config file not found: {path}")
    return cfg


def make_provider(spec: dict, fake_script=None) -> Provider:
    t = spec.get("type", "anthropic")
    if t == "anthropic":
        return AnthropicProvider(model=spec.get("model") or ANTHROPIC_DEFAULT_MODEL, effort=spec.get("effort", "high"),
                                 fallbacks=bool(spec.get("fallbacks", True)),
                                 api_key_env=spec.get("api_key_env", "ANTHROPIC_API_KEY"),
                                 base_url=spec.get("base_url"), timeout=float(spec.get("timeout", 900)),
                                 structured=bool(spec.get("structured", True)), name=spec.get("label", "anthropic"))
    if t == "openai":
        if not spec.get("base_url"):
            raise ProviderError("an OpenAI-compatible provider needs base_url (or a preset)")
        return OpenAICompatProvider(name=spec.get("label", "openai"), model=spec.get("model", ""),
                                    base_url=spec["base_url"], api_key_env=spec.get("api_key_env", ""),
                                    json_mode=spec.get("json_mode", "schema"),
                                    supports_images=bool(spec.get("supports_images", False)),
                                    timeout=float(spec.get("timeout", 900)), retries=int(spec.get("retries", 4)),
                                    max_tokens_field=spec.get("max_tokens_field", "max_tokens"),
                                    temperature=spec.get("temperature"), extra_headers=dict(spec.get("headers", {})),
                                    extra_body=dict(spec.get("extra_body", {})))
    if t == "fake":
        if fake_script is None:
            from .fake_demo import demo_script

            fake_script = demo_script()
        return FakeProvider(script=fake_script)
    raise ProviderError(f"unknown provider type {t!r} (anthropic | openai | fake)")


def public_spec(spec: dict) -> dict:
    """What we record in run.json: settings, never key values."""
    return {k: v for k, v in spec.items() if k not in ("headers",)}
