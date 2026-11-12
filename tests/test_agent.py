"""vfactory.agent: providers (request construction, offline), JSON validation + repair, stage chaining, resume, lint
feedback (mocked subprocess), build/gate/fix loop (mocked), rules and config. No network, no model, no render."""

from __future__ import annotations

import copy
import io
import json
import subprocess
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from vfactory.agent import config as C
from vfactory.agent import fake_demo, pipeline, rules, schemas
from vfactory.agent.jsonutil import JSONExtractError, all_required, extract_json, strict_subset, validate
from vfactory.agent.patch import PatchError, apply_ops
from vfactory.agent.pipeline import Pipeline, StageError, parse_lint, shadow_lesson
from vfactory.agent.providers import (AnthropicProvider, FakeProvider, OpenAICompatProvider, ProviderError,
                                      RefusalError, TruncatedError, stage_of)

MODEL_STAGES = C.MODEL_STAGES


# ------------------------------------------------------------------------------------------------ helpers

class Runner:
    """Stands in for subprocess.run: scripted results per command (lint/build/gate), records every call."""

    def __init__(self, lint=None, build=None, gate=None):
        self.calls = []
        self.lint = list(lint or [])
        self.build = list(build or [])
        self.gate = list(gate or [])

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        kind = cmd[3]
        queue = {"lint": self.lint, "build": self.build, "gate": self.gate}[kind]
        r = queue.pop(0) if len(queue) > 1 else (queue[0] if queue else (0, "{}", ""))
        if callable(r):
            r = r(cmd)
        rc, out, err = r
        return subprocess.CompletedProcess(cmd, rc, out, err)

    def count(self, kind):
        return sum(1 for c in self.calls if c[3] == kind)


CLEAN_LINT = (0, '{\n "beats": 18,\n "est_minutes": 4.1\n}\napproval view: x/script.md\n', "")


def cfg(**defaults) -> C.Config:
    c = C.Config()
    c.defaults.update({"build": False, "lint_mode": "shadow"})
    c.defaults.update(defaults)
    return c


def make(tmp_path, script=None, runner=None, **defaults):
    fake = FakeProvider(script=script if script is not None else fake_demo.demo_script())
    p = Pipeline.create("Tư duy từ gốc", cfg(**defaults), runs_dir=tmp_path, providers=fake,
                        runner=runner or Runner(lint=[CLEAN_LINT]), log=lambda *a: None)
    return p, fake


# ------------------------------------------------------------------------------------------------ jsonutil

def test_extract_json_tolerates_fences_think_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('<think>hmm {"no": 0}</think>Here: {"a": "x}"} trailing') == {"a": "x}"}
    assert extract_json('[1, 2]') == [1, 2]
    with pytest.raises(JSONExtractError, match="not closed"):
        extract_json('{"a": [1, 2')
    with pytest.raises(JSONExtractError):
        extract_json("no json here")


def test_validate_reports_paths():
    s = schemas.PACKAGE
    errs = validate({"title": "x" * 70, "thumbnail_text": "t", "description": "d", "chapters": [], "tags": ["a"],
                     "extra": 1}, s)
    joined = "\n".join(errs)
    assert "$.title: 70 characters, max 65" in joined
    assert "$.tags: 1 items, need at least 12" in joined
    assert "unexpected field 'extra'" in joined
    assert validate(fake_demo.IDEA, schemas.IDEA) == []
    assert validate(fake_demo.RESEARCH, schemas.RESEARCH) == []
    assert validate(fake_demo.LESSON, schemas.LESSON) == []


def test_strict_subset_closes_and_strips_or_refuses_open_schemas():
    s = strict_subset(schemas.PACKAGE)
    assert s["additionalProperties"] is False
    assert "maxLength" not in s["properties"]["title"] and "minItems" not in s["properties"]["tags"]
    assert strict_subset(schemas.LESSON) is None  # open objects: no constrained decoding
    a = all_required({"type": "object", "properties": {"x": {"type": "string"}, "y": {"type": "string"}},
                      "required": ["x"], "additionalProperties": False})
    assert a["required"] == ["x", "y"] and a["properties"]["y"]["type"] == ["string", "null"]


# ------------------------------------------------------------------------------------------------ patch ops

