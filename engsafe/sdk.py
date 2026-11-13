"""Anthropic SDK client for the API backend.

The key is read from PROXIMAB_API_KEY first, then ANTHROPIC_API_KEY. The private name keeps the
experiments' key separate from anything Claude Code itself would pick up (it reads ANTHROPIC_API_KEY),
so API-billed runs and the session's plan login never mix.
"""

from __future__ import annotations

import json
import os

import anthropic

KEY_VARS = ("PROXIMAB_API_KEY", "ANTHROPIC_API_KEY")


def api_key() -> str | None:
    return next((os.environ[v] for v in KEY_VARS if os.environ.get(v)), None)


def api_key_present() -> bool:
    return api_key() is not None


WORKSPACE_VAR = "PROXIMAB_WORKSPACE_ID"  # needed by keys that are not scoped to a workspace (not a secret)


def make_client(max_retries: int = 6) -> anthropic.Anthropic:
    headers = {"anthropic-workspace-id": os.environ[WORKSPACE_VAR]} if os.environ.get(WORKSPACE_VAR) else None
    return anthropic.Anthropic(api_key=api_key(), max_retries=max_retries, default_headers=headers)


def structured_call_api(client, system: str, prompt: str, schema: dict, model: str, effort: str = "medium",
                        max_tokens: int = 16000):
    """One structured-output call. Returns (parsed dict or None, usage, raw text or "refusal");
    the same contract as cli_backend.structured_call_cli. API errors propagate to the caller."""
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    u = resp.usage
    usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
             "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
             "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
    if resp.stop_reason == "refusal":
        return None, usage, "refusal"
    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    return (parsed if isinstance(parsed, dict) else None), usage, text
