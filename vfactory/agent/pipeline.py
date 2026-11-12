"""The episode pipeline: idea → research → spine → beats → lesson → critique → build → gate → fix → package.

All state lives in a run directory (default runs/<slug>/):

    run.json            topic, story hint, per-stage status/attempts/provider, config snapshot (no keys)
    notes.md, notes/, urls.txt   optional human input (read by idea + research; treated as data)
    brief.toml, brief.md         optional owner's production constraints (length, aspect, kicker, voice, end card,
                                 must-keep notes): INSTRUCTIONS for every writing stage, also set by CLI flags
    idea.json research.json research.md spine.json beats.json
    lesson.json script.md        the lesson (stage output) and lint's approval view
    critique.json build.json gate.json fix.json package.json package.md
    build/              `python -m vfactory.lesson build` output (video, gate/, qa.json)
    history/            lesson.json before every critique/fix edit
    transcripts/        every model call (prompt, reply, errors) for debugging
    log.jsonl           one line per model call and per command

Every model stage validates its JSON (stdlib validator + deterministic series rules + engine lint for the lesson) and
feeds the problems back to the model, at most `repair_tries` times. A finished stage is never redone on resume unless
asked (`--from STAGE` reruns that stage and everything after it).
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config as C
from . import rules, schemas
from .jsonutil import JSONExtractError, extract_json, validate
from .patch import PatchError, apply_ops
from .providers import Provider, ProviderError

PROMPTS = Path(__file__).parent / "prompts"
REPO = Path(__file__).resolve().parents[2]
STAGES = C.STAGES
NOTE_LIMIT = 40_000


class StageError(RuntimeError):
    def __init__(self, stage: str, message: str, errors: list[str] | None = None):
        super().__init__(f"[{stage}] {message}" + ("".join(f"\n  - {e}" for e in (errors or [])[:20])))
        self.stage, self.errors = stage, errors or []


def slugify(text: str, maxlen: int = 60) -> str:
    t = text.replace("đ", "d").replace("Đ", "D")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:maxlen].rstrip("-") or "episode"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=1)


def drop_nulls(x):
    """Providers in strict mode return optional fields as null; our schemas mean 'absent'."""
    if isinstance(x, dict):
        return {k: drop_nulls(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [drop_nulls(v) for v in x]
    return x


def render(template: str, **values) -> str:
    def sub(m):
        v = values.get(m.group(1), "")
        return v if isinstance(v, str) else _dump(v)
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def system_prompt(profile: str = "full") -> str:
    """The shared system prompt with the engine's sticker vocabulary filled in. It depends only on the install (not on
    the run or the stage), so it stays byte-identical across calls and is cached."""
    v = rules.engine_vocab()
    everyday = [k for k in ("phone", "coffee", "laptop", "scooter", "cash", "receipt", "parcel", "bag", "banhmi",
                            "phin", "cart", "chat", "heart") if k in v["icons"]]
    return render(prompt("system_compact" if profile == "compact" else "system"),
                  expressions=", ".join(v["expressions"]), actions=", ".join(v["actions"]), sets="|".join(v["sets"]),
                  transitions="|".join(v["transitions"]), props=", ".join(everyday) or "phone, coffee",
                  look_keys=", ".join(v["look_keys"]), hairs="|".join(v["hairs"]), outfits="|".join(v["outfits"]),
                  ages="|".join(v["ages"]))


# ------------------------------------------------------------------------------------------------- lint (engine CLI)

def _shadow_stage(v: dict) -> dict:
    props = v.get("props") or []
    chars = v.get("characters") or []
    bubbles = ([v["bubble"]] if v.get("bubble") else []) + list(v.get("bubbles") or [])
    line = v.get("caption") or (bubbles[0].get("text") if bubbles else "") or ""
    nv = {"type": "icon", "icon": (props[0].get("icon") if props else None) or "people", "_shadow_of": "stage"}
    if line:
        nv["line"] = line
    nv["action"] = next((c.get("action") for c in chars if c.get("action")), None) or "đứng"
    if v.get("cue"):
        nv["cue"] = v["cue"]
    return nv


def shadow_lesson(L: dict) -> dict:
    """A copy of the lesson that an engine lint without the sticker `stage` type can read: every `stage` picture (a
    beat's visual, or a shot inside `shots`) becomes an `icon` picture carrying the same on-screen words, while
    narration, sources and certainty stay as written. Lint's other checks (hook, numbers, sources, hedging, length,
    storyboard) still run."""
    S = copy.deepcopy(L)
    for b in S.get("beats", []):
        v = b.get("visual") or {}
        if v.get("type") == "stage":
            b["visual"] = _shadow_stage(v)
        elif v.get("type") == "shots":
            v["shots"] = [_shadow_stage(sh) if isinstance(sh, dict) and sh.get("type") == "stage" else sh
                          for sh in v.get("shots") or []]
    return S


def parse_lint(stdout: str, stderr: str, rc: int) -> dict:
    out = {"errors": [], "warnings": [], "story": [], "stats": None, "crash": None, "rc": rc}
    for line in stdout.splitlines():
        if line.startswith("ERROR  "):
            out["errors"].append(line[7:].strip())
        elif line.startswith("warn   "):
            out["warnings"].append(line[7:].strip())
        elif line.startswith("story  "):
            out["story"].append(line[7:].strip())
    m = re.search(r"^\{.*?^\}", stdout, re.S | re.M)
    if m:
        try:
            out["stats"] = json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    if rc != 0 and not out["errors"]:
        # schema.load raised (e.g. LessonError for an unknown visual type) or lint crashed: the last line says why
        tail = [ln for ln in (stderr or stdout).strip().splitlines() if ln.strip()]
        last = tail[-1] if tail else f"lint exited with code {rc}"
        # LessonError = the lesson is wrong (feed it back); anything else = the engine itself is broken
        out["crash_kind"] = "lesson" if "LessonError" in last else "engine"
        msg = re.sub(r"^[\w.]*(LessonError|Error|Exception):\s*", "", last)
        out["crash"] = msg
        out["errors"].append(msg)
    return out


# ------------------------------------------------------------------------------------------------- pipeline

class Pipeline:
    def __init__(self, run_dir: str | Path, cfg: C.Config | None = None, *, providers: dict | None = None,
                 runner: Callable | None = None, log: Callable = print, python: str = sys.executable):
        self.dir = Path(run_dir)
        self.cfg = cfg or C.Config()
        if isinstance(providers, Provider):  # one provider for every stage
            providers = {s: providers for s in C.MODEL_STAGES}
        self._providers: dict[str, Provider] = dict(providers or {})  # stage -> Provider (tests inject here)
        self._cache: dict[str, Provider] = {}
        self.runner = runner or (lambda *a, **k: subprocess.run(*a, **k))  # looked up per call (patchable)
        self.say = log
        self.python = python
        self.state = json.loads((self.dir / "run.json").read_text()) if (self.dir / "run.json").exists() else {}

    # ---- creation / persistence
    @classmethod
    def create(cls, topic: str, cfg: C.Config | None = None, *, story_hint: str = "", slug: str | None = None,
               runs_dir: str | Path | None = None, series: str | None = None, brief: dict | None = None,
               **kw) -> "Pipeline":
        cfg = cfg or C.Config()
        root = Path(runs_dir or cfg.get("runs_dir"))
        d = root / (slug or slugify(topic))
        d.mkdir(parents=True, exist_ok=True)
        p = cls(d, cfg, **kw)
        if not p.state:
            p.state = {"topic": topic, "story_hint": story_hint, "slug": d.name, "created": _now(),
                       "series": series or cfg.get("series", "Khung tư duy · Tập mới"), "stages": {}}
        else:  # an existing run: keep its topic unless the caller changes it explicitly
            p.state.setdefault("stages", {})
        if brief:
            p.set_brief(brief, save=False)
        p.save()
        return p

    # ---- the owner's brief (production constraints: instructions, not data)
    def set_brief(self, brief: dict, save: bool = True) -> None:
        """Store CLI brief flags in run.json (they win over brief.toml/brief.md and survive resume)."""
        cur = dict(self.state.get("brief") or {})
        new = C.normalize_brief(brief)
        if "must_keep" in new:
            new["must_keep"] = list(dict.fromkeys(cur.get("must_keep", []) + new["must_keep"]))
        cur.update(new)
        self.state["brief"] = cur
        if save:
            self.save()

    def brief(self) -> dict:
        """Series defaults < brief.toml/brief.md < CLI flags. `owner_set` lists the keys the owner gave (enforced)."""
        series = self.state.get("series") or self.cfg.get("series", "Khung tư duy · Tập mới")
        b = {"target_minutes": [4, 6], "aspect": "16:9", "kicker": series, "voice": C.DEFAULT_VOICE,
             "end_narration": self.cfg.get("end_narration") or C.SIGN_OFF, "end_ask": C.DEFAULT_ASK,
             "end_ask_hint": "", "must_keep": []}
        files = C.load_brief_files(self.dir)
        cli = self.state.get("brief") or {}
        keep = list(dict.fromkeys(files.get("must_keep", []) + cli.get("must_keep", [])))
        b.update(files)
        b.update(cli)
        b["must_keep"] = keep
        b["owner_set"] = sorted(k for k in (set(files) | set(cli)) if k != "must_keep")
        return b

    def brief_text(self) -> str:
        """The brief as the prompts show it: the owner's instructions for this episode."""
        b = self.brief()
        lo, hi = b["target_minutes"][0], b["target_minutes"][-1]
        syl = (round(lo * 60 * rules.FILM_SYL_PER_MIN / 60), round(hi * 60 * rules.FILM_SYL_PER_MIN / 60))
        lines = [f"- Length: {lo}–{hi} minutes. Plan on about {syl[0]}–{syl[1]} Vietnamese syllables of narration in "
                 f"total (measured: the films run ~{rules.FILM_SYL_PER_MIN:.0f} syllables per minute at speed 0.88 once "
                 "pauses, the title sting and the question are counted).",
                 f"- Aspect: {b['aspect']}.",
                 f"- Series kicker (title sting and end card): \"{b['kicker']}\".",
                 f"- Voice (meta.voice): \"{b['voice']}\".",
                 f"- End-card narration, word for word (a cached voice take): \"{b['end_narration']}\".",
                 f"- End-card ask (the one CTA): \"{b['end_ask']}\"."]
        if b.get("end_ask_hint"):
            lines.append(f"- End-card ask_hint: \"{b['end_ask_hint']}\".")
        if b["must_keep"]:
            lines.append("- Must keep (the owner's notes; follow them):")
            lines += ["  " + ln for k in b["must_keep"] for ln in ("- " + k.strip()).splitlines()]
        return "\n".join(lines)

    def save(self) -> None:
        self.state["updated"] = _now()
        self.state["config"] = {"source": self.cfg.source,
                                "stages": {s: C.public_spec(self.cfg.stage_spec(s)) for s in C.MODEL_STAGES
                                           if self._spec_ok(s)}}
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "run.json").write_text(_dump(self.state))

    def _spec_ok(self, s) -> bool:
        try:
            self.cfg.stage_spec(s)
            return True
        except ProviderError:
            return False

    def path(self, name: str) -> Path:
        return self.dir / name

    def read(self, stage: str):
        p = self.path(f"{stage}.json")
        if not p.exists():
            raise StageError(stage, f"{p} is missing: run that stage first")
        return json.loads(p.read_text())

    def write(self, stage: str, data) -> None:
        self.path(f"{stage}.json").write_text(_dump(data))

    def status(self, stage: str, status: str, **extra) -> None:
        st = self.state.setdefault("stages", {}).setdefault(stage, {})
        st.update(status=status, at=_now(), **extra)
        self.save()

    def event(self, **kw) -> None:
        with (self.dir / "log.jsonl").open("a") as f:
            f.write(json.dumps({"t": _now(), **kw}, ensure_ascii=False) + "\n")

    # ---- providers
    def provider(self, stage: str) -> Provider:
        if stage in self._providers:
            return self._providers[stage]
        spec = self.cfg.stage_spec(stage)
        key = json.dumps(spec, sort_keys=True, default=str)
        if key not in self._cache:
            self._cache[key] = C.make_provider(spec)
        return self._cache[key]

    def system(self, stage: str) -> str:
        profile = self.cfg.stage_spec(stage).get("profile", "full") if stage not in self._providers else "full"
        return system_prompt(profile)

    def compact(self, stage: str) -> bool:
        return stage not in self._providers and self.cfg.stage_spec(stage).get("profile") == "compact"

    # ---- the model call with validation and repair
    def ask_json(self, stage: str, user: str, schema: dict, *, check: Callable | None = None, images=None,
                 max_tokens: int | None = None):
        prov = self.provider(stage)
        system = self.system(stage)
        tries = int(self.cfg.get("repair_tries"))
        mt = max_tokens or (self.cfg.stage_spec(stage)["max_tokens"] if stage not in self._providers else
                            C.MAX_TOKENS.get(stage, 16000))
        messages = [{"role": "user", "content": user}]
        errors: list[str] = []
        tdir = self.dir / "transcripts"
        tdir.mkdir(exist_ok=True)
        for attempt in range(1, tries + 1):
            t0 = time.time()
            try:
                reply = prov.complete(system, messages, json_schema=schema, images=images if attempt == 1 else None,
                                      max_tokens=mt)
            except ProviderError as e:
                self.event(stage=stage, attempt=attempt, provider=prov.name, model=prov.model, error=str(e))
                raise StageError(stage, f"{prov.describe()}: {e}") from e
            data, errors = None, []
            try:
                data = drop_nulls(extract_json(reply))
                errors = validate(data, schema)
                if not errors and check:
                    errors = list(check(data) or [])
            except JSONExtractError as e:
                errors = [f"not valid JSON: {e}"]
            n = len(list(tdir.glob(f"{stage}-*.json"))) + 1
            (tdir / f"{stage}-{n:02d}.json").write_text(_dump({
                "stage": stage, "attempt": attempt, "provider": prov.name, "model": prov.model,
                "messages": messages, "images": [str(i) for i in (images or [])] if attempt == 1 else [],
                "reply": reply, "errors": errors}))
            self.event(stage=stage, attempt=attempt, provider=prov.name, model=prov.model,
                       seconds=round(time.time() - t0, 2), reply_chars=len(reply or ""), errors=len(errors))
            if not errors:
                st = self.state["stages"].setdefault(stage, {})
                st.update(attempts=st.get("attempts", 0) + attempt, provider=prov.name, model=prov.model)
                return data
            self.say(f"  [{stage}] attempt {attempt}: {len(errors)} problem(s); " +
                     ("asking for a repair" if attempt < tries else "giving up"))
            messages = [messages[0], {"role": "assistant", "content": reply or ""},
                        {"role": "user", "content": render(prompt("repair"), errors="\n".join(f"- {e}" for e in errors[:40]))}]
        raise StageError(stage, f"no valid output after {tries} tries", errors)

    # ---- inputs
    def notes(self) -> str:
        parts = []
        extra = sorted((self.dir / "notes").glob("*")) if (self.dir / "notes").is_dir() else []
        for p in [self.path("notes.md"), self.path("urls.txt"), *extra]:
            if p.is_file() and p.suffix.lower() in (".md", ".txt", ".csv", ".json", ""):
                parts.append(f"## {p.name}\n{p.read_text(errors='replace')[:NOTE_LIMIT]}")
        return "\n\n".join(parts) or "(none)"

    def research_view(self, stage: str):
        R = self.read("research")
        if not self.compact(stage):
            return R
        return {"sources": [{"id": s["id"], "cite": s["cite"]} for s in R.get("sources", [])],
                "claims": [f"{c['id']} [{c['certainty']}, {c['use']}]: {c.get('say') or c['claim']} (sources: "
                           f"{', '.join(c['sources'])})" for c in R.get("claims", []) if c.get("use") != "cut"]}

    @staticmethod
    def icons() -> str:
        return ", ".join(rules.icon_keys()) or "rocket, pot, packet, glass, coin, store, people"

    # ---- lint through the engine CLI
    def lint(self, L: dict) -> dict:
        """Run `python -m vfactory.lesson lint` on a copy of L. lint_mode: strict (as written), shadow (stage beats
        mapped to icon beats), auto (strict when the engine knows `stage`, else shadow; and a strict run that dies on
        the unknown `stage` type falls back to shadow). Returns {errors, warnings, story, mode, engine_gap, ...}."""
        mode = self.cfg.get("lint_mode")
        knows = rules.engine_knows_stage()
        if mode == "auto":
            mode = "strict" if knows else "shadow"
        res = self._lint_once(shadow_lesson(L) if mode == "shadow" else L)
        res["mode"], res["engine_gap"] = mode, not knows
        if mode == "strict" and res.get("crash") and re.search(r"visual\.type must be one of|'stage'|stage", res["crash"]) \
                and any(any(True for _ in rules.stage_visuals(b.get("visual") or {})) for b in L.get("beats", [])) \
                and self.cfg.get("lint_mode") == "auto":
            res = self._lint_once(shadow_lesson(L))
            res["mode"], res["engine_gap"] = "shadow", True
        return res

    def _lint_once(self, L: dict) -> dict:
        d = self.dir / ".lint"
        d.mkdir(exist_ok=True)
        f = d / "lesson.json"
        f.write_text(_dump(L))
        cmd = [self.python, "-m", "vfactory.lesson", "lint", str(f)]
        try:
            r = self.runner(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=300)
        except FileNotFoundError as e:
            return {"errors": [f"cannot run lint: {e}"], "warnings": [], "story": [], "crash": str(e), "rc": -1}
        except subprocess.TimeoutExpired:
            return {"errors": ["lint timed out"], "warnings": [], "story": [], "crash": "timeout", "rc": -1}
        res = parse_lint(r.stdout or "", r.stderr or "", r.returncode)
        self.event(command="lint", rc=r.returncode, errors=len(res["errors"]), warnings=len(res["warnings"]))
        return res

    def check_lesson(self, L: dict, research: dict | None) -> tuple[list[str], dict]:
        errs, warns = rules.check_lesson(L, research=research, brief=self.brief())
        lint = {"errors": [], "warnings": [], "story": []}
        if not errs:  # lint only a lesson that passes the cheap checks (saves a subprocess per bad draft)
            lint = self.lint(L)
            if lint.get("crash_kind") == "engine":
                (self.dir / "lesson.draft.json").write_text(_dump(L))
                raise StageError("lesson", "the engine's lint crashed (an engine problem, not this lesson): "
                                 f"{lint['crash']}. The draft is saved as lesson.draft.json; fix the engine, then "
                                 "resume (or --lint-mode shadow if the crash is about the `stage` type)")
            errs += [f"lint: {e}" for e in lint["errors"]]
            if self.cfg.get("lint_warnings_block", False):
                errs += [f"lint warning: {w}" for w in lint["warnings"] + lint.get("story", [])]
        return errs, {"rules_warnings": warns, "lint": lint}

    def _save_lesson(self, L: dict, why: str) -> None:
        L = rules.normalize_lesson(L)
        cur = self.path("lesson.json")
        if cur.exists():
            h = self.dir / "history"
            h.mkdir(exist_ok=True)
            n = len(list(h.glob("lesson.*.json"))) + 1
            shutil.copy(cur, h / f"lesson.{n:02d}.{why}.json")
        cur.write_text(_dump(L))
        if (self.dir / ".lint" / "script.md").exists():
            shutil.copy(self.dir / ".lint" / "script.md", self.path("script.md"))

    # ================================================================================================ stages
    def stage_idea(self):
        user = render(prompt("idea"), topic=self.state["topic"], story_hint=self.state.get("story_hint") or "(none)",
                      series=self.state.get("series", ""), notes=self.notes(), icons=self.icons(),
                      brief=self.brief_text(),
                      schema=json.dumps(schemas.IDEA, ensure_ascii=False))
        self.write("idea", self.ask_json("idea", user, schemas.IDEA, check=_check_idea))

    def stage_research(self):
        user = render(prompt("research"), idea=self.read("idea"), notes=self.notes(), brief=self.brief_text(),
                      schema=json.dumps(schemas.RESEARCH, ensure_ascii=False))
        R = self.ask_json("research", user, schemas.RESEARCH, check=_check_research)
        self.write("research", R)
        self.path("research.md").write_text(research_markdown(R, self.state))

    def stage_spine(self):
        b = self.brief()
        lo, hi = b["target_minutes"][0] * 60, b["target_minutes"][-1] * 60
        user = render(prompt("spine"), idea=self.read("idea"), research=self.research_view("spine"),
                      brief=self.brief_text(), seconds=f"{lo:.0f}–{hi:.0f}",
                      schema=json.dumps(schemas.SPINE_SCHEMA, ensure_ascii=False))
        research = self.read("research")
        win = rules.length_window(b["target_minutes"])
        self.write("spine", self.ask_json("spine", user, schemas.SPINE_SCHEMA,
                                          check=lambda d: _check_spine(d, research, win)))

    def stage_beats(self):
        user = render(prompt("beats"), idea=self.read("idea"), research=self.research_view("beats"),
                      spine=self.read("spine"), brief=self.brief_text(),
                      schema=json.dumps(schemas.BEATS, ensure_ascii=False))
        research = self.read("research")
        win = rules.length_window(self.brief()["target_minutes"])
        self.write("beats", self.ask_json("beats", user, schemas.BEATS, check=lambda d: _check_beats(d, research, win)))

    def stage_lesson(self):
        research = self.read("research")
        b = self.brief()
        user = render(prompt("lesson"), idea=self.read("idea"), research=self.research_view("lesson"),
                      spine=self.read("spine"), beats=self.read("beats"), series=self.state.get("series", ""),
                      brief=self.brief_text(), kicker=b["kicker"], aspect=b["aspect"], voice=b["voice"],
                      target_minutes=json.dumps(b["target_minutes"]), end_narration=b["end_narration"],
                      ask=b["end_ask"], ask_hint=b["end_ask_hint"] or "<three other frameworks, ' · ' separated>",
                      icons=self.icons())
        report: dict = {}

        def check(L):
            errs, rep = self.check_lesson(L, research)
            report.clear()
            report.update(rep)
            return errs

        L = self.ask_json("lesson", user, schemas.LESSON, check=check)
        self._save_lesson(L, "lesson")
        self.write("lesson_check", report)

    def stage_critique(self):
        research = self.read("research")
        rounds = []
        for r in range(int(self.cfg.get("critique_rounds"))):
            L = self.read("lesson")
            chk = self.read("lesson_check") if self.path("lesson_check.json").exists() else {}
            user = render(prompt("critique"), research=self.research_view("critique"), lesson=L, notes=chk or "(none)",
                          brief=self.brief_text(),
                          schema=json.dumps(schemas.CRITIQUE, ensure_ascii=False))
            patched: dict = {}

            def check(d):
                try:
                    L2 = apply_ops(L, d.get("ops", []))
                except PatchError as e:
                    return [f"ops: {e}"]
                errs, rep = self.check_lesson(L2, research)
                if errs:
                    return [f"after your ops: {x}" for x in errs]
                patched.update(lesson=L2, report=rep)
                return []

            d = self.ask_json("critique", user, schemas.CRITIQUE, check=check)
            if d.get("ops"):
                self._save_lesson(patched["lesson"], "critique")
                self.write("lesson_check", patched["report"])
            rounds.append({"verdict": d["verdict"], "pixar_checks": d.get("pixar_checks"), "issues": d.get("issues", []),
                           "ops_applied": len(d.get("ops", []))})
            if d["verdict"] == "pass" or not d.get("ops"):
                break
        self.write("critique", {"rounds": rounds})

    # -- build / gate (engine CLIs)
    def build_enabled(self) -> bool:
        return bool(self.cfg.get("build"))

    def _cmd(self, args: list[str], log_name: str, timeout=None):
        cmd = [self.python, "-m", "vfactory.lesson", *args]
        t0 = time.time()
        r = self.runner(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=timeout)
        bd = self.dir / "build"
        bd.mkdir(exist_ok=True)
        (bd / log_name).write_text(f"$ {' '.join(cmd)}\n\n{r.stdout or ''}\n{r.stderr or ''}")
        self.event(command=args[0], rc=r.returncode, seconds=round(time.time() - t0, 1))
        return r

    def stage_build(self):
        if not self.build_enabled():
            self.write("build", {"skipped": True, "reason": "build disabled (--no-build or a fake provider)"})
            return "skipped"
        if not rules.engine_knows_stage() and any(any(True for _ in rules.stage_visuals(b.get("visual") or {}))
                                                  for b in self.read("lesson")["beats"]):
            raise StageError("build", "the engine does not know the sticker `stage` visual yet (vfactory/lesson is "
                                      "still being extended). The lesson is written and linted; build after the engine "
                                      "work lands: `python -m vfactory.agent resume <run> --from build`")
        r = self._cmd(["build", str(self.path("lesson.json").resolve()), "--out", str((self.dir / "build").resolve()),
                       "--final"], "build.log")
        if r.returncode != 0:
            tail = "\n".join(((r.stderr or "") + (r.stdout or "")).strip().splitlines()[-12:])
            raise StageError("build", f"build failed (exit {r.returncode}); see build/build.log", [tail])
        info = extract_json(r.stdout) if (r.stdout or "").strip() else {}
        self.write("build", {"skipped": False, "result": info, "at": _now()})

    def _gate_once(self, round_no: int = 0) -> dict:
        r = self._cmd(["gate", str(self.path("lesson.json").resolve()), "--out", str((self.dir / "build").resolve())],
                      f"gate{round_no}.log")
        if r.returncode not in (0, 3):
            raise StageError("gate", f"gate command failed (exit {r.returncode}); see build/gate{round_no}.log",
                             ((r.stderr or "") + (r.stdout or "")).strip().splitlines()[-8:])
        bd = self.dir / "build"
        rep_p = bd / "gate" / "report.json"
        report = json.loads(rep_p.read_text()) if rep_p.exists() else {"verdict": "block", "fails": ["no gate/report.json"],
                                                                       "warnings": []}
        qa = next((json.loads(p.read_text()) for p in (bd / "qa.json", bd / "gate" / "qa.json") if p.exists()), None)
        prov = self.provider("gate")
        images = []
        if self.cfg.get("vision_review") and prov.supports_images:
            ev = report.get("evidence") or {}
            images = [Path(ev[k]) for k in ("hook", "scenes", "phone", "thumb") if ev.get(k)]
            images += sorted(bd.glob("hf/.hyperframes/artifacts/snapshots/*/contact-sheet-*.jpg"))
            images = [p for p in images if p.exists()][: int(self.cfg.get("max_images"))]
        review = None
        if self.cfg.get("llm_review", True):
            user = render(prompt("review"), images=", ".join(p.name for p in images) or "(none: text-only review)",
                          report={k: report.get(k) for k in ("verdict", "fails", "warnings", "metrics")},
                          qa=qa or "(none)", lesson=self.read("lesson"),
                          schema=json.dumps(schemas.REVIEW, ensure_ascii=False))
            review = self.ask_json("gate", user, schemas.REVIEW, images=images or None)
        rv = report.get("verdict", "block")
        if rv == "block" or (review and review["verdict"] == "block"):
            verdict = "block"
        elif review is not None:
            verdict = review["verdict"]
        else:
            verdict = rv
        g = {"round": round_no, "verdict": verdict, "report_verdict": rv, "fails": report.get("fails", []),
             "warnings": report.get("warnings", []), "metrics": report.get("metrics", {}), "qa": qa,
             "review": review, "vision": bool(images), "images": [str(p) for p in images], "at": _now()}
        self.write("gate", g)
        return g

    def stage_gate(self):
        if self.read("build").get("skipped"):
            self.write("gate", {"skipped": True, "verdict": "not built"})
            return "skipped"
        g = self._gate_once(0)
        self.say(f"  gate verdict: {g['verdict']}")

    def stage_fix(self):
        g = self.read("gate")
        if g.get("skipped"):
            self.write("fix", {"skipped": True})
            return "skipped"
        research = self.read("research")
        n = int(self.cfg.get("fix_rounds"))
        rounds, needs = [], []
        r = 0
        while g["verdict"] != "pass" and r < n:
            r += 1
            L = self.read("lesson")
            user = render(prompt("fix"), round=str(r), rounds=str(n), gate=g, research=self.research_view("fix"),
                          lesson=L, brief=self.brief_text(), schema=json.dumps(schemas.FIX, ensure_ascii=False))
            patched: dict = {}

            def check(d):
                try:
                    L2 = apply_ops(L, d.get("ops", []))
                except PatchError as e:
                    return [f"ops: {e}"]
                errs, rep = self.check_lesson(L2, research)
                if errs:
                    return [f"after your ops: {x}" for x in errs]
                patched.update(lesson=L2, report=rep)
                return []

            d = self.ask_json("fix", user, schemas.FIX, check=check)
            needs += d.get("needs_human", [])
            if not d.get("ops"):
                rounds.append({"round": r, "summary": d["summary"], "ops": 0, "verdict": g["verdict"]})
                break
            self._save_lesson(patched["lesson"], f"fix{r}")
            self.write("lesson_check", patched["report"])
            self.stage_build()
            g = self._gate_once(r)
            rounds.append({"round": r, "summary": d["summary"], "ops": len(d["ops"]), "verdict": g["verdict"]})
            self.say(f"  fix round {r}: {len(d['ops'])} edit(s) → gate {g['verdict']}")
        self.write("fix", {"rounds": rounds, "verdict": g["verdict"], "needs_human": needs})
        if g["verdict"] != "pass":
            raise StageError("fix", f"the gate did not pass after {r} round(s) (verdict {g['verdict']}); nothing is "
                                    "delivered. See gate.json, fix.json (needs_human) and run the video-gatekeeper.",
                             needs)

    def stage_package(self):
        L = self.read("lesson")
        g = self.read("gate") if self.path("gate.json").exists() else {}
        user = render(prompt("package"), lesson=L, gate={k: g.get(k) for k in ("verdict", "review")} if g else "(none)",
                      brief=self.brief_text(),
                      schema=json.dumps(schemas.PACKAGE, ensure_ascii=False))
        P = self.ask_json("package", user, schemas.PACKAGE, check=lambda d: rules.check_package(d, L))
        self.write("package", P)
        L["meta"]["youtube"] = {k: P[k] for k in ("title", "thumbnail_text", "description", "chapters", "tags") if k in P}
        self._save_lesson(L, "package")
        self.path("package.md").write_text(
            f"# {P['title']}\n\nThumbnail: {P['thumbnail_text']}\n\n{P['description']}\n\n## Chương\n" +
            "".join(f"- {c}\n" for c in P.get("chapters", [])) + f"\nTags: {', '.join(P['tags'])}\n\n"
            f"Bình luận ghim: {P.get('pinned_comment', '')}\n")

    # ================================================================================================ driver
    def run(self, from_stage: str | None = None, until: str | None = None) -> dict:
        start = STAGES.index(from_stage) if from_stage else 0
        stop = STAGES.index(until) if until else len(STAGES) - 1
        if from_stage:  # rerunning a stage invalidates everything after it
            for s in STAGES[start:]:
                if s in self.state.get("stages", {}):
                    self.state["stages"][s]["status"] = "stale"
        for s in STAGES[start:stop + 1]:
            if self.state.get("stages", {}).get(s, {}).get("status") in ("done", "skipped") and not from_stage:
                self.say(f"✓ {s} (done)")
                continue
            self.say(f"→ {s}")
            self.status(s, "running")
            t0 = time.time()
            try:
                res = getattr(self, f"stage_{s}")()
            except StageError as e:
                self.status(s, "failed", error=str(e)[:2000], seconds=round(time.time() - t0, 1))
                raise
            except Exception as e:  # noqa: BLE001 - record, then surface
                self.status(s, "failed", error=f"{type(e).__name__}: {e}"[:2000])
                raise
            self.status(s, "skipped" if res == "skipped" else "done", seconds=round(time.time() - t0, 1))
        return self.state