def test_patch_ops_by_id_value_json_and_atomic():
    L = copy.deepcopy(fake_demo.LESSON)
    out = apply_ops(L, [{"op": "replace", "path": "/beats/@b05/narration", "value": "mới"},
                        {"op": "add", "path": "/beats/@b14/visual/caption", "value_json": '"Có gì?"'},
                        {"op": "add", "path": "/principles/-", "value_json": '{"name": "n", "line": "l"}'},
                        {"op": "remove", "path": "/beats/@b13"}])
    by = {b["id"]: b for b in out["beats"]}
    assert by["b05"]["narration"] == "mới" and by["b14"]["visual"]["caption"] == "Có gì?"
    assert "b13" not in by and len(out["principles"]) == 4
    assert L == fake_demo.LESSON  # the original is untouched
    with pytest.raises(PatchError, match="no element with id"):
        apply_ops(L, [{"op": "replace", "path": "/beats/@b05/narration", "value": "x"},
                      {"op": "replace", "path": "/beats/@zz/narration", "value": "y"}])


# ------------------------------------------------------------------------------------------------ rules

def test_demo_lesson_passes_series_rules():
    errs, warns = rules.check_lesson(fake_demo.LESSON, research=fake_demo.RESEARCH,
                                     end_narration=fake_demo.END)
    assert errs == [], errs


def test_rules_catch_series_violations():
    L = copy.deepcopy(fake_demo.LESSON)
    by = {b["id"]: b for b in L["beats"]}
    by["b05"]["narration"] = "Giá là 20 triệu đô. Hãy đăng ký kênh nhé."
    by["b02"]["visual"]["bubble"]["cue"] = "không có"
    by["b02"]["visual"]["characters"][0]["id"] = "tung"
    by["h2"]["narration"] = "Đến cuối clip, bạn sẽ biết ba điều."
    L["beats"][-1]["visual"]["cta"] = "Đăng ký"
    L["sources"].append({"id": "invented", "cite": "?"})
    errs, _ = rules.check_lesson(L, research=fake_demo.RESEARCH)
    text = "\n".join(errs)
    for needle in ("digits in narration", "outside the end card", "bubble cue 'không có'", "'tung' is not in meta.cast",
                   "no previews", "label the fictional thread", "no 'cta'", "'invented' is not in the research pack"):
        assert needle in text, needle


def test_rules_spine_order_allows_cold_open_only():
    L = copy.deepcopy(fake_demo.LESSON)
    by = {b["id"]: b for b in L["beats"]}
    by["b08"]["spine"] = "vi_vay"  # after cho_den_khi: out of order
    errs, _ = rules.check_lesson(L)
    assert any("follow the spine in order" in e for e in errs)


def test_package_rules():
    assert rules.check_package(fake_demo.PACKAGE, fake_demo.LESSON) == []
    bad = dict(fake_demo.PACKAGE, title="T" * 66, tags=["a"], description="no sources")
    text = "\n".join(rules.check_package(bad, fake_demo.LESSON))
    assert "at most 65" in text and "12-15" in text and "Nguồn" in text


# ------------------------------------------------------------------------------------------------ stage chaining

def test_stage_chaining_dry_run(tmp_path):
    p, fake = make(tmp_path)
    p.run()
    d = p.dir
    for f in ("idea", "research", "spine", "beats", "lesson", "critique", "build", "gate", "fix", "package"):
        assert (d / f"{f}.json").exists(), f
    st = p.state["stages"]
    assert [st[s]["status"] for s in C.STAGES] == ["done"] * 6 + ["skipped"] * 3 + ["done"]
    # every model stage was called once, routed by its [stage:NAME] marker
    assert [c["stage"] for c in fake.calls] == ["idea", "research", "spine", "beats", "lesson", "critique", "package"]
    # one stable system prompt for every stage (prompt caching); stage inputs travel in the user turn
    assert len({c["system"] for c in fake.calls}) == 1
    assert "Linh" in fake.calls[2]["messages"][0]["content"]  # spine sees the idea
    assert "wired2012" in fake.calls[4]["messages"][0]["content"]  # lesson sees the research pack
    L = json.loads((d / "lesson.json").read_text())
    by = {b["id"]: b for b in L["beats"]}
    assert by["b14"]["visual"]["caption"] == "Trong nồi này có gì?"  # critique op applied
    assert L["meta"]["youtube"]["title"] == fake_demo.PACKAGE["title"]  # package merged
    assert (d / "research.md").read_text().count("| A") >= 3
    assert (d / "history").is_dir() and (d / "package.md").exists()
    assert len(list((d / "transcripts").glob("*.json"))) == 7
    run = json.loads((d / "run.json").read_text())
    assert "KEY" not in json.dumps(run).upper().replace("API_KEY_ENV", "")


