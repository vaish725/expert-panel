"""Streaming integration test: verifies all 4 persona token streams arrive
correctly tagged and interleaved without cross-contamination, i.e. persona
A's tokens never appear under persona B's node tag (PRD 13).

Runs the real graph fan-out and the real get_stream_writer() custom-event
mechanism; only the LLM call itself is faked, so no API calls are made.
"""

import asyncio
import random

import pytest
from langgraph.graph import END, StateGraph

from app.graph.nodes import debate
from app.graph.state import DecisionState

# distinct, easily-detectable token vocabulary per persona: if any token from
# one persona's set showed up under another persona's node tag, that would
# be exactly the cross-contamination this test exists to catch
CHUNK_SETS = {
    "skeptic": ["SKEPTIC-alpha ", "SKEPTIC-beta ", "SKEPTIC-gamma "],
    "optimist": ["OPTIMIST-alpha ", "OPTIMIST-beta ", "OPTIMIST-gamma "],
    "contrarian": ["CONTRARIAN-alpha ", "CONTRARIAN-beta ", "CONTRARIAN-gamma "],
    "pragmatist": ["PRAGMATIST-alpha ", "PRAGMATIST-beta ", "PRAGMATIST-gamma "],
}


class _FakeChunk:
    def __init__(self, content):
        self.content = content


class _FakePersonaLLM:
    """Stands in for ChatAnthropic. Identifies which persona is calling from
    its own system prompt (it names itself, e.g. "You are the Skeptic..."),
    then streams that persona's chunk set with real await points in between
    so the four persona nodes genuinely interleave, same as live streaming."""

    async def astream(self, messages):
        system_prompt = messages[0]["content"].lower()
        for name, chunks in CHUNK_SETS.items():
            if name in system_prompt:
                for text in chunks:
                    await asyncio.sleep(random.uniform(0, 0.005))
                    yield _FakeChunk(text)
                return
        raise AssertionError(f"could not identify persona from system prompt: {system_prompt[:80]}")


def _build_fan_out_graph():
    """Minimal graph: one entry point fanning out to all 4 real persona
    nodes, mirroring the fan-out shape in app.graph.builder."""

    def _start(_state):
        return {}

    graph = StateGraph(DecisionState)
    graph.add_node("start", _start)
    for node_name, node_fn in [
        ("persona_skeptic", debate.persona_skeptic),
        ("persona_optimist", debate.persona_optimist),
        ("persona_contrarian", debate.persona_contrarian),
        ("persona_pragmatist", debate.persona_pragmatist),
    ]:
        graph.add_node(node_name, node_fn)
        graph.add_edge("start", node_name)
        graph.add_edge(node_name, END)
    graph.set_entry_point("start")
    return graph.compile()


async def test_persona_token_streams_tagged_correctly_no_cross_contamination(monkeypatch):
    monkeypatch.setattr(debate, "_build_persona_llm", lambda: _FakePersonaLLM())

    graph = _build_fan_out_graph()
    initial_state = {
        "decision_question": "Test decision?",
        "options": ["Option A", "Option B"],
        "user_context": "",
        "evidence": [],
        "transcript": [],
        "claims_ledger": [],
        "round_number": 1,
    }

    token_events = [
        event
        async for event in graph.astream(initial_state, stream_mode="custom")
        if event["type"] == "token"
    ]
    assert token_events, "expected at least one token event"

    deltas_by_node: dict[str, list[str]] = {}
    for event in token_events:
        deltas_by_node.setdefault(event["node"], []).append(event["delta"])

    assert set(deltas_by_node.keys()) == {
        "persona_skeptic",
        "persona_optimist",
        "persona_contrarian",
        "persona_pragmatist",
    }

    for node_id, deltas in deltas_by_node.items():
        persona_name = node_id.removeprefix("persona_")
        reconstructed = "".join(deltas)

        # correct tagging + correct ordering: concatenating this node's
        # deltas in arrival order reproduces exactly its own persona's text
        assert reconstructed == "".join(CHUNK_SETS[persona_name])

        # no cross-contamination: no other persona's tokens leaked in here
        for other_name, other_chunks in CHUNK_SETS.items():
            if other_name == persona_name:
                continue
            for chunk in other_chunks:
                assert chunk not in reconstructed
