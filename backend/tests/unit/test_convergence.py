"""Table-driven tests for the pure convergence-decision function.

No LLM calls involved: this exercises app.graph.convergence.check_convergence
directly against combinations of round_number/new_claims/resolved against
min_rounds/max_rounds, per the PRD's testing plan.
"""

import pytest

from app.graph.convergence import check_convergence

# (round_number, new_claims_this_round, resolved_this_round, min_rounds, max_rounds) -> (converged, forced)
CASES = [
    # below min_rounds: never converges naturally even with a quiet round
    pytest.param(1, 0, 0, 2, 6, (False, False), id="quiet_round_before_min_rounds"),
    # at min_rounds with a quiet round: converges naturally
    pytest.param(2, 0, 0, 2, 6, (True, False), id="quiet_round_at_min_rounds"),
    # new claims raised: keeps going regardless of round number
    pytest.param(3, 1, 0, 2, 6, (False, False), id="new_claim_keeps_going"),
    # a claim resolved (even with no new claims): keeps going, still productive
    pytest.param(3, 0, 1, 2, 6, (False, False), id="resolution_keeps_going"),
    # reinforcement-only round (no new, no resolved) after min_rounds: converges
    pytest.param(4, 0, 0, 2, 6, (True, False), id="reinforcement_only_converges"),
    # hard cap hit while still productive: force-converges
    pytest.param(6, 2, 1, 2, 6, (True, True), id="max_rounds_forces_even_if_productive"),
    # hard cap hit on an otherwise-natural quiet round: still just converged, not double-flagged oddly
    pytest.param(6, 0, 0, 2, 6, (True, False), id="max_rounds_with_quiet_round_is_natural_not_forced"),
    # past max_rounds (shouldn't normally happen, but must still force)
    pytest.param(7, 3, 0, 2, 6, (True, True), id="past_max_rounds_forces"),
]


@pytest.mark.parametrize("round_number,new_claims,resolved,min_rounds,max_rounds,expected", CASES)
def test_check_convergence(round_number, new_claims, resolved, min_rounds, max_rounds, expected):
    result = check_convergence(
        round_number=round_number,
        new_claims_this_round=new_claims,
        resolved_this_round=resolved,
        min_rounds=min_rounds,
        max_rounds=max_rounds,
    )
    assert (result.converged, result.forced) == expected
