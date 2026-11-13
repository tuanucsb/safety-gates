import json
from types import SimpleNamespace

from engsafe import sdk


def test_key_preference(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anth-key")
    monkeypatch.setenv("PROXIMAB_API_KEY", "prox-key")
    assert sdk.api_key_present()
    assert sdk.make_client().api_key == "prox-key"
    monkeypatch.delenv("PROXIMAB_API_KEY")
    assert sdk.make_client().api_key == "anth-key"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert not sdk.api_key_present()


def test_workspace_header(monkeypatch):
    monkeypatch.setenv("PROXIMAB_API_KEY", "prox-key")
    monkeypatch.delenv("PROXIMAB_WORKSPACE_ID", raising=False)
    assert "anthropic-workspace-id" not in sdk.make_client().default_headers
    monkeypatch.setenv("PROXIMAB_WORKSPACE_ID", "wrkspc_123")
    assert sdk.make_client().default_headers["anthropic-workspace-id"] == "wrkspc_123"


class FakeClient:
    def __init__(self, text, stop="end_turn"):
        self.text, self.stop, self.calls = text, stop, []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                                cache_creation_input_tokens=0)
        return SimpleNamespace(stop_reason=self.stop, usage=usage,
                               content=[SimpleNamespace(type="text", text=self.text)])


def test_structured_call_api_parses_json():
    c = FakeClient(json.dumps({"a": 1}))
    parsed, usage, raw = sdk.structured_call_api(c, "sys", "p", {"type": "object"}, "claude-haiku-5-5", "low")
    assert parsed == {"a": 1} and usage["input_tokens"] == 10 and usage["output_tokens"] == 5
    cfg = c.calls[0]["output_config"]
    assert cfg["effort"] == "low" and cfg["format"]["schema"] == {"type": "object"}
    assert c.calls[0]["system"] == "sys" and c.calls[0]["messages"][0]["content"] == "p"


def test_structured_call_api_refusal_and_garbage():
    assert sdk.structured_call_api(FakeClient("x", stop="refusal"), "s", "p", {}, "m")[2] == "refusal"
    parsed, _, raw = sdk.structured_call_api(FakeClient("not json"), "s", "p", {}, "m")
    assert parsed is None and raw == "not json"
    parsed, _, _ = sdk.structured_call_api(FakeClient("[1, 2]"), "s", "p", {}, "m")
    assert parsed is None