def test_notes_are_passed_to_idea_and_research(tmp_path):
    p, fake = make(tmp_path)
    (p.dir / "notes.md").write_text("Ghi chú: Wired 2012 đã mở và kiểm.")
    (p.dir / "notes").mkdir()
    (p.dir / "notes" / "urls.txt").write_text("https://example.org/a")
    p.run(until="research")
    for c in fake.calls:
        assert "Wired 2012 đã mở" in c["messages"][0]["content"]
        assert "https://example.org/a" in c["messages"][0]["content"]


# ------------------------------------------------------------------------------------------------ repair loop

def test_json_validation_and_repair_loop(tmp_path):
    good = copy.deepcopy(fake_demo.IDEA)
    missing = {k: v for k, v in good.items() if k != "metaphor"}
    script = fake_demo.demo_script()
    script["idea"] = ["Sorry, here is the idea: {not json", missing, good]
    p, fake = make(tmp_path, script=script)
    p.run(until="idea")
    calls = [c for c in fake.calls if c["stage"] == "idea"]
    assert len(calls) == 3
    second = calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]  # never an assistant prefill
    assert "not valid JSON" in second[-1]["content"]
    assert "missing required field 'metaphor'" in calls[2]["messages"][-1]["content"]
    assert json.loads((p.dir / "idea.json").read_text())["framework"] == "Tư duy từ gốc"
    assert p.state["stages"]["idea"]["attempts"] == 3


def test_repair_loop_gives_up_after_max_tries(tmp_path):
    script = fake_demo.demo_script()
    bad = copy.deepcopy(fake_demo.RESEARCH)
    bad["claims"][1]["use"] = "voice"  # a disputed claim voiced as fact: a deterministic research check
    script["research"] = [bad]
    p, fake = make(tmp_path, script=script, repair_tries=3)
    with pytest.raises(StageError) as ei:
        p.run(until="research")
    assert "disputed claims are hedged or cut" in str(ei.value)
    assert sum(1 for c in fake.calls if c["stage"] == "research") == 3
    assert p.state["stages"]["research"]["status"] == "failed"


# ------------------------------------------------------------------------------------------------ resume

def test_resume_skips_done_stages_and_from_reruns(tmp_path):
    p, fake = make(tmp_path)
    p.run(until="spine")
    assert [c["stage"] for c in fake.calls] == ["idea", "research", "spine"]
    fake2 = FakeProvider(script=fake_demo.demo_script())
    p2 = Pipeline(p.dir, cfg(), providers=fake2, runner=Runner(lint=[CLEAN_LINT]), log=lambda *a: None)
    p2.run(until="lesson")
    assert [c["stage"] for c in fake2.calls] == ["beats", "lesson"]
    fake3 = FakeProvider(script=fake_demo.demo_script())
    p3 = Pipeline(p.dir, cfg(), providers=fake3, runner=Runner(lint=[CLEAN_LINT]), log=lambda *a: None)
    p3.run(from_stage="spine", until="beats")
    assert [c["stage"] for c in fake3.calls] == ["spine", "beats"]
    assert p3.state["stages"]["lesson"]["status"] == "stale"  # downstream of a rerun


# ------------------------------------------------------------------------------------------------ lint feedback

def test_lint_errors_are_fed_back_to_the_model(tmp_path):
    lint_err = (1, '{\n "beats": 18\n}\nERROR  b05: marked disputed but the narration states it as fact; say so out loud\n'
                   "warn   b03: contains a number or date with no source id\n", "")
    runner = Runner(lint=[lint_err, CLEAN_LINT])
    p, fake = make(tmp_path, runner=runner)
    p.run(until="lesson")
    calls = [c for c in fake.calls if c["stage"] == "lesson"]
    assert len(calls) == 2
    assert "lint: b05: marked disputed" in calls[1]["messages"][-1]["content"]
    assert runner.count("lint") == 2
    # lint ran on the shadow copy: no `stage` visuals reach an engine that does not know them
    shadow = json.loads((p.dir / ".lint" / "lesson.json").read_text())
    assert all(b["visual"]["type"] != "stage" for b in shadow["beats"])
    chk = json.loads((p.dir / "lesson_check.json").read_text())
    assert chk["lint"]["mode"] == "shadow" and chk["lint"]["errors"] == []