# ------------------------------------------------------------------------------------------------- stage checks

def _check_idea(d: dict) -> list[str]:
    e = []
    if not 0 <= d.get("chosen", -1) < len(d.get("storylines", [])):
        e.append("'chosen' must index storylines")
    return e


def _check_research(R: dict) -> list[str]:
    e = []
    ids = [s["id"] for s in R["sources"]]
    if len(set(ids)) != len(ids):
        e.append("source ids must be unique")
    cids = [c["id"] for c in R["claims"]]
    if len(set(cids)) != len(cids):
        e.append("claim ids must be unique")
    for c in R["claims"]:
        for s in c["sources"]:
            if s not in ids:
                e.append(f"claim {c['id']}: source {s!r} is not listed in sources")
        notes_backed = any(src.get("from_notes") for src in R["sources"] if src["id"] in c["sources"])
        if c.get("verified") and not notes_backed:
            e.append(f"claim {c['id']}: 'verified' is true only when a source from the human notes backs it")
        if c["certainty"] == "disputed" and c["use"] == "voice":
            e.append(f"claim {c['id']}: disputed claims are hedged or cut, never voiced as fact")
        say = c.get("say", "")
        if c["certainty"] in ("attributed", "estimate") and c["use"] == "voice" and not (
                rules.HEDGE_RE.search(say) or (c["certainty"] == "estimate" and re.search(r"minh họa", say, re.I))):
            e.append(f"claim {c['id']}: {c['certainty']} — its 'say' must hedge out loud (theo…, khoảng, ước tính…) "
                     "or set use to 'hedge'")
        if re.search(r"\d", c.get("say", "")):
            e.append(f"claim {c['id']}: 'say' is spoken Vietnamese: numbers in words, no digits")
    for s in R["sources"]:
        if s.get("from_notes") and s.get("kind") not in ("notes", "primary", "secondary"):
            e.append(f"source {s['id']}: from_notes sources are notes/primary/secondary")
    return e


