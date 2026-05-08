import pytest
from app.services.methods import (
    weighted_score_method,
    borda_method,
    condorcet_method,
    delphi_method,
    ahp_like_method,
    check_transitivity,
)

EXPERTS = [{"id": 1, "weight": 0.9}, {"id": 2, "weight": 0.8}, {"id": 3, "weight": 0.7}]
ALTS = ["A", "B", "C", "D"]
SCORES = {
    1: {"A": 8, "B": 7, "C": 6, "D": 9},
    2: {"A": 7, "B": 8, "C": 7, "D": 8},
    3: {"A": 6, "B": 9, "C": 8, "D": 7},
}


def test_weighted_score_winner():
    result = weighted_score_method(SCORES, EXPERTS, ALTS)
    assert "winner" in result
    assert result["winner"] in ALTS
    assert len(result["scores"]) == 4


def test_weighted_score_values_positive():
    result = weighted_score_method(SCORES, EXPERTS, ALTS)
    for v in result["scores"].values():
        assert v >= 0


def test_borda_winner():
    result = borda_method(SCORES, EXPERTS, ALTS)
    assert result["winner"] in ALTS
    assert len(result["scores"]) == 4


def test_borda_ranking_length():
    result = borda_method(SCORES, EXPERTS, ALTS)
    assert len(result["ranking"]) == 4


def test_condorcet_winner():
    result = condorcet_method(SCORES, EXPERTS, ALTS)
    assert result["winner"] in ALTS


def test_condorcet_wins_non_negative():
    result = condorcet_method(SCORES, EXPERTS, ALTS)
    for v in result["scores"].values():
        assert v >= 0


def test_delphi_single_round():
    round_map = {1: SCORES}
    result = delphi_method(round_map, EXPERTS, ALTS)
    assert result["winner"] in ALTS


def test_delphi_two_rounds():
    scores2 = {k: {a: v + 0.5 for a, v in sm.items()} for k, sm in SCORES.items()}
    round_map = {1: SCORES, 2: scores2}
    result = delphi_method(round_map, EXPERTS, ALTS)
    assert result["winner"] in ALTS


def test_ahp_priorities_sum_approx_one():
    result = ahp_like_method(SCORES, EXPERTS, ALTS)
    total = sum(result["scores"].values())
    assert abs(total - 1.0) < 0.01


def test_ahp_winner():
    result = ahp_like_method(SCORES, EXPERTS, ALTS)
    assert result["winner"] in ALTS


def test_check_transitivity_valid():
    pc = {("A", "B"): 1, ("B", "C"): 1, ("A", "C"): 1}
    is_t, viol = check_transitivity(pc)
    assert is_t
    assert viol == []


def test_check_transitivity_violation():
    pc = {("A", "B"): 1, ("B", "C"): 1, ("C", "A"): 1}
    is_t, viol = check_transitivity(pc)
    assert not is_t
    assert len(viol) > 0


def test_all_methods_return_ranking():
    for fn in [weighted_score_method, borda_method, condorcet_method, ahp_like_method]:
        result = fn(SCORES, EXPERTS, ALTS)
        assert "ranking" in result
        assert len(result["ranking"]) == 4