def test_lint_crash_on_unknown_stage_type_falls_back_to_shadow(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "engine_knows_stage", lambda: True)  # so auto picks strict first
    crash = (1, "", 'Traceback (most recent call last):\n  ...\nvfactory.lesson.schema.LessonError: beat 0 (h1): '
                    "visual.type must be one of ['hook', 'title']\n")
    runner = Runner(lint=[crash, CLEAN_LINT])
    p, _ = make(tmp_path, runner=runner, lint_mode="auto")
    res = p.lint(fake_demo.LESSON)
    assert res["mode"] == "shadow" and res["errors"] == [] and res["engine_gap"] is True
    assert runner.count("lint") == 2


def test_parse_lint_traceback_and_lines():
    r = parse_lint("", "Traceback...\nvfactory.lesson.schema.LessonError: beat 3 (b03): empty narration\n", 1)
    assert r["errors"] == ["beat 3 (b03): empty narration"] and r["crash"]
    r = parse_lint('{\n "beats": 2\n}\nERROR  x\nwarn   y\nstory  z\n', "", 1)
    assert (r["errors"], r["warnings"], r["story"], r["stats"]) == (["x"], ["y"], ["z"], {"beats": 2})


def test_shadow_lesson_maps_stage_to_icon():
    S = shadow_lesson(fake_demo.LESSON)
    h1 = S["beats"][0]["visual"]
    assert h1["type"] == "icon" and h1["icon"] == "glass" and h1["line"] == "Phần còn lại là gì?"
    assert fake_demo.LESSON["beats"][0]["visual"]["type"] == "stage"


def test_demo_lesson_passes_real_engine_lint(tmp_path):
    """Integration: the fixture is valid for today's engine lint (shadow mode, real subprocess)."""
    p = Pipeline.create("demo", cfg(), runs_dir=tmp_path, providers=FakeProvider(script={}), log=lambda *a: None)
    res = p.lint(fake_demo.LESSON)
    if res.get("crash_kind") == "engine":
        pytest.skip(f"the engine's own lint is broken right now: {res['crash']}")
    assert res["errors"] == [], res


def test_engine_crash_stops_instead_of_burning_repairs(tmp_path):
    crash = (1, "", "Traceback (most recent call last):\nImportError: cannot import name 'ICONS' (circular import)\n")
    runner = Runner(lint=[crash])
    p, fake = make(tmp_path, runner=runner)
    with pytest.raises(StageError, match="engine's lint crashed"):
        p.run(until="lesson")
    assert sum(1 for c in fake.calls if c["stage"] == "lesson") == 1
    assert (p.dir / "lesson.draft.json").exists()


# ------------------------------------------------------------------------------------------------ build / gate / fix

def _gate_writer(verdicts):
    seq = list(verdicts)

    def run(cmd):
        out = Path(cmd[cmd.index("--out") + 1])
        g = out / "gate"
        g.mkdir(parents=True, exist_ok=True)
        from PIL import Image

        for k in ("hook", "scenes"):
            Image.new("RGB", (64, 48), (200, 180, 150)).save(g / f"{k}.jpg")
        v = seq.pop(0) if len(seq) > 1 else seq[0]
        (g / "report.json").write_text(json.dumps({"verdict": v, "fails": [], "warnings": ["[E] still 3s"], "metrics": {},
                                                   "evidence": {k: str(g / f"{k}.jpg") for k in ("hook", "scenes")}}))
        return (0 if v != "block" else 3, json.dumps({"verdict": v}), "")
    return run