def _window_msg(win: tuple[float, float]) -> str:
    return f"aim for {win[0] / 0.9:.0f}-{win[1] / 1.05:.0f} s (the owner's target length)"


def _check_spine(d: dict, research: dict, win: tuple[float, float] = (216.0, 378.0)) -> list[str]:
    e = []
    acts = [a["act"] for a in d["acts"]]
    if acts != list(rules.SPINE):
        e.append(f"acts must be exactly, in order: {list(rules.SPINE)}")
    known = {c["id"] for c in research.get("claims", [])}
    for a in d["acts"]:
        for c in a.get("claims", []):
            if c not in known:
                e.append(f"act {a['act']}: unknown claim id {c!r} (use the research pack's ids)")
    total = sum(a.get("seconds", 0) for a in d["acts"])
    if not win[0] <= total <= win[1]:
        e.append(f"total length {total:.0f}s: {_window_msg(win)}")
    return e


def _check_beats(d: dict, research: dict, win: tuple[float, float] = (216.0, 378.0)) -> list[str]:
    e = []
    beats = d["beats"]
    ids = [b["id"] for b in beats]
    if len(set(ids)) != len(ids):
        e.append("beat ids must be unique")
    if beats[0]["act"] != "hook":
        e.append("the first beat is the hook")
    if beats[-1]["act"] != "close" or beats[-1]["thread"] != "card":
        e.append("the last beat is the end card (act close, thread card)")
    cast = {c["id"] for c in d.get("cast", [])}
    claims = {c["id"]: c for c in research.get("claims", [])}
    for b in beats:
        for c in b.get("characters", []):
            if c not in cast:
                e.append(f"{b['id']}: character {c!r} is not in cast")
        for c in b.get("claims", []):
            if c not in claims:
                e.append(f"{b['id']}: unknown claim id {c!r}")
            elif claims[c].get("use") == "cut":
                e.append(f"{b['id']}: claim {c!r} was cut in research")
        if re.search(r"\d", b.get("narration_draft", "")):
            e.append(f"{b['id']}: narration_draft has digits: numbers as Vietnamese words")
    if not any("hư cấu" in b.get("narration_draft", "") for b in beats):
        e.append("one beat labels the fiction (\"nhân vật hư cấu, chuyện có thật\")")
    for need in ("misconception", "question", "recap"):
        if need not in [b["act"] for b in beats]:
            e.append(f"no {need!r} beat")
    total = sum(b.get("seconds", 0) for b in beats)
    if not win[0] <= total <= win[1]:
        e.append(f"total {total:.0f}s: {_window_msg(win)}")
    return e


