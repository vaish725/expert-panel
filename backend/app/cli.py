"""Manual entry point for exercising the graph before the API/UI layers exist.

Usage: uv run python -m app.cli
"""

import asyncio
import uuid

from app.graph.builder import build_graph
from app.graph.state import DecisionState


async def run_sample_debate() -> None:
    graph = build_graph()

    initial_state: DecisionState = {
        "thread_id": str(uuid.uuid4()),
        "decision_question": "Should I take a remote senior engineer offer at a startup, or stay at my stable corporate job?",
        "options": ["Take the startup offer", "Stay at the corporate job"],
        "user_context": "The startup offer pays 15% less base but includes equity. I have six months of savings.",
        "evidence": [],
        "personas": [],
        "transcript": [],
        "claims_ledger": [],
        "round_number": 1,
        "min_rounds": 2,
        "max_rounds": 6,
        "new_claims_this_round": 0,
        "resolved_this_round": 0,
        "converged": False,
        "forced": False,
        "final_recommendation": None,
        "human_approved": False,
    }

    # each round is several graph steps (4 parallel personas, extraction,
    # convergence check); the default recursion limit is too low for 6 rounds
    result = await graph.ainvoke(initial_state, config={"recursion_limit": 60})

    print(f"Decision: {result['decision_question']}")
    print(f"Options: {result['options']}")
    print(f"Evidence gathered: {len(result['evidence'])} items")
    for item in result["evidence"]:
        print(f"  - {item['source']} ({item['url']})")

    print("\nTranscript:")
    for turn in result["transcript"]:
        print(f"[round {turn['round']}] {turn['persona']}:\n{turn['content']}\n")

    print("Claims ledger:")
    for claim in result["claims_ledger"]:
        status = "contested" if claim["contested"] else f"resolved (round {claim['resolved_round']})"
        print(f"  {claim['id']} [{claim['stance']}, {status}, reinforced x{claim['reinforced_count']}]: {claim['text']}")

    print(
        f"\nConverged after round {result['round_number']} "
        f"(forced={result['forced']}), {len(result['claims_ledger'])} total claims."
    )


if __name__ == "__main__":
    asyncio.run(run_sample_debate())
