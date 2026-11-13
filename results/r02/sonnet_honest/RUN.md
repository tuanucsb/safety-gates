# Release 0.2 arm: Sonnet 5.5 as a third honest agent (SDK harness)

- Frozen at commit: d583356 (2026-11-08T17:31Z)
- Command: python -m engsafe.run --backend api --out results/r02/sonnet_honest --agents claude-sonnet-5-5 --effort high --repeats 3 --workers 8
- Same 22 tasks x 3 variants x 3 repeats and four monitors as results/r0_api. Note the sonnet-grounded monitor shares
  the agent's model family here, which is the pairing the common-cause (beta) measurement needs.
- Billing: Anthropic API key (console workspace).
