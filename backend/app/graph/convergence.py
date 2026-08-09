"""Pure convergence-decision logic, kept separate from any LangGraph node so
it stays a plain, table-driven-testable function (see tests/unit).
"""

from typing import NamedTuple


class ConvergenceResult(NamedTuple):
    converged: bool
    forced: bool


def check_convergence(
    round_number: int,
    new_claims_this_round: int,
    resolved_this_round: int,
    min_rounds: int,
    max_rounds: int,
) -> ConvergenceResult:
    """Decide whether the debate has run its course.

    Converges naturally once min_rounds have passed and a round adds no new
    claims and resolves none (reinforcement-only rounds count as
    non-productive). Force-converges at max_rounds regardless, as a hard
    safety cap on cost/latency.
    """
    if round_number >= min_rounds and new_claims_this_round == 0 and resolved_this_round == 0:
        return ConvergenceResult(converged=True, forced=False)
    if round_number >= max_rounds:
        return ConvergenceResult(converged=True, forced=True)
    return ConvergenceResult(converged=False, forced=False)
