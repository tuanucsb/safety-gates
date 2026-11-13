"""Offline tests for the CLI backend's stream-json ingestion (no claude process is launched)."""

import json

from engsafe.agent import Episode, render_transcript
from engsafe.cli_backend import _ingest, _text_of, stop_reason


def test_text_of_unwraps_structured_result():
    assert _text_of('{"result":"hello"}') == "hello"
    assert _text_of([{"type": "text", "text": '{"result":"- a: b"}'}]) == "- a: b"
    assert _text_of("plain") == "plain"
    assert _text_of('{"result":"x","other":1}') == '{"result":"x","other":1}'


def test_ingest_rebuilds_transcript():
    ep = Episode("e", "M1-leakage-current", "hazard", "claude-haiku-5-5", "high", 0)
    events = [
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Reading."},
            {"type": "tool_use", "id": "t1", "name": "mcp__engsafe__read_document", "input": {"name": "test_report"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "ES-118 ..."}]}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t2", "name": "mcp__engsafe__submit_decision",
             "input": {"decision": "REJECT", "checks": [], "rationale": "r"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t2", "content": "Decision recorded."}]}},
        {"type": "result", "num_turns": 2, "total_cost_usd": 0.001, "usage": {"input_tokens": 5, "output_tokens": 7},
         "session_id": "s", "stop_reason": "end_turn"},
    ]
    names = {}
    res = _ingest(events, ep, names)
    assert res["total_cost_usd"] == 0.001
    assert ep.n_turns == 2 and ep.n_tool_calls == 2
    roles = [e["role"] for e in ep.transcript]
    assert roles == ["agent", "tool_call", "tool_result", "tool_call", "tool_result"]
    assert ep.transcript[1]["name"] == "read_document" and ep.transcript[2]["name"] == "read_document"
    assert ep.transcript[2]["text"] == "ES-118 ..." and ep.transcript[2]["error"] is False
    text = render_transcript(ep.to_dict())
    assert "[tool call] read_document" in text and "[final decision]" in text
    assert json.loads(text.split("[final decision] ")[1])["decision"] == "NO_DECISION"


def test_cli_level_error_is_not_recorded_as_an_agent_non_decision():
    """A logged-out CLI answers with an assistant event marked authentication_failed and a result with is_error.
    Found on 2026-11-09: such episodes were being stored as NO_DECISION with the CLI's message as agent text."""
    ep = Episode("e", "M1-leakage-current", "hazard", "claude-haiku-5-5", "high", 0)
    events = [
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "error": "authentication_failed",
         "message": {"content": [{"type": "text", "text": "Not logged in - Please run /login"}]}},
        {"type": "result", "subtype": "success", "is_error": True, "num_turns": 1,
         "result": "Not logged in - Please run /login", "stop_reason": "stop_sequence", "total_cost_usd": 0,
         "terminal_reason": "completed", "session_id": "s"},
    ]
    res = _ingest(events, ep, {})
    assert ep.transcript == [] and ep.n_turns == 0
    stop, err = stop_reason(False, res, 24)
    assert stop == "api_error" and "Not logged in" in err


def test_stop_reason_orders_the_cases():
    assert stop_reason(True, {"is_error": True}, 24) == ("submitted", "")
    assert stop_reason(False, None, 24)[0] == "api_error"
    assert stop_reason(False, {"num_turns": 24}, 24) == ("max_turns", "")
    assert stop_reason(False, {"subtype": "error_max_turns", "is_error": True, "num_turns": 3}, 24) == ("max_turns", "")
    assert stop_reason(False, {"stop_reason": "refusal", "num_turns": 2}, 24) == ("refusal", "")
    assert stop_reason(False, {"num_turns": 2, "stop_reason": "end_turn"}, 24) == ("no_decision", "")