def test_build_gate_fix_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "engine_knows_stage", lambda: True)
    script = fake_demo.demo_script()
    script["gate"] = [{"verdict": "revise", "seen": "a cafe set, Linh at left", "issues": [
        {"beat": "b03", "problem": "still picture", "fix": "add an action", "severity": "must"}]},
        {"verdict": "pass", "seen": "fixed", "issues": []}]
    script["fix"] = [{"summary": "add motion", "needs_human": ["listen at 0:42"],
                      "ops": [{"op": "replace", "path": "/beats/@b03/visual/action", "value_json": '"rơi xuống"'}]}]
    runner = Runner(lint=[CLEAN_LINT], build=[(0, '{"video": "x.mp4", "duration": 240.0}', "")],
                    gate=[_gate_writer(["revise", "pass"])])
    p, fake = make(tmp_path, script=script, runner=runner, build=True)
    p.run()
    fix = json.loads((p.dir / "fix.json").read_text())
    assert fix["verdict"] == "pass" and len(fix["rounds"]) == 1 and fix["needs_human"] == ["listen at 0:42"]
    assert runner.count("build") == 2 and runner.count("gate") == 2
    build_cmd = next(c for c in runner.calls if c[3] == "build")
    assert build_cmd[-1] == "--final" and "--out" in build_cmd
    gate_calls = [c for c in fake.calls if c["stage"] == "gate"]
    assert len(gate_calls[0]["images"]) == 2  # frames went to the (vision-capable) reviewer
    L = json.loads((p.dir / "lesson.json").read_text())
    assert {b["id"]: b for b in L["beats"]}["b03"]["visual"]["action"] == "rơi xuống"
    assert json.loads((p.dir / "gate.json").read_text())["verdict"] == "pass"
    assert p.state["stages"]["package"]["status"] == "done"


def test_fix_gives_up_and_blocks_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "engine_knows_stage", lambda: True)
    script = fake_demo.demo_script()
    script["gate"] = [{"verdict": "revise", "seen": "x", "issues": []}]
    script["fix"] = [{"summary": "try", "needs_human": [],
                      "ops": [{"op": "replace", "path": "/beats/@b03/visual/action", "value_json": '"rung"'}]}]
    runner = Runner(lint=[CLEAN_LINT], build=[(0, "{}", "")], gate=[_gate_writer(["revise"])])
    p, _ = make(tmp_path, script=script, runner=runner, build=True, fix_rounds=2)
    with pytest.raises(StageError, match="did not pass after 2 round"):
        p.run()
    assert p.state["stages"]["fix"]["status"] == "failed"
    assert "package" not in p.state["stages"]  # nothing is packaged/delivered before the gate passes


def test_build_refuses_while_engine_lacks_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "engine_knows_stage", lambda: False)
    runner = Runner(lint=[CLEAN_LINT])
    p, _ = make(tmp_path, runner=runner, build=True)
    with pytest.raises(StageError, match="does not know the sticker `stage`"):
        p.run()
    assert runner.count("build") == 0 and (p.dir / "lesson.json").exists()


# ------------------------------------------------------------------------------------------------ providers

SCHEMA = {"type": "object", "properties": {"title": {"type": "string", "maxLength": 65}}, "required": ["title"],
          "additionalProperties": False}


def test_anthropic_request_payload():
    p = AnthropicProvider()
    req = p.build_request("SYSTEM RULES", [{"role": "user", "content": "[stage:idea] hi"}], json_schema=SCHEMA,
                          max_tokens=32000)
    assert req["model"] == "claude-opus-5-5" and req["max_tokens"] == 32000
    assert req["thinking"] == {"type": "adaptive"}
    assert req["output_config"]["effort"] == "high"
    assert req["output_config"]["format"] == {"type": "json_schema", "schema": {
        "type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"], "additionalProperties": False}}
    assert req["system"] == [{"type": "text", "text": "SYSTEM RULES", "cache_control": {"type": "ephemeral"}}]
    assert req["betas"] == ["server-side-fallback-2026-07-01"] and req["fallbacks"] == "default"
    for banned in ("temperature", "top_p", "top_k", "budget_tokens"):
        assert banned not in json.dumps(req)
    assert req["messages"] == [{"role": "user", "content": [{"type": "text", "text": "[stage:idea] hi"}]}]


def test_anthropic_request_variants(tmp_path):
    from PIL import Image

    img = tmp_path / "f.png"
    Image.new("RGB", (40, 30)).save(img)
    p = AnthropicProvider(effort="xhigh", fallbacks=False)
    msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]
    req = p.build_request("S", msgs, json_schema=schemas.LESSON, images=[img])
    assert "betas" not in req and "fallbacks" not in req
    assert "format" not in req["output_config"]  # open schema: prompt + validation instead
    assert req["output_config"]["effort"] == "xhigh"
    last = req["messages"][-1]["content"]
    assert last[0]["type"] == "image" and last[0]["source"]["media_type"] == "image/png" and last[-1]["text"] == "c"
    assert req["messages"][0]["content"][-1]["cache_control"] == {"type": "ephemeral"}  # repair turns reuse the prefix
    with pytest.raises(ProviderError, match="prefill"):
        p.build_request("S", msgs[:2])
    with pytest.raises(ProviderError):
        AnthropicProvider(effort="huge")


