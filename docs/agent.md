# The episode agent (`python -m vfactory.agent`)

A local, model-agnostic writers' room for the story-driven sticker explainers described in
`docs/plans/story-sticker-agent.md`. It researches a topic, writes the Pixar story spine and the beat sheet, emits a
`lesson.json` in the sticker format, critiques it, builds and gates the video with the existing engine CLIs, fixes
what the gate finds, and writes the YouTube packaging. Every stage is a prompt file plus a JSON contract, and every
result is a file in the run directory. You can stop a run, edit a file and resume it.

```
idea → research → spine → beats → lesson → critique → build → gate → fix → package
```

## Install

The core is the project's own dependencies (stdlib, numpy, Pillow). Provider SDKs are optional:

```bash
pip install -e .                 # vfactory itself
pip install anthropic            # only for the Claude provider (or: pip install -e ".[agent]")
```

OpenAI-compatible providers (OpenAI, OpenRouter, Gemini, Ollama, LM Studio, vLLM, llama.cpp) use the stdlib HTTP
client and need nothing extra. Python 3.10 needs `pip install tomli` to read `agent.toml`. Python 3.11+ reads it with
the stdlib.

## Run it

```bash
# Claude (default): reads ANTHROPIC_API_KEY, or a profile from `ant auth login`
python -m vfactory.agent run "Tư duy từ gốc" --story-hint "Linh, 27, kế toán Q.7, muốn mở quán cà phê"

# a dry run with scripted replies: no model, no network, no render
python -m vfactory.agent run "Tư duy từ gốc" --provider fake --runs-dir /tmp/agent-runs

# continue where it stopped, or rerun from a stage (that stage and everything after it)
python -m vfactory.agent resume runs/tu-duy-tu-goc
python -m vfactory.agent resume runs/tu-duy-tu-goc --from lesson --until critique
python -m vfactory.agent status runs/tu-duy-tu-goc

# which providers are configured, and do they answer? (lists models; spends no tokens)
python -m vfactory.agent providers
```

Flags for `run` and `resume`: `--provider NAME`, `--model M`, `--base-url URL`, `--api-key-env VAR`,
`--effort low|medium|high|xhigh|max`, `--stage STAGE=PROVIDER` (repeatable), `--config FILE`, `--runs-dir DIR`,
`--from STAGE`, `--until STAGE`, `--no-build` (text only, which skips build, gate and fix), `--no-vision`,
`--fix-rounds N`, `--lint-mode auto|strict|shadow`. CLI flags override `agent.toml` for every stage, and
`--stage` overrides a single stage.

Keep real runs outside the repo (`--runs-dir ~/Videos/agent-runs`, or `runs_dir` in `agent.toml`). `runs/` is
git-ignored for quick experiments.

### Providers

