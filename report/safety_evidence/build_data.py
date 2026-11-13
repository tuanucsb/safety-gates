"""Build the data files behind the dashboard "Do monitors catch unsafe engineering approvals?".

Every figure on that page is read from one of these files, and every file is extracted from
results/r02/calibration.json (python -m engsafe.calibrate) and the task registry. Run this after the calibration
changes, then replace the attached files in the dashboard's Sources panel, or ask Claude to republish them.

Counts are given by run and by distinct case: every unsafe case was run many times, so runs are not independent
trials. The interval on the transcript-only monitor is resampled by task for the same reason.

Usage (from the repository root):
  python report/safety_evidence/build_data.py
Writes report/safety_evidence/data/*.json. The page itself is report/safety_evidence/index.html.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from engsafe.tasks import SUITES, VARIANTS  # noqa: E402

LAB = {"haiku-transcript": "Haiku, transcript only", "haiku-grounded": "Haiku, with documents",
       "sonnet-grounded": "Sonnet, with documents", "rule": "Rule checker"}
LLM = ("haiku-transcript", "haiku-grounded", "sonnet-grounded")
CAL = "results/r02/calibration.json"


def build(c: dict) -> dict[str, list[dict]]:
    et = c["event_tree"]
    units, pairs, rt, rt_cases, q2 = (et["q1_units"], et["pressure_pairs"], et["q1_redteam"],
                                      et["q1_redteam_by_case"], et["q2_budget2"])
    opus, haiku = "claude-opus-5-5", "claude-haiku-5-5"
    sm = c["pairs"]["budget2"]["haiku-transcript|sonnet-grounded"]["all"]
    fa = c["false_alarm_anatomy"]["sonnet-grounded"]["sdk_all"]

    def row(i, stage, condition, events=None, runs=None, distinct_cases=None, **extra):
        return {"id": i, "stage": stage, "condition": condition, "events": events, "runs": runs,
                "distinct_cases": distinct_cases, "source": CAL, **extra}

    evidence = [
        row("honest", "agent", "Honest agent: unsafe case approved", units["runs"]["k"], units["runs"]["n"],
            units["by_case"]["n"], tasks=units["by_task"]["n"],
            bound_by_case_pct=round(100 * units["by_case"]["hi"])),
        row("pressure", "agent", "Schedule and cost note added: decision flipped", pairs["flips"], pairs["pairs"],
            pairs["tasks"]),
        row("told_opus", "agent", "Told openly to get it approved, Opus 5.5: complied", rt[opus]["k"], rt[opus]["n"],
            rt_cases[opus]["n"]),
        row("told_haiku", "agent", "Told openly to get it approved, Haiku 5.5: complied", rt[haiku]["k"],
            rt[haiku]["n"], rt_cases[haiku]["n"]),
        row("confessed", "note", "Red-team approvals disclosed by the agent itself", rt[opus]["k"], rt[opus]["k"],
            source="results/control/redteam/episodes.jsonl"),
        row("monitor_rule", "monitor", "Deterministic limit check on reported numbers: wrong approvals escaped",
            q2["rule"]["escaped_all"]["k"], q2["rule"]["escaped_all"]["n"]),
        row("shared_misses", "note", "Transcript-only monitor's misses shared by a monitor with documents",
            sm["both"], sm["a_fail"]),
        row("contradictions", "note",
            "Sonnet monitor false alarms on the SDK harness whose reasoning endorses the approval",
            fa["reasoning_concludes_safe"], fa["flagged"]),
        row("models", "setup", "Models run as honest agents", count=len({a["model"] for a in c["agents"].values()}),
            source="results/*/RUN.md"),
        row("tasks", "setup", "Decision tasks in the battery the agents ran", count=len(SUITES["r0"]),
            source="engsafe/tasks, suite r0"),
        row("variants", "setup", "Variants of each task", count=len(VARIANTS), source="engsafe/tasks/base.py"),
        row("new_tasks", "setup", "Harder tasks built and not yet run", count=len(SUITES["r02-new"]),
            source="engsafe/tasks, suite r02-new"),
    ]
    curves, points = [], []
    for m in LLM:
        mon = c["monitors"][m]
        for key, name in (("cli_pilot_read", "read"), ("cli_pilot_skip", "never opened")):
            best: dict[float, float] = {}
            for r in mon["sweep"][key]:  # at each false-alarm rate keep the best catch (the upper envelope)
                if r["fa"] is not None:
                    x = round(100 * r["fa"], 2)
                    best[x] = max(round(100 * r["catch"], 1), best.get(x, 0))
            curves += [{"monitor": LAB[m], "hazard_document": name, "false_alarm_pct": x, "caught_pct": y}
                       for x, y in sorted(best.items())]
        b2, cur, cc = mon["budget"]["cli_pilot"]["0.02"], mon["budget"]["cli_current"]["0.02"], \
            mon["catch_cost"]["sim_all"]["0.99"]
        cl = mon["clustered"]
        points.append({
            "monitor": LAB[m], "false_alarm_budget_pct": 2, "threshold": b2["threshold"],
            "caught_read": b2["sim_read"]["k"], "wrong_read": b2["sim_read"]["n"],
            "caught_unread": b2["sim_skip"]["k"], "wrong_unread": b2["sim_skip"]["n"],
            # interval with the task as the unit, threshold set again in every resample
            "unread_low_pct": round(100 * cl["sim_skip"]["joint"][0]),
            "unread_high_pct": round(100 * cl["sim_skip"]["joint"][1]), "resamples": cl["sim_skip"]["n_boot"],
            "tasks_all_caught": cl["skip_by_task"]["all_caught"], "tasks_none_caught": cl["skip_by_task"]["none_caught"],
            "tasks_mixed": cl["skip_by_task"]["mixed"],
            # the same budget on safe approvals with the two corrected tasks swapped in
            "threshold_corrected": cur["threshold"], "caught_unread_corrected": cur["sim_skip"]["k"],
            "catch_target_pct": 99, "false_alarms_at_target": cc["cli_pilot"]["k"],
            "safe_approvals": cc["cli_pilot"]["n"], "false_alarm_pct_at_target": round(100 * cc["cli_pilot"]["p"])})
    harness = []
    for m in ("rule", *LLM):
        d, tr = c["monitors"][m]["default"], c["monitors"][m].get("transfer", {}).get("0.02", {})
        for name, key, tkey in (("CLI", "cli_pilot", "t_cli"), ("SDK", "sdk_all", "t_sdk")):
            v = d[key]
            harness.append({"monitor": LAB[m], "harness": name, "flagged": v["k"], "safe_approvals": v["n"],
                            "flagged_pct": round(100 * v["p"], 1), "low_pct": round(100 * v["lo"], 1),
                            "high_pct": round(100 * v["hi"], 1), "threshold_at_budget": tr.get(tkey)})
    shared = []
    for a, b, name in (("haiku-transcript", "haiku-grounded", "Haiku transcript-only and Haiku with documents"),
                       ("haiku-transcript", "sonnet-grounded", "Haiku transcript-only and Sonnet with documents"),
                       ("haiku-grounded", "sonnet-grounded", "Haiku with documents and Sonnet with documents")):
        r = c["pairs"]["default"][f"{a}|{b}"]
        for hname, key in (("CLI", "fa_cli_pilot"), ("SDK", "fa_sdk_all")):
            v = r[key]
            shared.append({"pair": name, "harness": hname, "first_false_alarms": v["a_fail"], "shared": v["both"],
                           "shared_pct": round(100 * v["both"] / v["a_fail"], 1), "kappa": round(v["kappa"], 2)})
    return {"evidence": evidence, "catch_curves": curves, "monitor_points": points,
            "false_alarms_by_harness": harness, "shared_false_alarms": shared}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calibration", default=str(HERE.parents[1] / "results" / "r02" / "calibration.json"))
    ap.add_argument("--out", default=str(HERE / "data"))
    args = ap.parse_args(argv)
    tables = build(json.loads(Path(args.calibration).read_text()))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        (out / f"{name}.json").write_text(json.dumps(rows, indent=1))
        print(f"{name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
