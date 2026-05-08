import pytest
from app.services.metrics import (
    build_rankings_from_scores,
    kendall_w_from_rankings,
    variation_coefficient,
    entropy_metric,
    round_statistics,
    kendall_tau,
    spearman_rho,
    methods_correlation_matrix,
    detect_outlier_experts,
    consensus_ranking,
)

ALTS = ["A", "B", "C", "D"]
SCORES = {
    1: {"A": 8, "B": 7, "C": 6, "D": 9},
    2: {"A": 7, "B": 8, "C": 7, "D": 8},
    3: {"A": 6, "B": 9, "C": 8, "D": 7},
}
EXPERTS = [{"id": 1, "weight": 0.9}, {"id": 2, "weight": 0.8}, {"id": 3, "weight": 0.7}]


def test_build_rankings_returns_list_of_lists():
    rankings = build_rankings_from_scores(SCORES, ALTS)
    assert len(rankings) == 3
    for r in rankings:
        assert set(r) == set(ALTS)


def test_kendall_w_range():
    rankings = build_rankings_from_scores(SCORES, ALTS)
    w = kendall_w_from_rankings(rankings, ALTS)
    assert 0.0 <= w <= 1.0


def test_kendall_w_perfect():
    r = [ALTS, ALTS, ALTS]
    w = kendall_w_from_rankings(r, ALTS)
    assert abs(w - 1.0) < 1e-9


def test_kendall_w_empty():
    assert kendall_w_from_rankings([], ALTS) == 0.0


def test_variation_coefficient_keys():
    cv = variation_coefficient(SCORES, EXPERTS, ALTS)
    assert set(cv.keys()) == set(ALTS)
    for v in cv.values():
        assert v >= 0


def test_entropy_metric_keys():
    ent = entropy_metric(SCORES, ALTS)
    assert set(ent.keys()) == set(ALTS)


def test_round_statistics_fields():
    stats = round_statistics(SCORES, ALTS)
    for alt in ALTS:
        assert alt in stats
        s = stats[alt]
        for k in ("median", "q1", "q3", "iqr", "mean", "std"):
            assert k in s


def test_kendall_tau_identical():
    r = ["A", "B", "C"]
    assert abs(kendall_tau(r, r) - 1.0) < 1e-9


def test_kendall_tau_reversed():
    r1 = ["A", "B", "C"]
    r2 = ["C", "B", "A"]
    assert abs(kendall_tau(r1, r2) - (-1.0)) < 1e-9


def test_kendall_tau_range():
    r1 = ["A", "B", "C", "D"]
    r2 = ["B", "A", "D", "C"]
    tau = kendall_tau(r1, r2)
    assert -1.0 <= tau <= 1.0


def test_spearman_rho_identical():
    r = ["A", "B", "C"]
    assert abs(spearman_rho(r, r) - 1.0) < 1e-9


def test_spearman_rho_reversed():
    r1 = ["A", "B", "C"]
    r2 = ["C", "B", "A"]
    assert abs(spearman_rho(r1, r2) - (-1.0)) < 1e-9


def test_methods_correlation_matrix_structure():
    methods = {
        "M1": {"ranking": ["A", "B", "C", "D"]},
        "M2": {"ranking": ["B", "A", "D", "C"]},
        "M3": {"ranking": ["A", "C", "B", "D"]},
    }
    matrix = methods_correlation_matrix(methods)
    for mn in methods:
        assert mn in matrix
        for mn2 in methods:
            assert mn2 in matrix[mn]
            assert "tau" in matrix[mn][mn2]
            assert "rho" in matrix[mn][mn2]
    # Diagonal should be 1
    for mn in methods:
        assert matrix[mn][mn]["tau"] == 1.0


def test_detect_outlier_experts_no_outliers():
    # Uniform scores → no outliers
    uniform = {i: {a: 5.0 for a in ALTS} for i in range(1, 6)}
    outliers = detect_outlier_experts(uniform, ALTS)
    assert outliers == []


def test_detect_outlier_experts_finds_outlier():
    # One expert with very different scores
    scores = {i: {a: 5.0 for a in ALTS} for i in range(1, 6)}
    scores[99] = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}
    outliers = detect_outlier_experts(scores, ALTS, threshold=1.5)
    # expert 99 should be detected
    expert_ids = [o[0] for o in outliers]
    assert 99 in expert_ids


def test_consensus_ranking_returns_all_alts():
    methods = {
        "M1": {"ranking": ["A", "B", "C", "D"]},
        "M2": {"ranking": ["D", "A", "B", "C"]},
    }
    ranking = consensus_ranking(methods, ALTS)
    assert set(ranking) == set(ALTS)
    assert len(ranking) == 4
