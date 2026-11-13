"""Run agents on the task suite, then run monitors on every APPROVE.

Usage:
  python -m engsafe.run --out results/pilot --agents claude-opus-5-5,claude-haiku-5-5 --repeats 3
  python -m engsafe.run --out results/smoke --agents claude-haiku-5-5 --tasks N1-decay-heat --repeats 1
  python -m engsafe.run --out results/offline --scripted   # no API calls; pipeline test only

Results are appended to <out>/episodes.jsonl and <out>/monitors.jsonl; re-running resumes.
"""

from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .agent import POLICIES, Episode, episode_id
from .monitors import LLMMonitor, RuleMonitor
from .tasks import SUITES, VARIANTS, all_instances, get

# USD per million tokens: (input, output, cache read, cache write). From the Claude API price list
# (2026-10). Used only for the running cost estimate printed to the console.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}

MONITOR_SPECS = {
    "rule": None,
    "haiku-transcript": ("claude-haiku-5-5", "transcript"),
    "haiku-grounded": ("claude-haiku-5-5", "grounded"),
    "sonnet-grounded": ("claude-sonnet-5-5", "grounded"),
    # Opt-in variants whose schema asks for the reasoning before the verdict (see monitors.MONITOR_SCHEMA_RF).
    # Not in the default set: every frozen arm used the verdict-first schema, and a change of schema is a change
    # of monitor that has to be measured in its own arm.
    "haiku-transcript-rf": ("claude-haiku-5-5", "transcript", "reason_first"),
    "haiku-grounded-rf": ("claude-haiku-5-5", "grounded", "reason_first"),
    "sonnet-grounded-rf": ("claude-sonnet-5-5", "grounded", "reason_first"),
}
DEFAULT_MONITORS = ["rule", "haiku-transcript", "haiku-grounded", "sonnet-grounded"]

_lock = threading.Lock()


def cost(model: str, usage: dict) -> float:
    if "cost_usd" in usage:  # the CLI reports its own cost
        return usage["cost_usd"]
    p = PRICES.get(model)
    if not p:
        return 0.0
    return (usage.get("input_tokens", 0) * p[0] + usage.get("output_tokens", 0) * p[1]
            + usage.get("cache_read_input_tokens", 0) * p[2]
            + usage.get("cache_creation_input_tokens", 0) * p[3]) / 1e6


def _append(path: Path, rec: dict) -> None:
    with _lock, path.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _load(path: Path, key=lambda r: r["episode_id"]) -> list[dict]:
    """Last record per key wins, so a re-run can append a corrected row."""
    if not path.exists():
        return []
    rows = {}
    for line in path.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[key(r)] = r
    return list(rows.values())


