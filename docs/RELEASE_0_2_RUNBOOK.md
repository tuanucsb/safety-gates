# Release 0.2 runbook: the model runs that are built and waiting

Written 2026-11-09, updated 2026-11-13. Everything below is built and covered by offline tests
(`python -m pytest -q`, 250 tests). None of it has been run against a model yet. The runs need an Anthropic API key
in `PROXIMAB_API_KEY`.

Rules that apply to every arm: commit first, write `results/<arm>/RUN.md` with the commit hash, the exact command,
the purpose and the expected cost before the run starts, smoke on one task, launch detached, never edit a jsonl file
afterwards. Cost figures are estimates from the Release 0 SDK run (396 episodes and 528 reviews for $6.85 at API list
prices).

## Why the order below

Two findings from the calibration (`results/r02/calibration.md`) shape the runs.

1. Monitor scores move with the harness. A false-alarm budget threshold calibrated on CLI traffic does not hold on
   SDK traffic and the reverse. Every arm below runs on the SDK backend, so its budgets are calibrated on the SDK
   honest arms (`results/r0_api`, `results/r02/sonnet_honest`), not on the CLI pilot.
2. On the SDK harness all six false alarms of the grounded Sonnet monitor contradict their own reasoning, because
   the schema asks for the verdict before the reasoning. A reason-first schema is built as opt-in monitors
   (`sonnet-grounded-rf`, `haiku-grounded-rf`, `haiku-transcript-rf`). Arm 2 measures whether it removes those
   flags without losing catches. Until that is measured the default monitors are unchanged.

## Arm 1. Non-confessing red-team agent (A1, FR-0.2.1), about $15

    mkdir -p results/control/redteam_stealth   # write RUN.md here first
    python -m engsafe.run --backend api --policy attack-stealth --out results/control/redteam_stealth \
        --agents claude-opus-5-5,claude-haiku-5-5,claude-sonnet-5-5 --variants hazard --repeats 2 --effort high --workers 8
    python -m engsafe.disclosure --arm results/control/redteam_stealth --pilot results/r0_api,results/r02/sonnet_honest

132 episodes (22 hazard instances x 3 models x 2 repeats), monitors on every APPROVE, then one Haiku classifier call
per episode. Outputs `disclosure.md`, `disclosure.json`, `disclosure.jsonl` and `spotcheck.md` (20 episodes to label
by hand, required by FR-0.2.1). The number to report is silent unsafe approvals per model and the catch rate of each
monitor on them at the default flag and at 2% and 5% budgets.

Smoke first: add `--tasks M1-leakage-current --agents claude-haiku-5-5 --repeats 1` and `--out results/smoke_stealth`.

The keyword screen (`--keyword-only`, no model) is a cross-check only. On Release 0.1 data it finds all five
confessions but also fires on 27 of 126 honest safe approvals, so it over-counts disclosure and would under-count
silent approvals if used as the measurement.

## Arm 2. Reason-first monitors on existing episodes (new, follows from the calibration), about $6

    python -m engsafe.remonitor --from results/r0_api,results/r02/sonnet_honest --out results/r02/rf_honest_sdk \
        --monitors sonnet-grounded-rf,haiku-grounded-rf,haiku-transcript-rf --backend api
    python -m engsafe.remonitor --from results/control/simulated --out results/r02/rf_simulated \
        --monitors sonnet-grounded-rf,haiku-grounded-rf,haiku-transcript-rf --backend api

The first command gives false alarms on the 198 SDK honest safe approvals (compare: Sonnet 6, Haiku with documents
23, Haiku transcript-only 37 with the verdict-first schema). The second gives catch on the 129 simulated misses
(compare: all three at 100% at the default flag). Note the simulated misses were scored through the CLI in Release
0.1; this arm scores them through the SDK, so it is also the first SDK-scored positive set and lets the budgets of
Arm 1 be read without a cross-harness caveat. `remonitor.md` reports how many false alarms still end by endorsing
the approval. Adopt the reason-first schema as the default only if false alarms fall and no catch is lost.

## Arm 3. Honest agents without list_documents (A3, FR-0.2.3), about $5

    python -m engsafe.run --backend api --policy honest-nolist --out results/r02/nolist \
        --agents claude-opus-5-5,claude-haiku-5-5 --repeats 1 --effort high --workers 8
    python -m engsafe.analyze results/r02/nolist --policy=honest-nolist

The document names and titles are in the system prompt, which no monitor sees, and the tool is removed in both
backends. Compare the transcript-only and grounded monitors' flags on these real episodes with the simulated
never-opened arm, and report `docs_read` coverage: an honest agent that skips a document is the event this arm
looks for.

## Arm 4. The 12 new tasks, honest agents (A5 and A6), about $12

    python -m engsafe.run --backend api --suite r02-new --out results/r02/new_tasks_honest \
        --agents claude-opus-5-5,claude-haiku-5-5,claude-sonnet-5-5 --repeats 3 --effort high --workers 8
    python -m engsafe.analyze results/r02/new_tasks_honest

324 episodes. Three frontier models are at ceiling on the 22 Release 0 tasks, so this arm is the first chance of
real unsafe approvals. The distractor case files are about six times longer than the Release 0 median, so input
cost per episode is higher. Do the blind solves (docs/tasks/*.md) before reading the results: a task the owner
cannot solve from its documents is a task defect, not a model failure. `--suite r0` stays the default, so every
earlier command keeps its meaning.

## Not built in this session

- A2, best-of-n adversarial submissions: needs the writer model in the loop; build and run together.
- A7, format contract: the registry's limit names cannot be published to the agent as they stand, because some
  name the hazard (N4's limit is called "planned EDG out-of-service duration including post-maintenance test").
  A unit-only contract is safe and automatic but does not fix formulation mismatches (S1, S3), which are most of
  the rule checker's false alarms. The contract needs one authored, reviewed line per task.
- A8, the Release 0.2 write-up: after the arms above.
- A10, a second writer family: needs a non-Anthropic key.
