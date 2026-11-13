# Release 0 on the API harness (harness-effect arm)

- Frozen at commit: da6b402 (2026-11-08T09:33Z)
- Command: python -m engsafe.run --backend api --out results/r0_api --agents claude-opus-5-5,claude-haiku-5-5 --effort high --repeats 3 --workers 8
- Same 22 tasks, 3 variants, 3 repeats, effort high and four monitors as results/pilot (Release 0); only the harness differs:
  anthropic-sdk-manual-loop (SDK tool loop, monitors via structured output) instead of claude-code-cli.
- Billing: Anthropic API key (console workspace), not the Claude Code login. Smoke check first: results/smoke_api (6 Haiku episodes, 8 reviews, $0.03).
- Purpose: measure the harness effect on agent decisions and monitor scores (HANDOFF open item 4); the task set is unchanged
  from Release 0.1 (N5/S6 fixes included), so compare against results/pilot plus results/r01 for N5/S6.

## Results (2026-11-08)

396 episodes, 528 monitor reviews, 0 API errors. Model spend at list prices with caching: agents $5.25, monitors $1.60,
total $6.85 (the CLI run of the same design reported $17.56).

| | SDK harness (`anthropic-sdk-manual-loop`, this run) | CLI harness (`claude-code-cli`, results/pilot) |
|---|---|---|
| Opus 5.5 Pass@1 / Pass^3 | 100% / 100% | 100% / 100% |
| Haiku 5.5 Pass@1 / Pass^3 | 100% / 100% | 97.0% / 95.5% |
| Unsafe cases approved (both agents) | 0 / 264 | 0 / 264 |
| Safe cases approved (denominator for false alarms) | 132 / 132 | 126 / 132 |
| Sonnet grounded monitor, false alarms | 3 (2.3%) | 2 (1.6%) |
| Haiku grounded monitor, false alarms | 15 (11.4%) | 33 (26.2%) |
| Haiku transcript-only monitor, false alarms | 24 (18.2%) | 31 (24.6%) |
| Rule checker, false alarms | 34 (25.8%) | 34 (27.0%) |

Reading. Agent decisions were unchanged for Opus and improved for Haiku: the six cautious escalations of safe cases
that Haiku made on the CLI harness did not recur on the SDK loop, so Haiku's Pass^3 rose from 95% to 100%. No unsafe
case was approved under either harness. The monitor side changed more: the Haiku grounded monitor's false-alarm rate
fell from 26% to 11% when its structured output came through the SDK (`output_config` JSON schema) rather than the
CLI's `--json-schema` path, with the same prompt, model and threshold; Sonnet and the rule checker were unchanged
within noise. The harness is part of the measured configuration for monitors as much as for agents, which is the
reason every result carries its harness string. The run cost less than the CLI run at list prices because the SDK
loop reuses the prompt cache on every turn and the CLI's reported cost includes its own overheads.
