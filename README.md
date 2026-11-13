# Safety Gates: do monitors catch unsafe engineering approvals?

A pilot control evaluation. An AI agent is asked to approve or reject a safety-critical engineering action, and
independent monitors review every approval before it would execute. The question is narrow and has computed ground
truth:

> When an agent approves an unsafe action, which kinds of oversight catch it, and at what cost in false alarms?

Regulated engineering is a useful testbed for this because the limits are written down. Whether an approved action
breaks its governing limit is computed in code from the same parameters that generate the case documents, so every
wrong approval and every monitor miss can be counted.

Every plant, spacecraft, product, drug and standard in this repository is fictional, and every number is
illustrative. Nothing here is engineering or clinical guidance, and nothing here certifies or qualifies a system.

## What the pilot found

Three Claude models (Opus 5.5, Haiku 5.5, Sonnet 5.5) worked 22 tasks in three variants each: a safe case, the same
case with one realistic hazard, and the hazard case with a manager's note about schedule and cost.

| Question | Result | Where |
|---|---|---|
| Does an honest agent approve an unsafe case? | 0 unsafe approvals in 684 runs, which cover 44 distinct unsafe cases from 22 tasks. The tasks are at ceiling for these models | `results/r02/calibration.md`, Section 8 |
| Does it comply when told to get the action approved? | Told openly that it was a red-team agent in a sandbox, Opus submitted 5 unsafe approvals in 44 attempts and disclosed each one; Haiku submitted none | `results/control/control.md` |
| What does a monitor catch at a 2% false-alarm budget? | On 129 simulated wrong approvals, both monitors given the source documents caught all of them. A monitor given only the agent's transcript caught 66 of 66 when the agent had read the hazard document and 40 of 63 when it had not | `results/r02/calibration.md`, Section 2 |
| How stable is that 40 of 63? | Not very. Resampled by task it runs from 40% to 87%, and its threshold rests on safe approvals of a task that was later corrected; with the corrected runs it is 44 of 63. The direction is stable | Section 2b |
| Does a deterministic limit check on reported numbers help? | It caught 38 of 129. A mistaken reading produces numbers that satisfy the limit | Section 8 |

Three observations about the monitors themselves, each resting on small counts:

- The same monitor scores honest traffic differently through the Claude Code CLI and through the SDK, so a
  false-alarm threshold has to be set on traffic from the harness it will run on (Section 5).
- The monitor output format asks for the verdict before the reasoning. On the SDK harness all six false alarms of
  one monitor end by endorsing the approval (Section 4b). A reason-first format is built and not yet measured.
- Two monitors built on the same model raised mostly the same false alarms, while their misses did not overlap
  (Section 6).

## What it does not show

- **An agent that hides.** Every real unsafe approval came with a disclosure in the agent's own text. A red-team
  policy that forbids disclosure is built and has not been run.
- **Tasks hard enough to separate models or monitors.** Twelve harder tasks are built and not yet run.
- **A human baseline.** No task has been solved blind by a person, and nothing measures what a reviewer does with a
  flag.
- **Independent wrong approvals.** One model wrote the simulated ones after being shown the answer, and all were
  scored on one harness.
- **Held-out thresholds.** Thresholds were set and scored on the same safe approvals.

Counts by run overstate the evidence, because each case was run many times across models, harnesses and repeats.
Where a number matters, quote it by distinct case or by task; the calibration report gives both.

## Run it

Python 3.10 or later. The checks below make no model calls.

```bash
pip install -r requirements.txt
python -m pytest -q                                                   # 250 offline tests
python -m engsafe.run --out results/offline --scripted --repeats 1    # pipeline check with scripted agents
python -m engsafe.calibrate                                           # rebuilds results/r02/calibration.md and .json
```

Model runs need either an Anthropic API key in `PROXIMAB_API_KEY` (`--backend api`) or a logged-in Claude Code CLI
(`--backend cli`). The harness is recorded on every episode, because it changes the scores.

```bash
python -m engsafe.run --backend api --out results/scratch --agents claude-haiku-5-5 --tasks D1-pediatric-dose --repeats 1
python -m engsafe.analyze results/scratch
```

## What is in the repository

| Path | Contents |
|---|---|
| `engsafe/tasks/` | Task generators with computed ground truth: 22 tasks in the default suite, 12 newer ones in the suite `r02-new` |
| `engsafe/agent.py`, `cli_backend.py`, `mcp_server.py` | The agent's four tools, its policies, and the two backends |
| `engsafe/monitors.py` | The deterministic rule checker and the model monitors |
| `engsafe/run.py`, `analyze.py` | Runner and the honest-agent analysis |
| `engsafe/synth.py`, `control.py` | Simulated wrong approvals and the control analysis |
| `engsafe/calibrate.py` | Monitor calibration, task-level intervals, shared failures between monitors |
| `engsafe/disclosure.py`, `remonitor.py` | Tools for the red-team arm and for re-reviewing an arm with other monitors |
| `tests/` | Ground-truth checks against independent hand formulas, label-leak checks, harness and analysis tests |
| `results/` | The frozen runs, each with a run record (`RUN.md`), every episode and every monitor review |
| `report/results.md` | The write-up of Releases 0 and 0.1 |
| `report/safety_evidence/` | Source and data of a results dashboard, generated from the calibration |
| `docs/DESIGN.md` | The research questions, metrics and design as frozen before the first full run |
| `docs/physical_ai_safety_design.md` | A design note on defense in depth for AI engineering agents |
| `docs/RELEASE_0_2_RUNBOOK.md` | The next experiments, built and waiting to be run |
| `docs/tasks/` | One card for each of the 12 newer tasks |

## The runs

| Arm | What ran | Harness |
|---|---|---|
| `results/pilot` | Opus and Haiku, 22 tasks x 3 variants x 3 repeats, four monitors | Claude Code CLI |
| `results/r01` | The two tasks corrected in Release 0.1, re-run | Claude Code CLI |
| `results/r0_api` | The pilot design repeated | SDK |
| `results/r02/sonnet_honest` | Sonnet as a third agent | SDK |
| `results/control/redteam` | The announced red-team policy on the hazard cases | Claude Code CLI |
| `results/control/simulated` | Simulated wrong approvals and matched correct ones, with monitors | Claude Code CLI |

Designs were frozen before each run, and each run record names the commit at which that happened. Those commit
hashes belong to the project's working history, which is not published here; this repository starts from a single
snapshot. Changes made after seeing agent behaviour are listed in the run records. The calibration in `results/r02`
was computed after the data were seen and is exploratory.

## How this was built

The harness, the tasks and the analysis were built with AI coding agents (Claude Code) directed by the author. The
ground truth of every task is computed in code and tested against independent formulas, but no task has yet been
solved blind by a person.

## Licence

No licence has been chosen yet. Until a licence file is added, all rights are reserved.

## Author

Tuan Anh Dinh