def research_markdown(R: dict, state: dict) -> str:
    """The human review view of the research pack: check `open_items` in a browser, edit research.json, resume."""
    src = {s["id"]: s for s in R["sources"]}
    rows = ["| id | claim | certainty | use | verified | sources |", "|---|---|---|---|---|---|"]
    for c in R["claims"]:
        rows.append(f"| {c['id']} | {c['claim']}{' — ' + c['value'] if c.get('value') else ''} | {c['certainty']} | "
                    f"{c['use']} | {'yes' if c.get('verified') else 'NO'} | {', '.join(c['sources'])} |")
    out = [f"# Research pack — {state.get('topic', '')}", "",
           "Model-proposed claims. `verified` = backed by your notes; everything else must be checked before the voice "
           "is locked. Edit research.json (set use to cut/hedge, fix values), then "
           "`python -m vfactory.agent resume <run> --from spine`.", "", *rows, "", "## Sources"]
    out += [f"- **{s['id']}** ({s.get('kind')}{', from notes' if s.get('from_notes') else ''}): {s['cite']}"
            f"{' — ' + s['url'] if s.get('url') else ''}" for s in src.values()]
    if R.get("myths"):
        out += ["", "## Myths to correct"] + [f"- {m['myth']} → {m['truth']}" for m in R["myths"]]
    out += ["", "## Open items (check in a browser)"] + ([f"- [ ] {o}" for o in R.get("open_items", [])] or ["- none"])
    if R.get("neutral_line"):
        out += ["", f"Neutral line: {R['neutral_line']}"]
    return "\n".join(out) + "\n"