| Provider | How |
|---|---|
| Claude | `--provider anthropic` (default). Model `claude-opus-5-5`, effort `high` (Opus 5.5's own default is `medium`, so the agent always sends effort). |
| Ollama | `ollama serve`, `ollama pull qwen3:32b`, then `--provider ollama --model qwen3:32b` (`http://localhost:11434/v1`, no key) |
| LM Studio | start the local server, then `--provider lmstudio --model <loaded model id>` (`http://localhost:1234/v1`) |
| OpenRouter | `export OPENROUTER_API_KEY=…`, then `--provider openrouter --model anthropic/claude-opus-5-5` (or any listed model) |
| Gemini | `export GEMINI_API_KEY=…`, then `--provider gemini --model <gemini model>` (Google's OpenAI-compatible endpoint) |
| OpenAI | `export OPENAI_API_KEY=…`, then `--provider openai --model <model>` (some reasoning models need `max_tokens_field = "max_completion_tokens"`) |
| vLLM / llama.cpp | `--provider vllm` (`:8000/v1`) or `--provider llamacpp` (`:8080/v1`) with `--model` |
| Any other compatible server | `--provider openai-compat --base-url http://host:port/v1 --model M [--api-key-env VAR]` |

Keys are only ever read from environment variables. `agent.toml` names the variable (`api_key_env`), and run files
never contain a key.

**Claude details.** The agent uses the official SDK. It streams every request with `.get_final_message()`, uses
`thinking={"type": "adaptive"}` and `output_config={"effort": …}`, and sends no temperature, top_p or assistant
prefill. The shared system prompt is cached (`cache_control` on the system block; repair turns also cache the large
first user turn). Server-side refusal fallbacks are on by default (`betas=["server-side-fallback-2026-07-01"]`,
`fallbacks="default"`); set `fallbacks = false` on the provider to turn them off. If the whole chain still declines,
the stage stops with a clear error that names the refusal category. A reply cut off at `max_tokens` is retried once
with double the budget (up to 128K), and the stage fails if it is cut off again. Structured outputs
(`output_config.format = {"type": "json_schema", "schema": …}`) are used when a stage schema is closed. The lesson
stage's schema is open, because visuals carry many optional fields, so that stage uses prompt-instructed JSON with
validation. The request shape was checked offline against `anthropic` 2.8.0 with a mock HTTP transport.

**OpenAI-compatible details.** `json_mode = "schema"` (default) sends `response_format: json_schema` with
`strict: false`. `"schema_strict"` is OpenAI strict mode, `"object"` sends `json_object` (use it for servers that
reject schemas), and `"none"` relies on the prompt. Images are sent as data URLs when `supports_images = true`
(presets set it for OpenAI, OpenRouter and Gemini). Requests retry on 429/5xx/timeouts with backoff and respect
`Retry-After`. `timeout` defaults to 900 s, so raise it for big models on CPU. `<think>` blocks from reasoning models
are stripped before the JSON is parsed.

### Per-stage models (`agent.toml`)

Copy `vfactory/agent/agent.example.toml` to `./agent.toml`. A typical split: a local model drafts the cheap stages
(idea, spine, beats, package), and a strong model researches, writes the lesson, critiques, reviews frames (it
needs vision) and fixes:

```toml
[defaults]
provider = "claude"

[providers.claude]
type = "anthropic"
effort = "high"

[providers.local]
type = "openai"
preset = "ollama"
model = "qwen3:32b"
profile = "compact"      # smaller system prompt and slimmer inputs for small models

[stages]
idea = "local"
beats = "local"
critique = { provider = "claude", effort = "xhigh" }
```

Weaker models get help in three ways. They get the compact profile. They get strict JSON, with a schema when the
server takes one and a stdlib validator either way. And they get repair loops: each validation, rule or lint error
is sent back verbatim, at most `repair_tries` times, before the stage stops.

## What each stage does and writes

| Stage | Output | Checked by |
|---|---|---|
| idea | `idea.json`: 3 storylines (fictional protagonist with want/flaw + a real story), the chosen one, the metaphor (shows/omits), the misconception | schema |
| research | `research.json` + `research.md`: claims with sources, certainty (established/attributed/disputed/estimate), `verified`, `use` (voice/screen/hedge/cut), `say`; myths; open items | schema + rules: every claim cites a listed source; `verified` only when your notes back it; disputed claims are never voiced as fact; attributed/estimate claims hedge out loud; spoken numbers in words |
| spine | `spine.json`: the six Pixar acts in order, want/flaw/stakes, 3 moves, worked example, metaphor limit, Pixar checks | schema + known claim ids + 240–330 s |
| beats | `beats.json`: 18–30 beats with spine act, teaching act, thread (fiction/real/card), narration draft, visual idea, claim ids; the cast | schema + hook first, end card last, fiction labelled, misconception/question/recap present, no cut claims |
| lesson | `lesson.json` (+ `script.md`, `lesson_check.json`): `meta.style: "sticker"`, `meta.cast`, `stage` beats, `spine` on every beat | schema + series rules (`rules.py`) + `python -m vfactory.lesson lint` |
| critique | `critique.json`; edits `lesson.json` with patch ops (old copy in `history/`) | ops must apply and leave rules + lint clean |
| build | `build/` via `python -m vfactory.lesson build lesson.json --out build --final` | exit code; refuses while the engine lacks `stage` |
| gate | `gate.json` via `python -m vfactory.lesson gate …`: `gate/report.json`, `qa.json`, and an LLM review of the contact sheets (vision models) or of the report (text-only) | the report's hard fails always block |
| fix | `fix.json`: up to `fix_rounds` rounds of patch ops → lint → rebuild → gate; `needs_human` | stops the run (no packaging) if the gate never passes |
| package | `package.json` + `package.md`: title ≤ 65 chars, thumbnail text, description with sources and the fiction label, chapters, 12–15 tags, pinned comment; merged into `meta.youtube` | rules |

The series rules are enforced in code (`vfactory/agent/rules.py`). The writers' briefs learned them the hard way:

- Numbers in narration are spoken Vietnamese, never digits, and long numbers are rounded in speech.
- No previews, greetings or filler.
- One CTA only: the end card's `ask`, with no `cta` field and no "đăng ký/chia sẻ" anywhere else.
- The fictional thread is labelled once ("hư cấu").
- Real people get a name tag and never a likeness.
- On-screen text uses only glyphs the fonts draw.
- Every `cue` is a word in its own beat's narration.
- The spine runs in order after an optional cold open.
- Lesson sources must come from the research pack, so the model cannot invent a source in the writing stage.

Patch ops are JSON-pointer edits. A segment `@ID` selects a beat by id (`/beats/@b07/visual/caption`), and
`value_json` carries the value as a string for strict structured outputs.

### Lint while the sticker engine is still landing

`lint_mode = "auto"` (default) checks whether `vfactory.lesson.schema.VISUALS` knows `stage`:

- **If it does,** lint runs on the lesson as written.
- **If it does not** (or a strict run dies with "visual.type must be one of …" on a lesson with `stage` beats),
  lint runs on a **shadow copy**. In that copy every `stage` beat becomes an `icon` beat with the same narration,
  sources, certainty and on-screen words. Lint's other checks (hook length, digits, sources, hedging, length,
  storyboard) still run, and the stage contract itself is checked by `rules.py`.

The lint output is parsed from its `ERROR`/`warn`/`story` lines. A traceback (lint dies before printing, because
`schema.load` raises) is reduced to its last line and fed back as an error. `lesson_check.json` records the mode and
whether there was an engine gap. The build stage refuses to run until the engine knows `stage`. Resume it later with
`resume <run> --from build`.

## How human review fits in

The agent writes files you can read and edit at every step. A practical rhythm:

1. **Give it material.** Drop `notes.md`, a `notes/` folder or `urls.txt` into the run directory before `run`
   (or before `resume --from research`). Only claims backed by your notes can be marked `verified`. Everything else
   the model proposes is unverified, and it has to be hedged or listed as an open item. The agent cannot browse.
2. **Check the facts.** Stop after research with `run … --until research`. Read `research.md`, tick its open items
   in a browser, and edit `research.json` (fix values, set `use` to `cut` or `hedge`). Then run
   `resume <run> --from spine`.
3. **Approve the script.** Stop after critique with `--until critique` (or `--no-build`). Read `script.md` (lint's
   approval view) and `lesson.json`, edit freely, then run `resume <run> --from build`. To re-check an edited lesson
   first, use `--from critique`.
4. **Gate.** The agent's gate is a first pass. Per CLAUDE.md no video is delivered before it passes the
   `video-gatekeeper` (`python -m vfactory.lesson gate <lesson.json> --out <run>/build`, then the gatekeeper
   review). If the agent's fix rounds do not reach `pass`, the run stops before packaging, and `fix.json` lists what
   needs a human (`needs_human`), for example listening at a timestamp or checking a quote.
5. **Package.** `package.md` is ready to paste into YouTube Studio. Chapter times come from the build.

Every model call is saved in `transcripts/` (the prompt, the reply and the errors fed back) and summarised in
`log.jsonl`, so you can see exactly why a stage needed three tries.

## Cost and time

These are rough figures for one 4–6 minute episode on Claude Opus 5.5 ($4 / $20 per million input / output tokens).
Measure your own runs with `log.jsonl` and the API's usage reports.

- Model text: about 200–300K input tokens (the research pack and the lesson are resent to later stages, and repair
  turns resend the prompt) and 60–100K output tokens including adaptive thinking at effort `high`. That comes to
  roughly **$2–4 per episode** before caching. The cached system prompt and cached first turns of repair calls cut
  the input share. Each extra fix round adds about 40K input and 5K output tokens. `xhigh` on critique costs more
  and is worth measuring.
- A local model costs nothing per token, but a 30B-class model on a laptop GPU can take 5–20 minutes for the lesson
  stage alone. Small models need the compact profile and usually more repair tries.
- Build time dominates. `build --final` voices every line with local TTS (minutes per line on CPU; cached lines are
  reused) and renders the video, so plan on tens of minutes per build. Each fix round that changes narration
  re-voices those lines, and fix rounds that only change visuals are much cheaper.
- `providers` and `--provider fake` dry runs cost nothing.

## Files

- `vfactory/agent/providers.py`: `Provider`, `AnthropicProvider`, `OpenAICompatProvider`, `FakeProvider`
- `vfactory/agent/config.py`: `agent.toml` + CLI flags → a provider per stage
- `vfactory/agent/pipeline.py`: stages, run directory, repair loop, lint/build/gate integration
- `vfactory/agent/rules.py`: deterministic series rules and the `stage` contract
- `vfactory/agent/schemas.py`, `jsonutil.py`, `patch.py`: stage schemas, the validator and JSON extraction, patch ops
- `vfactory/agent/prompts/*.md`: the system prompt (full and compact) and one prompt per stage
- `vfactory/agent/fake_demo.py`: the dry-run script (a short demo episode)
- `tests/test_agent.py`: the tests (no network, no model, no render)
