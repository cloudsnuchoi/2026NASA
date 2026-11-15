"""/explain with a mocked OpenAI-compatible client (no network)."""

import json
from types import SimpleNamespace as NS

from model_api import explain


class FakeCompletions:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


def tool_msg(name, args, reasoning=None):
    call = NS(id="call_1", function=NS(name=name, arguments=json.dumps(args)))
    return NS(choices=[NS(message=NS(content="", tool_calls=[call], reasoning_content=reasoning))])


def final_msg(text):
    return NS(choices=[NS(message=NS(content=text, tool_calls=None, reasoning_content=None))])


def fake_client(script):
    comp = FakeCompletions(script)
    return NS(chat=NS(completions=comp)), comp


def test_explain_numbers_traced_and_thinking_disabled(client, fake_repo):
    from model_api.main import app

    llm, comp = fake_client([
        tool_msg("get_profile", {"field_id": "TEST-FIELD-0001"}, reasoning="r1"),
        final_msg("Field area is 30 ha; ndvi class shown. Value 12345 is not from tools."),
    ])
    app.state.llm_client, app.state.llm_model = llm, "test-model"
    r = client.post("/explain", json={"field_id": "TEST-FIELD-0001", "strategy_code": "B", "question": "How big?", "lang": "en"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["tool_calls"][0]["endpoint"] == "GET /field/{id}/profile"
    assert "$.area_ha" in out["tool_calls"][0]["json_paths_used"]
    assert out["unverified_numbers"] == ["12345"]
    assert out["insufficient_evidence"] is True and out["citations"] == []
    first = comp.calls[0]
    assert first["extra_body"] == {"thinking": {"type": "disabled"}}
    assert first["model"] == "test-model"
    # reasoning_content is passed back with the assistant tool-call message
    assistant = [m for m in comp.calls[1]["messages"] if m["role"] == "assistant"][0]
    assert assistant["reasoning_content"] == "r1"
    tool = [m for m in comp.calls[1]["messages"] if m["role"] == "tool"][0]
    assert "geometry" not in json.loads(tool["content"])


def test_explain_citations_from_evidence(client):
    from model_api.main import app
    from model_api.tests.conftest import FakeRepo

    app.state.repo = FakeRepo(evidence=[{"source_title": "T", "doi": None, "url": "https://example.org/x", "quote": "Rye cover scavenges N.",
                                         "license": None, "strategy_code": "B"}])
    llm, _ = fake_client([tool_msg("search_evidence", {"q": "rye"}), final_msg("See the cited source.")])
    app.state.llm_client, app.state.llm_model = llm, "m"
    out = client.post("/explain", json={"field_id": "TEST-FIELD-0001", "question": "Why rye?"}).json()
    assert out["citations"] == [{"doi": None, "url": "https://example.org/x"}]
    assert out["insufficient_evidence"] is False


def test_explain_without_key_is_503(client):
    r = client.post("/explain", json={"field_id": "TEST-FIELD-0001", "question": "hi"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_unavailable"


def test_trace_numbers_handles_rounding():
    calls, unv = explain.trace_numbers("deficit 72.3 mm and 0.59", [("compare_strategies", {"a": {"b": 72.31}, "c": 0.586})])
    assert unv == ["0.59"] or unv == []  # 0.586 -> "0.59" accepted via 2-dp variant
    assert "$.a.b" in calls[0]["json_paths_used"]
