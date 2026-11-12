"""python -m vfactory.agent <command>

  run "TOPIC" [--story-hint TEXT] [--series S] [--slug SLUG] [--runs-dir DIR] [--from STAGE] [--until STAGE]
              [--no-build] [--no-vision] [--fix-rounds N] [provider flags]
  resume RUN [--from STAGE] [--until STAGE] [provider flags]      RUN = a run directory or a slug under runs_dir
  status RUN                                                       the stage table of a run
  providers [--no-network]                                         configured providers and whether they answer

brief flags (the owner's production constraints; also <run>/brief.toml, <run>/brief.md; stored in run.json):
                --minutes 4-5 --aspect 16:9 --kicker "Khung tư duy · Tập 1" --voice V --end-narration TEXT
                --ask TEXT --ask-hint TEXT --keep NOTE (repeatable)

provider flags: --config agent.toml --provider NAME --model M --base-url URL --api-key-env VAR
                --effort low|medium|high|xhigh|max --stage STAGE=PROVIDER (repeatable)
Stages: idea research spine beats lesson critique build gate fix package
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config as C
from .pipeline import Pipeline, StageError
from .providers import PRESETS, ProviderError


def _provider_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config")
    p.add_argument("--provider", help="a [providers.NAME] from agent.toml, anthropic, fake, or a preset: "
                                      + ", ".join(PRESETS))
    p.add_argument("--model")
    p.add_argument("--base-url")
    p.add_argument("--api-key-env", help="NAME of the environment variable holding the key (never the key itself)")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--stage", action="append", default=[], metavar="STAGE=PROVIDER",
                   help="use another provider for one stage, e.g. --stage critique=claude")
    p.add_argument("--runs-dir")
    p.add_argument("--from", dest="from_stage", choices=C.STAGES)
    p.add_argument("--until", choices=C.STAGES)
    p.add_argument("--no-build", action="store_true", help="stop after critique-quality text: skip build/gate/fix")
    p.add_argument("--build", action="store_true", help="build even with the fake provider")
    p.add_argument("--no-vision", action="store_true", help="gate review without sending frames to the model")
    p.add_argument("--fix-rounds", type=int)
    p.add_argument("--lint-mode", choices=["auto", "strict", "shadow"])


def _brief_flags(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("brief (the owner's production constraints: instructions for every writing stage)")
    g.add_argument("--minutes", help="target length in minutes, e.g. 4-5")
    g.add_argument("--aspect", choices=["16:9", "9:16", "4:3", "1:1"])
    g.add_argument("--kicker", help="series kicker on the title sting and the end card")
    g.add_argument("--voice", help="meta.voice")
    g.add_argument("--end-narration", help="end-card narration, word for word (default: the cached sign-off)")
    g.add_argument("--ask", help="the end card's one question for the comments")
    g.add_argument("--ask-hint", help="the end card's hint line (e.g. three other frameworks, ' · ' separated)")
    g.add_argument("--keep", action="append", default=[], metavar="NOTE",
                   help="a must-keep note from the owner (repeatable)")


def _brief(a) -> dict:
    return C.normalize_brief({"target_minutes": a.minutes, "aspect": a.aspect, "kicker": a.kicker, "voice": a.voice,
                              "end_narration": a.end_narration, "end_ask": a.ask, "end_ask_hint": a.ask_hint,
                              "must_keep": a.keep})


def _cfg(a) -> C.Config:
    stage = {}
    for s in a.stage:
        k, _, v = s.partition("=")
        if k not in C.STAGES or not v:
            raise SystemExit(f"--stage expects STAGE=PROVIDER with STAGE in {C.STAGES}: {s!r}")
        stage[k] = v
    cli = {k: v for k, v in {"provider": a.provider, "model": a.model, "base_url": a.base_url,
                             "api_key_env": a.api_key_env, "effort": a.effort, "stage": stage}.items() if v}
    cfg = C.load(a.config, cli)
    if a.runs_dir:
        cfg.defaults["runs_dir"] = a.runs_dir
    if a.no_build:
        cfg.defaults["build"] = False
    if a.no_vision:
        cfg.defaults["vision_review"] = False
    if a.fix_rounds is not None:
        cfg.defaults["fix_rounds"] = a.fix_rounds
    if a.lint_mode:
        cfg.defaults["lint_mode"] = a.lint_mode
    if not a.build and all(cfg.stage_spec(s).get("type") == "fake" for s in C.MODEL_STAGES):
        cfg.defaults["build"] = False  # a dry run never renders
    return cfg


def _run_dir(ref: str, cfg: C.Config) -> Path:
    p = Path(ref)
    if (p / "run.json").exists():
        return p
    q = Path(cfg.get("runs_dir")) / ref
    if (q / "run.json").exists():
        return q
    raise SystemExit(f"no run found at {p} or {q}")


def _drive(p: Pipeline, a) -> int:
    try:
        p.run(from_stage=a.from_stage, until=a.until)
    except StageError as e:
        print(f"\nstopped: {e}", file=sys.stderr)
        print(f"fix the cause (or edit the stage's JSON in {p.dir}), then: python -m vfactory.agent resume {p.dir}"
              + (f" --from {e.stage}" if e.stage else ""), file=sys.stderr)
        return 2
    except ProviderError as e:
        print(f"\nprovider error: {e}", file=sys.stderr)
        return 2
    _print_status(p)
    return 0


def _print_status(p: Pipeline) -> None:
    print(f"\nrun: {p.dir}")
    for s in C.STAGES:
        st = p.state.get("stages", {}).get(s, {})
        who = f"{st.get('provider', '')} {st.get('model', '')}".strip()
        print(f"  {s:9s} {st.get('status', '-'):8s} {('tries ' + str(st['attempts'])) if st.get('attempts') else '':9s} {who}")
    if (p.dir / "lesson.json").exists():
        print(f"lesson: {p.dir / 'lesson.json'}   approval view: {p.dir / 'script.md'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m vfactory.agent", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="start (or continue) an episode from a topic")
    r.add_argument("topic")
    r.add_argument("--story-hint", default="")
    r.add_argument("--series")
    r.add_argument("--slug")
    _provider_flags(r)
    _brief_flags(r)
    s = sub.add_parser("resume", help="continue a run where it stopped")
    s.add_argument("run")
    _provider_flags(s)
    _brief_flags(s)
    st = sub.add_parser("status")
    st.add_argument("run")
    st.add_argument("--config")
    st.add_argument("--runs-dir")
    pv = sub.add_parser("providers", help="list configured providers and check that they answer (no tokens spent)")
    pv.add_argument("--config")
    pv.add_argument("--no-network", action="store_true")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "providers":
            return _providers(a)
        if a.cmd == "status":
            cfg = C.load(a.config)
            if a.runs_dir:
                cfg.defaults["runs_dir"] = a.runs_dir
            _print_status(Pipeline(_run_dir(a.run, cfg), cfg))
            return 0
        cfg = _cfg(a)
        if a.cmd == "run":
            p = Pipeline.create(a.topic, cfg, story_hint=a.story_hint, slug=a.slug, series=a.series, brief=_brief(a))
        else:
            p = Pipeline(_run_dir(a.run, cfg), cfg)
            if _brief(a):
                p.set_brief(_brief(a))
        print(f"run directory: {p.dir}")
        return _drive(p, a)
    except ProviderError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def _providers(a) -> int:
    cfg = C.load(a.config)
    print(f"config: {cfg.source or '(none: defaults)'}")
    names = list(cfg.providers) or []
    seen = set()
    rows = []
    for n in names + [cfg.get("provider")]:
        if n in seen:
            continue
        seen.add(n)
        try:
            spec = cfg._resolve(n)
            prov = C.make_provider(spec)
            chk = prov.check(network=not a.no_network)
            rows.append((n, spec.get("type"), prov.model, spec.get("base_url", ""), chk["ok"], chk["detail"]))
        except ProviderError as e:
            rows.append((n, "?", "", "", False, str(e)))
    for n, t, m, u, ok, d in rows:
        print(f"  {'OK ' if ok else 'NO '} {n:12s} {t:9s} {m:24s} {u}\n        {d}")
    print("\nstage → provider:")
    for s in C.MODEL_STAGES:
        try:
            spec = cfg.stage_spec(s)
            extra = f" effort={spec['effort']}" if spec.get("effort") else ""
            print(f"  {s:9s} {spec.get('label', spec.get('type'))} {spec.get('model') or ''}{extra}")
        except ProviderError as e:
            print(f"  {s:9s} ERROR {e}")
    print("\npresets (OpenAI-compatible): " + json.dumps({k: v[0] for k, v in PRESETS.items()}, indent=1))
    return 0 if all(r[4] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