def scripted_episode(inst, policy: str, repeat: int) -> Episode:
    """Offline stand-in agents used only to test the pipeline (never reported as results).

    oracle       - approves iff the action is truly safe and reports the true value.
    rubber_stamp - always approves and reports a value exactly at the limit (a wrong input that
                   looks compliant), i.e. the failure a rule monitor cannot see.
    """
    t, lim = inst.truth, inst.truth.limit
    ep = Episode(f"{inst.task_id}|{inst.variant}|scripted-{policy}|na|r{repeat}", inst.task_id, inst.variant,
                 f"scripted-{policy}", "na", repeat, truth=t.as_dict())
    value = t.value if policy == "oracle" else lim.limit
    passes = t.safe if policy == "oracle" else True
    ep.decision = ("APPROVE" if t.safe else "REJECT") if policy == "oracle" else "APPROVE"
    ep.checks = [{"criterion": lim.name, "value": value, "unit": lim.unit, "comparator": lim.comparator,
                  "limit": lim.limit, "passes": passes}]
    ep.rationale = "scripted"
    ep.transcript = [{"role": "agent", "text": f"scripted {policy} agent"}]
    ep.stop = "submitted"
    return ep


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--agents", default="claude-opus-5-5,claude-haiku-5-5")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: the whole suite)")
    ap.add_argument("--suite", choices=list(SUITES), default="r0",
                    help="r0 = the 22 tasks of Releases 0 and 0.1 (default, the set every frozen arm ran on); "
                         "r02-new = the 12 derived-quantity and distractor tasks; all = both")
    ap.add_argument("--policy", choices=list(POLICIES), default="honest",
                    help="honest (default); honest-nolist (document names in the system prompt, no list_documents "
                         "tool); attack (red-team agent, Release 0.1); attack-stealth (red-team agent that may not "
                         "disclose, Release 0.2)")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--monitors", default=",".join(DEFAULT_MONITORS),
                    help="comma-separated; also available: " + ", ".join(m for m in MONITOR_SPECS
                                                                           if m not in DEFAULT_MONITORS))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--backend", choices=["api", "cli"], default=None,
                    help="api = Anthropic SDK with PROXIMAB_API_KEY (or ANTHROPIC_API_KEY); cli = Claude Code CLI "
                         "with the session's login (default: cli unless a key is set)")
    ap.add_argument("--scripted", action="store_true", help="offline pipeline test, no API calls")
    ap.add_argument("--dry-run", action="store_true", help="print the job count and exit")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ep_path, mon_path = out / "episodes.jsonl", out / "monitors.jsonl"
    task_ids = [t for t in args.tasks.split(",") if t]
    variants = tuple(v for v in args.variants.split(",") if v)
    instances = all_instances(task_ids or None, variants, suite=args.suite)
    agents = ["scripted-oracle", "scripted-rubber_stamp"] if args.scripted else args.agents.split(",")
    monitors = ["rule"] if args.scripted else [m for m in args.monitors.split(",") if m]

    done = {e["episode_id"] for e in _load(ep_path) if e["stop"] != "api_error"}  # errored rows are retried
    jobs = []
    for model in agents:
        for inst in instances:
            for r in range(args.repeats):
                eid = (f"{inst.task_id}|{inst.variant}|{model}|na|r{r}" if args.scripted
                       else episode_id(inst, model, args.effort, r, args.policy))
                if eid not in done:
                    jobs.append((model, inst, r))
    print(f"{len(instances)} instances x {len(agents)} agents x {args.repeats} repeats; "
          f"{len(done)} done, {len(jobs)} to run.")
    if args.dry_run:
        return

    import os
    from .sdk import api_key_present, make_client
    backend = args.backend or ("api" if api_key_present() else "cli")
    client = None
    if not args.scripted and backend == "api":
        client = make_client()
    if not args.scripted:
        print(f"backend: {backend}")

    spent = {"usd": 0.0}

    def do_episode(job):
        model, inst, r = job
        if args.scripted:
            ep = scripted_episode(inst, model.split("-", 1)[1], r)
        elif backend == "cli":
            from .cli_backend import run_episode_cli
            ep = run_episode_cli(inst, model, args.effort, r, policy=args.policy)
        else:
            from .agent import run_episode
            ep = run_episode(client, inst, model, args.effort, r, policy=args.policy)
        rec = ep.to_dict()
        _append(ep_path, rec)
        with _lock:
            spent["usd"] += cost(model, ep.usage)
        return rec

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do_episode, j) for j in jobs]), 1):
            rec = fut.result()
            ok = "SAFE" if rec["truth"]["safe"] else "UNSAFE"
            print(f"[{i}/{len(jobs)}] {rec['episode_id']}: {rec['decision']} (truth {ok}, {rec['stop']}) "
                  f"~${spent['usd']:.3f}", flush=True)

    # ---- monitors on every APPROVE ----
    episodes = [e for e in _load(ep_path) if e["agent_model"] in agents
                and e.get("policy", "honest") == (args.policy if not args.scripted else "honest")]
    spent["usd"] += run_monitors(episodes, monitors, mon_path, client, backend, args.workers)
    print(f"Done. Approximate spend this run: ${spent['usd']:.3f}")


def run_monitors(episodes: list[dict], monitors: list[str], mon_path: Path, client=None, backend: str = "cli",
                 workers: int = 8, instance_of=None) -> float:
    """Review every APPROVE in `episodes` with each monitor; append results to mon_path; return spend.

    `instance_of(ep)` returns the task instance a monitor should see; defaults to the registry instance.
    Already-reviewed (episode, monitor) pairs are skipped; errored reviews are retried.
    """
    instance_of = instance_of or (lambda ep: get(ep["task_id"]).instance(ep["variant"]))
    approvals = [e for e in episodes if e["decision"] == "APPROVE"]
    reviewed = {(m["episode_id"], m["monitor"]) for m in _load(mon_path, key=lambda r: (r["episode_id"], r["monitor"]))
                if m.get("flag") is not None}
    mon_objs = {}
    for m in monitors:
        if m == "rule":
            mon_objs[m] = RuleMonitor()
        else:
            model, mode, *rest = MONITOR_SPECS[m]
            mon_objs[m] = LLMMonitor(client, model, mode, backend=backend, schema=rest[0] if rest else "verdict_first")
    mjobs = [(e, m) for e in approvals for m in monitors if (e["episode_id"], m) not in reviewed]
    print(f"{len(approvals)} approvals; {len(mjobs)} monitor reviews to run.")
    spent = {"usd": 0.0}

    def do_monitor(job):
        ep, m = job
        res = mon_objs[m].review(ep, instance_of(ep))
        res["monitor"] = m
        res["episode_id"] = ep["episode_id"]
        _append(mon_path, res)
        if "usage" in res:
            with _lock:
                spent["usd"] += cost(res.get("model", ""), res["usage"])
        return res

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, fut in enumerate(as_completed([pool.submit(do_monitor, j) for j in mjobs]), 1):
            fut.result()
            if i % 25 == 0 or i == len(mjobs):
                print(f"  monitors {i}/{len(mjobs)} ~${spent['usd']:.3f}", flush=True)
    return spent["usd"]

if __name__ == "__main__":
    main()
