"""L4: LLM explanation via tool calls over the model API (OpenAI client; model from OPENAI_MODEL, default gpt-4o-mini).

Rules (SOT 6 "LLM rules"): numbers only from tool responses; RAG (search_evidence) for citations only;
missing values are information gaps. Every number in the answer is checked against the tool JSON and
reported in ``tool_calls[].json_paths_used``; numbers not found are listed in ``unverified_numbers``.
The API key is read from the environment only and never logged.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from . import config

SYSTEM = (
    "You explain a crop-rotation decision-support tool for Corn Belt farmers. Rules: "
    "(1) Use ONLY numbers that appear in tool results; never compute, round differently, or invent numbers. "
    "(2) Literature claims need a search_evidence hit; cite its url/doi. If no hit, say the evidence is not in the "
    "library. (3) Missing values are 'information gaps' - say so, do not estimate. (4) Never name a single best "
    "strategy; describe trade-offs and remind that the farmer/agronomist decides. (5) Percentages are relative "
    "index changes vs strategy A, not guarantees. (6) SMAP/POWER/GEOS-S2S/NEX-GDDP are context cells (tens of km), "
    "not field-precise. (7) Future climate is a range of scenarios, not a forecast. Keep answers under 180 words."
)

TOOLS = [
    {"type": "function", "function": {"name": "get_profile", "description": "Field profile (area, soil, climate normals, CDL history).",
                                      "parameters": {"type": "object", "properties": {"field_id": {"type": "string"}}, "required": ["field_id"]}}},
    {"type": "function", "function": {"name": "compare_strategies", "description": "Monte Carlo comparison of strategies A-D (scores, P10/P50/P90, CVaR, cards).",
                                      "parameters": {"type": "object", "properties": {"field_id": {"type": "string"}}, "required": ["field_id"]}}},
    {"type": "function", "function": {"name": "get_climate_history", "description": "Last 1-5 years of precipitation, ET, NDVI, temperature, CDL crop.",
                                      "parameters": {"type": "object", "properties": {"field_id": {"type": "string"}, "years": {"type": "integer"}},
                                                     "required": ["field_id"]}}},
    {"type": "function", "function": {"name": "get_outlook", "description": "Next-season (GEOS-S2S) and 2030s (NEX-GDDP-CMIP6) scenario ranges.",
                                      "parameters": {"type": "object", "properties": {"field_id": {"type": "string"}}, "required": ["field_id"]}}},
    {"type": "function", "function": {"name": "get_vulnerable_seasons", "description": "Season hazards and anomalies (POWER, SMAP context cell).",
                                      "parameters": {"type": "object", "properties": {"field_id": {"type": "string"}}, "required": ["field_id"]}}},
    {"type": "function", "function": {"name": "search_evidence", "description": "Search the citation library (quotes + DOI/URL only).",
                                      "parameters": {"type": "object", "properties": {"q": {"type": "string"}, "strategy_code": {"type": "string"}},
                                                     "required": ["q"]}}},
]

ENDPOINTS = {
    "get_profile": "GET /field/{id}/profile",
    "compare_strategies": "POST /strategies/compare",
    "get_climate_history": "GET /field/{id}/climate/history",
    "get_outlook": "GET /field/{id}/climate/outlook",
    "get_vulnerable_seasons": "GET /field/{id}/vulnerable-seasons",
    "search_evidence": "GET /evidence/search",
}

NUM_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?")


class LLMUnavailable(RuntimeError):
    pass


def make_client():
    s = config.llm_settings()
    if not s["api_key"]:
        raise LLMUnavailable("OPENAI_API_KEY is not set")
    from openai import OpenAI

    return OpenAI(api_key=s["api_key"], max_retries=2, timeout=60.0), s["model"]


def _walk(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def _num_variants(v) -> set[str]:
    out = set()
    if isinstance(v, bool) or v is None:
        return out
    if isinstance(v, (int, float)):
        f = float(v)
        out |= {f"{f:g}", str(v), f"{f:.0f}", f"{f:.1f}", f"{f:.2f}", f"{f:.3f}"}
        out |= {s.rstrip("0").rstrip(".") for s in list(out) if "." in s}
    elif isinstance(v, str):
        out |= set(m.group(0) for m in NUM_RE.finditer(v))
    return out


def trace_numbers(answer: str, outputs: list[tuple[str, dict]]) -> tuple[list[dict], list[str]]:
    """Map each number in ``answer`` to JSON paths of the tool outputs; return (tool_calls, unverified)."""
    nums = [m.group(0).replace(",", "") for m in NUM_RE.finditer(answer or "")]
    index: list[tuple[int, str, set[str]]] = []
    for i, (_, out) in enumerate(outputs):
        for path, v in _walk(out):
            index.append((i, path, _num_variants(v)))
    used: dict[int, list[str]] = {i: [] for i in range(len(outputs))}
    unverified = []
    for n in nums:
        bare = n.lstrip("+")
        alts = {bare, bare.lstrip("-")}
        hit = [(i, p) for i, p, vs in index if alts & vs]
        if not hit:
            unverified.append(n)
            continue
        for i, p in hit[:3]:
            if p not in used[i]:
                used[i].append(p)
    calls = [{"endpoint": ENDPOINTS.get(name, name), "tool": name, "json_paths_used": used[i]} for i, (name, _) in enumerate(outputs)]
    return calls, unverified


def explain(req: dict, tools: dict[str, Callable[[dict], dict]], client=None, model: str | None = None) -> dict:
    if client is None:
        client, model = make_client()
    lang = req.get("lang") or "ko"
    focus = req.get("candidate_id") or req.get("strategy_code")
    user = (f"field_id={req['field_id']}; focus strategy={focus or 'all'}; answer language={'Korean' if lang == 'ko' else 'English'}.\n"
            f"Question: {req['question']}")
    messages: list[dict] = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    outputs: list[tuple[str, dict]] = []
    answer = None
    for _ in range(5):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS, tool_choice="auto", temperature=0.2,
        )
        msg = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            answer = msg.content or ""
            break
        am = {"role": "assistant", "content": msg.content or "",
              "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                             for c in calls]}
        messages.append(am)
        for c in calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            args.setdefault("field_id", req["field_id"])
            fn = tools.get(name)
            try:
                out = fn(args) if fn else {"error": {"code": "unknown_tool", "message": name}}
            except Exception as exc:  # tool errors are returned to the model, not raised
                out = {"error": {"code": "tool_error", "message": str(exc)[:200]}}
            outputs.append((name, out))
            messages.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(out, default=str)[:30000]})
    if answer is None:
        answer = ""
    tool_calls, unverified = trace_numbers(answer, outputs)
    citations = []
    for name, out in outputs:
        if name == "search_evidence":
            for h in out.get("hits", []):
                c = {"doi": h.get("doi"), "url": h.get("url")}
                if c not in citations:
                    citations.append(c)
    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "citations": citations,
        "insufficient_evidence": not citations,
        "unverified_numbers": unverified,
        "model": model,
    }
