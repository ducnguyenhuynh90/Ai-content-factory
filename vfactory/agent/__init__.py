"""vfactory.agent: a local, model-agnostic writers' room that researches, writes, builds, gates and packages
story-driven sticker explainer videos (see docs/agent.md and docs/plans/story-sticker-agent.md).

    python -m vfactory.agent run "Tư duy từ gốc" --story-hint "Linh, kế toán Q.7"
"""

from .pipeline import Pipeline, StageError  # noqa: F401
from .providers import AnthropicProvider, FakeProvider, OpenAICompatProvider, Provider, ProviderError  # noqa: F401