class _Stream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


def _msg(stop, text="", category=None):
    blocks = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(stop_reason=stop, content=blocks,
                           stop_details=SimpleNamespace(category=category, explanation=None) if stop == "refusal" else None)


def _client(replies, seen):
    def stream(**kw):
        seen.append(kw)
        return _Stream(replies.pop(0))
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)),
                           messages=SimpleNamespace(stream=stream))


def test_anthropic_complete_stop_reasons():
    seen = []
    p = AnthropicProvider(_client=_client([_msg("max_tokens", "{"), _msg("end_turn", '{"title": "t"}')], seen))
    assert p.complete("S", [{"role": "user", "content": "u"}], max_tokens=1000) == '{"title": "t"}'
    assert [s["max_tokens"] for s in seen] == [1000, 2000]  # truncated once: retried with a larger budget
    assert seen[0]["betas"] == ["server-side-fallback-2026-07-01"]
    p = AnthropicProvider(_client=_client([_msg("refusal", category="cyber")], []))
    with pytest.raises(RefusalError) as ei:
        p.complete("S", [{"role": "user", "content": "u"}])
    assert ei.value.category == "cyber"
    p = AnthropicProvider(_client=_client([_msg("max_tokens"), _msg("max_tokens")], []))
    with pytest.raises(TruncatedError):
        p.complete("S", [{"role": "user", "content": "u"}], max_tokens=100)


def test_anthropic_missing_sdk_is_a_clear_error(monkeypatch):
    import builtins

    real = builtins.__import__

    def no_anthropic(name, *a, **k):
        if name == "anthropic":
            raise ImportError("no")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", no_anthropic)
    with pytest.raises(ProviderError, match="pip install anthropic"):
        AnthropicProvider().complete("S", [{"role": "user", "content": "u"}])


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(replies, seen):
    def op(req, timeout=None):
        seen.append({"url": req.full_url, "method": req.get_method(), "headers": dict(req.header_items()),
                     "body": json.loads(req.data) if req.data else None, "timeout": timeout})
        r = replies.pop(0)
        if isinstance(r, int):
            raise urllib.error.HTTPError(req.full_url, r, "err", {"Retry-After": "0"}, io.BytesIO(b'{"error": "busy"}'))
        return _Resp(json.dumps(r).encode())
    return op


def _ok(text, finish="stop"):
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}


