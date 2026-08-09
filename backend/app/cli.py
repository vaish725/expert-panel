"""Manual entry point for exercising the graph before the API/UI layers exist.

Usage: uv run python -m app.cli

Runs a full debate through convergence and synthesis, prints the resulting
recommendation, then simulates a human approving it at the review gate and
resumes the graph to produce the exported report.
"""

import asyncio
import uuid

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings
from app.graph.builder import build_graph
from app.graph.state import DecisionState


def _print_debate_summary(result: dict) -> None:
    print(f"Decision: {result['decision_question']}")
    print(f"Options: {result['options']}")
    print(f"Evidence gathered: {len(result['evidence'])} items")

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

    recommendation = result["final_recommendation"]
    print("\nRecommendation (awaiting human review):")
    print(f"  Recommended option: {recommendation['recommended_option']}")
    print(f"  Confidence note: {recommendation['confidence_note']}")
    print(f"  Unresolved disagreements: {recommendation['unresolved_disagreements']}")
    for option, items in recommendation["tradeoffs"].items():
        print(f"  {option}:")
        for item in items:
            print(f"    ({item['direction']}) {item['claim_id']}")


async def run_sample_debate() -> None:
    thread_id = str(uuid.uuid4())
    initial_state: DecisionState = {
        "thread_id": thread_id,
        "decision_question": "Should I take a remote senior engineer offer at a startup, or stay at my stable corporate job?",
        "options": ["Take the startup offer", "Stay at the corporate job"],
        "user_context": "The startup offer pays 15% less base but includes equity. I have six months of savings.",
        "evidence": [],
        "personas": [],
        "transcript": [],
        "claims_ledger": [],
        "round_number": 1,
        "min_rounds": 2,
        "max_rounds": 3,
        "new_claims_this_round": 0,
        "resolved_this_round": 0,
        "converged": False,
        "forced": False,
        "final_recommendation": None,
        "human_approved": False,
        "exported_report_path": None,
    }

    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        # each round is several graph steps (4 parallel personas, extraction,
        # convergence check); the default recursion limit is too low
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

        result = await graph.ainvoke(initial_state, config=config)
        _print_debate_summary(result)

        # simulate the human-review gate: approve as-is and resume past the
        # interrupt_before("export") pause
        print("\nApproving and resuming...")
        await graph.aupdate_state(config, {"human_approved": True})
        result = await graph.ainvoke(None, config=config)

        print(f"Exported report to: {result['exported_report_path']}")


if __name__ == "__main__":
    asyncio.run(run_sample_debate())
