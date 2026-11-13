"""Run agents and monitors through the Claude Code CLI (`claude -p`) instead of the API.

Uses the session's own Claude login, so no API key is needed. The agent gets the same four tools
as the API backend, served over MCP by `engsafe.mcp_server`; the transcript is rebuilt from the
CLI's stream-json output so monitors see the same format either way. The harness string is
recorded on every episode because harness choice changes results.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .agent import NO_LIST_POLICIES, OPENING, Episode, episode_id, opening_for, system_prompt  # noqa: F401
from .tasks.base import Instance

TOOL_NAMES = ["list_documents", "read_document", "calculate", "submit_decision"]


def tool_names_for(policy: str) -> list[str]:
    return [n for n in TOOL_NAMES if not (policy in NO_LIST_POLICIES and n == "list_documents")]


def mcp_config(inst: Instance, policy: str, state_path: str, pythonpath: str) -> dict:
    """MCP server configuration for one episode; no-list policies start the server without list_documents."""
    return {"mcpServers": {"engsafe": {
        "command": sys.executable, "args": ["-m", "engsafe.mcp_server"],
        "env": {"ENGSAFE_TASK": inst.task_id, "ENGSAFE_VARIANT": inst.variant, "ENGSAFE_STATE": state_path,
                "ENGSAFE_NO_LIST": "1" if policy in NO_LIST_POLICIES else "0", "PYTHONPATH": pythonpath}}}}


def cli_args(inst: Instance, model: str, effort: str, policy: str, cfg_path: str, max_turns: int) -> list[str]:
    """Arguments for `claude -p` for one episode (without the prompt)."""
    return ["-p", "--output-format", "stream-json", "--verbose", "--model", model, "--effort", effort,
            "--system-prompt", system_prompt(policy, inst), "--mcp-config", cfg_path, "--strict-mcp-config",
            "--tools", "", "--allowedTools", *[f"mcp__engsafe__{n}" for n in tool_names_for(policy)],
            "--max-turns", str(max_turns)]


def claude_bin() -> str:
    path = shutil.which("claude")
    if not path:
        raise RuntimeError("claude CLI not found on PATH")
    return path


def harness_id() -> str:
    try:
        v = subprocess.run([claude_bin(), "--version"], capture_output=True, text=True, timeout=30).stdout
        return "claude-code-cli-" + v.split()[0]
    except Exception:  # noqa: BLE001
        return "claude-code-cli"


def _clean_env() -> dict:
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)  # allow a nested non-interactive run
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    return env


def _call(args: list[str], cwd: str, timeout: int) -> tuple[list[dict], str]:
    """Run claude -p; return parsed stream-json events (or the single json result) and stderr."""
    proc = subprocess.run([claude_bin(), *args], capture_output=True, text=True, cwd=cwd,
                          env=_clean_env(), timeout=timeout)
    events = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if proc.returncode != 0 and not events:
        raise RuntimeError(f"claude exited {proc.returncode}: {proc.stderr[-800:]}")
    return events, proc.stderr


def _text_of(content) -> str:
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    text = content if isinstance(content, str) else str(content)
    if text.startswith('{"result"'):  # structured wrapper some CLI versions add around a string result
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and set(obj) == {"result"} and isinstance(obj["result"], str):
                return obj["result"]
        except json.JSONDecodeError:
            pass
    return text


def _ingest(events: list[dict], ep: Episode, tool_names: dict[str, str]) -> dict | None:
    """Append stream-json events to the episode transcript; return the final result event."""
    result = None
    for ev in events:
        t = ev.get("type")
        if t == "assistant":
            if ev.get("error"):  # e.g. authentication_failed: the CLI's own message, not something the agent wrote
                continue
            ep.n_turns += 1
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    ep.transcript.append({"role": "agent", "text": b["text"]})
                elif b.get("type") == "tool_use":
                    ep.n_tool_calls += 1
                    short = b["name"].split("__")[-1]
                    tool_names[b["id"]] = short
                    ep.transcript.append({"role": "tool_call", "name": short, "input": b.get("input", {})})
        elif t == "user":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    ep.transcript.append({"role": "tool_result", "name": tool_names.get(b.get("tool_use_id"), "?"),
                                          "text": _text_of(b.get("content")), "error": bool(b.get("is_error"))})
        elif t == "result":
            result = ev
    return result


def stop_reason(submitted: bool, res: dict | None, max_turns: int) -> tuple[str, str]:
    """Classify how a CLI episode ended. Returns (stop, error text).

    A CLI-level failure (not logged in, quota, transport) arrives as a result event with is_error set and no model
    turn behind it. It is recorded as api_error, so the runner retries it and the analysis never counts it as an
    agent that failed to decide.
    """
    if submitted:
        return "submitted", ""
    if res is None:
        return "api_error", "no result event from claude CLI"
    if (res.get("num_turns", 0) >= max_turns or res.get("terminal_reason") == "max_turns"
            or res.get("subtype") == "error_max_turns"):
        return "max_turns", ""
    if res.get("is_error"):
        return "api_error", f"claude CLI error: {str(res.get('result'))[:300]}"
    if res.get("stop_reason") == "refusal":
        return "refusal", ""
    return "no_decision", ""


def run_episode_cli(inst: Instance, model: str, effort: str, repeat: int, max_turns: int = 24,
                    timeout: int = 900, policy: str = "honest") -> Episode:
    ep = Episode(episode_id=episode_id(inst, model, effort, repeat, policy),
                 task_id=inst.task_id, variant=inst.variant, agent_model=model, effort=effort,
                 repeat=repeat, truth=inst.truth.as_dict(), harness=harness_id(), policy=policy)
    opening = opening_for(policy)
    ep.transcript.append({"role": "user", "text": opening})
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="engsafe-") as tmp:
        state = Path(tmp) / "state.json"
        cfg = Path(tmp) / "mcp.json"
        cfg.write_text(json.dumps(mcp_config(inst, policy, str(state), _clean_env()["PYTHONPATH"])))
        workdir = Path(tmp) / "work"
        workdir.mkdir()
        base = cli_args(inst, model, effort, policy, str(cfg), max_turns)
        tool_names: dict[str, str] = {}
        usage_total: dict = {}
        cost = 0.0
        try:
            events, _ = _call([*base, opening], str(workdir), timeout)
            res = _ingest(events, ep, tool_names)
            if res:
                cost += res.get("total_cost_usd", 0.0) or 0.0
                _add_usage(usage_total, res.get("usage", {}))
            submitted = state.exists() and json.loads(state.read_text()).get("submission")
            if not submitted and res and not res.get("is_error") and res.get("session_id") and ep.n_turns < max_turns:
                nudge = "Please record your decision by calling submit_decision."
                ep.transcript.append({"role": "user", "text": nudge})
                events, _ = _call([*base, "--resume", res["session_id"], nudge], str(workdir), timeout)
                res2 = _ingest(events, ep, tool_names)
                if res2:
                    cost += res2.get("total_cost_usd", 0.0) or 0.0
                    _add_usage(usage_total, res2.get("usage", {}))
                    res = res2
            st = json.loads(state.read_text()) if state.exists() else {}
            ep.docs_read = st.get("docs_read", [])
            sub = st.get("submission")
            if sub:
                ep.decision = sub.get("decision", "NO_DECISION")
                ep.checks = sub.get("checks", [])
                ep.rationale = sub.get("rationale", "")
            ep.stop, ep.error = stop_reason(bool(sub), res, max_turns)
        except (subprocess.TimeoutExpired, RuntimeError, OSError) as exc:
            ep.stop, ep.error = "api_error", f"{type(exc).__name__}: {exc}"[:500]
    ep.usage = {**usage_total, "cost_usd": round(cost, 5)}
    ep.seconds = round(time.time() - t0, 1)
    return ep


def _add_usage(total: dict, usage: dict) -> None:
    for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        total[k] = total.get(k, 0) + (usage.get(k, 0) or 0)


def structured_call_cli(system: str, prompt: str, schema: dict, model: str, effort: str,
                        timeout: int = 600) -> tuple[dict | None, dict, str]:
    """One no-tool call returning JSON matching `schema`. Returns (parsed, usage, raw_text)."""
    with tempfile.TemporaryDirectory(prefix="engsafe-mon-") as tmp:
        args = ["-p", "--output-format", "json", "--model", model, "--effort", effort,
                "--system-prompt", system, "--tools", "", "--strict-mcp-config", "--no-session-persistence",
                "--json-schema", json.dumps(schema), prompt]
        events, _ = _call(args, tmp, timeout)
    res = next((e for e in events if e.get("type") == "result"), events[-1] if events else {})
    if res.get("is_error") and res.get("structured_output") is None:
        raise RuntimeError(f"claude CLI error: {str(res.get('result'))[:300]}")
    usage = {k: (res.get("usage", {}) or {}).get(k, 0) for k in ("input_tokens", "output_tokens")}
    usage["cost_usd"] = round(res.get("total_cost_usd", 0.0) or 0.0, 5)
    parsed = res.get("structured_output")
    raw = res.get("result", "") if isinstance(res.get("result"), str) else json.dumps(res.get("result"))
    if parsed is None:
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            parsed = None
    if res.get("stop_reason") == "refusal":
        return None, usage, "refusal"
    return parsed, usage, raw
