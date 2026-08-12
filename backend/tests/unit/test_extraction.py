"""Table-driven tests for stance normalization in the extraction node.

No LLM calls: exercises app.graph.nodes.extraction.normalize_stance directly
against freeform model output matched to a decision's exact option strings.
"""

import pytest

from app.graph.nodes.extraction import normalize_stance

OPTIONS = ["Adopt Prettier", "Keep formatting manually"]

CASES = [
    pytest.param("Adopt Prettier", "Adopt Prettier", id="exact_match"),
    pytest.param("adopt prettier", "Adopt Prettier", id="case_insensitive"),
    pytest.param("adopt Prettier", "Adopt Prettier", id="mixed_case"),
    pytest.param("keep manual", "Keep formatting manually", id="abbreviated_paraphrase"),
    pytest.param("Keep formatting manually", "Keep formatting manually", id="exact_match_other_option"),
    pytest.param("neutral", "neutral", id="explicit_neutral"),
    pytest.param("Neutral", "neutral", id="neutral_case_insensitive"),
    pytest.param("something unrelated", "neutral", id="no_match_falls_back_to_neutral"),
]


@pytest.mark.parametrize("raw_stance,expected", CASES)
def test_normalize_stance(raw_stance, expected):
    assert normalize_stance(raw_stance, OPTIONS) == expected