def test_openai_compat_request_payload_and_headers(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-123")
    base, env, _ = C.PRESETS["openrouter"]
    p = OpenAICompatProvider(name="openrouter", model="some/model", base_url=base, api_key_env=env,
                             supports_images=True, extra_headers={"X-Title": "vfactory"})
    from PIL import Image

    img = tmp_path / "f.jpg"
    Image.new("RGB", (40, 30)).save(img)
    body = p.build_request("SYS", [{"role": "user", "content": "go"}], json_schema=SCHEMA, images=[img], max_tokens=500)
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    parts = body["messages"][1]["content"]
    assert parts[0] == {"type": "text", "text": "go"} and parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert body["max_tokens"] == 500
    rf = body["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is False
    assert "maxLength" not in json.dumps(rf)
    assert "temperature" not in body
    h = p.headers()
    assert h["Authorization"] == "Bearer sk-test-123" and h["X-Title"] == "vfactory"
    assert "sk-test-123" not in json.dumps(body)


def test_openai_compat_json_modes():
    mk = lambda mode: OpenAICompatProvider(model="m", base_url="http://localhost:11434/v1", json_mode=mode)  # noqa: E731
    msgs = [{"role": "user", "content": "x"}]
    strict = mk("schema_strict").build_request("S", msgs, json_schema=SCHEMA)["response_format"]["json_schema"]
    assert strict["strict"] is True and strict["schema"]["required"] == ["title"]
    assert mk("object").build_request("S", msgs, json_schema=SCHEMA)["response_format"] == {"type": "json_object"}
    assert "response_format" not in mk("none").build_request("S", msgs, json_schema=SCHEMA)
    assert mk("schema").build_request("S", msgs, json_schema=schemas.LESSON)["response_format"] == {"type": "json_object"}
    # images are dropped for a text-only local model
    body = mk("schema").build_request("S", msgs, images=[b"\x89PNG\r\n\x1a\n"])
    assert body["messages"][1]["content"] == "x"
    with pytest.raises(ProviderError, match="needs a model"):
        OpenAICompatProvider(model="", base_url="http://x")


def test_openai_compat_retries_and_length(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    seen = []
    p = OpenAICompatProvider(model="m", base_url="http://localhost:1234/v1/", _sleep=lambda s: None,
                             _opener=_opener([429, 503, _ok("{", "length"), _ok('{"title": "t"}')], seen))
    assert p.complete("S", [{"role": "user", "content": "x"}], max_tokens=100) == '{"title": "t"}'
    assert seen[0]["url"] == "http://localhost:1234/v1/chat/completions" and seen[0]["method"] == "POST"
    assert [s["body"]["max_tokens"] for s in seen] == [100, 100, 100, 200]
    assert "Authorization" not in seen[0]["headers"]
    p = OpenAICompatProvider(model="m", base_url="http://x/v1", retries=0, _opener=_opener([401], []))
    with pytest.raises(ProviderError, match="HTTP 401"):
        p.complete("S", [{"role": "user", "content": "x"}])


def test_openai_compat_check_lists_models_without_tokens():
    seen = []
    p = OpenAICompatProvider(model="qwen3:32b", base_url="http://localhost:11434/v1",
                             _opener=_opener([{"data": [{"id": "qwen3:32b"}]}], seen))
    r = p.check()
    assert r["ok"] and seen[0]["url"].endswith("/models") and seen[0]["method"] == "GET"


def test_fake_provider_routes_by_stage_marker():
    f = FakeProvider(script={"idea": ["a", "b"], "spine": [{"x": 1}]})
    m = lambda s: [{"role": "user", "content": f"[stage:{s}] go"}]  # noqa: E731
    assert f.complete("S", m("idea")) == "a" and f.complete("S", m("idea")) == "b"
    assert f.complete("S", m("idea")) == "b"  # the last reply repeats
    assert json.loads(f.complete("S", m("spine"))) == {"x": 1}
    assert stage_of(m("fix")) == "fix"
    with pytest.raises(ProviderError):
        f.complete("S", m("gate"))


# ------------------------------------------------------------------------------------------------ config + CLI

def test_config_per_stage_and_cli_overrides(tmp_path):
    t = tmp_path / "agent.toml"
    t.write_text('''
[defaults]
provider = "claude"
fix_rounds = 2
[providers.claude]
type = "anthropic"
effort = "high"
[providers.local]
type = "openai"
preset = "ollama"
model = "qwen3:32b"
profile = "compact"
[stages]
idea = "local"
critique = { provider = "claude", effort = "xhigh" }
''')
    c = C.load(t)
    assert c.get("fix_rounds") == 2
    idea = c.stage_spec("idea")
    assert idea["type"] == "openai" and idea["base_url"] == "http://localhost:11434/v1" and idea["profile"] == "compact"
    assert c.stage_spec("critique")["effort"] == "xhigh"
    assert c.stage_spec("lesson")["type"] == "anthropic" and c.stage_spec("lesson")["max_tokens"] == 64000
    assert isinstance(C.make_provider(idea), OpenAICompatProvider)
    c2 = C.load(t, {"provider": "lmstudio", "model": "local-model", "stage": {"critique": "claude"}})
    assert c2.stage_spec("idea")["base_url"] == "http://localhost:1234/v1"
    assert c2.stage_spec("critique")["type"] == "anthropic"
    with pytest.raises(ProviderError, match="unknown provider"):
        C.load(t, {"provider": "nope"}).stage_spec("idea")


def test_cli_dry_run_and_providers(tmp_path, monkeypatch, capsys):
    from vfactory.agent.__main__ import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pipeline.subprocess, "run", Runner(lint=[CLEAN_LINT]))
    rc = main(["run", "Tư duy từ gốc", "--provider", "fake", "--runs-dir", str(tmp_path / "runs")])
    assert rc == 0
    d = tmp_path / "runs" / "tu-duy-tu-goc"
    assert (d / "package.json").exists() and json.loads((d / "build.json").read_text())["skipped"]
    assert main(["resume", str(d), "--provider", "fake"]) == 0  # nothing left to do
    assert main(["status", str(d)]) == 0
    assert main(["providers", "--no-network"]) in (0, 1)
    out = capsys.readouterr().out
    assert "stage → provider" in out and "ollama" in out
