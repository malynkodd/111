"""Tests for cross-method comparison and new metrics (Step 7)."""
import pytest
from app.services.comparison import methods_comparison
from app.services.metrics import chi_squared_test


# ── Chi-squared tests ────────────────────────────────────────────────────────

def test_chi_squared_perfect_concordance():
    """W=1 with 5 experts and 4 alternatives."""
    result = chi_squared_test(1.0, m=5, n=4)
    assert result["chi_squared"] == pytest.approx(5 * 3, rel=1e-6)
    assert result["df"] == 3
    assert result["significant"] is True


def test_chi_squared_zero_concordance():
    result = chi_squared_test(0.0, m=5, n=4)
    assert result["chi_squared"] == 0.0
    assert result["significant"] is False


def test_chi_squared_moderate():
    result = chi_squared_test(0.6, m=5, n=5)
    assert result["chi_squared"] == pytest.approx(0.6 * 5 * 4, rel=1e-4)
    assert result["df"] == 4
    assert 0 <= result["p_value"] <= 1


def test_chi_squared_single_alternative():
    result = chi_squared_test(1.0, m=5, n=1)
    assert result["chi_squared"] == 0.0
    assert result["df"] == 0


def test_chi_squared_keys_present():
    result = chi_squared_test(0.7, 4, 5)
    for key in ("chi_squared", "df", "p_value", "significant"):
        assert key in result


# ── Comparison tests ─────────────────────────────────────────────────────────

METHODS = {
    "M1": {"ranking": ["A", "B", "C", "D"], "scores": {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}},
    "M2": {"ranking": ["A", "B", "D", "C"], "scores": {"A": 0.38, "B": 0.32, "C": 0.1, "D": 0.2}},
    "M3": {"ranking": ["B", "A", "C", "D"], "scores": {"A": 0.3, "B": 0.35, "C": 0.2, "D": 0.15}},
}
ALTS = ["A", "B", "C", "D"]


def test_comparison_returns_consensus_ranking(subtests):
    result = methods_comparison(METHODS, ALTS)
    assert "consensus_ranking" in result
    assert set(result["consensus_ranking"]) == set(ALTS)
    assert len(result["consensus_ranking"]) == 4


def test_comparison_returns_correlation_matrix():
    result = methods_comparison(METHODS, ALTS)
    matrix = result["correlation_matrix"]
    for mn in METHODS:
        assert mn in matrix
        for mn2 in METHODS:
            assert mn2 in matrix[mn]
            assert "tau" in matrix[mn][mn2]
            assert "rho" in matrix[mn][mn2]


def test_comparison_diagonal_is_one():
    result = methods_comparison(METHODS, ALTS)
    matrix = result["correlation_matrix"]
    for mn in METHODS:
        assert matrix[mn][mn]["tau"] == 1.0
        assert matrix[mn][mn]["rho"] == 1.0


def test_comparison_agreement_score_range():
    result = methods_comparison(METHODS, ALTS)
    score = result["agreement_score"]
    assert -1.0 <= score <= 1.0


def test_comparison_empty_methods():
    result = methods_comparison({}, ALTS)
    assert result["consensus_ranking"] == ALTS
    assert result["correlation_matrix"] == {}


def test_comparison_single_method():
    single = {"M1": METHODS["M1"]}
    result = methods_comparison(single, ALTS)
    assert result["consensus_ranking"] == METHODS["M1"]["ranking"]
    assert result["agreement_score"] == 1.0


# ── Unified method interface tests ───────────────────────────────────────────

def test_unified_method_borda():
    from app.services.methods.borda import calculate
    alts = ["A", "B", "C"]
    scores = [{"A": 9, "B": 7, "C": 5}, {"A": 8, "B": 9, "C": 6}]
    weights = [0.6, 0.4]
    result = calculate(alts, scores, weights)
    assert "ranking" in result
    assert "scores" in result
    assert "details" in result
    assert len(result["ranking"]) == 3
    assert abs(sum(result["scores"].values()) - 1.0) < 0.01


def test_unified_method_condorcet():
    from app.services.methods.condorcet import calculate
    alts = ["A", "B", "C"]
    scores = [{"A": 9, "B": 7, "C": 5}, {"A": 8, "B": 9, "C": 6}]
    weights = [0.6, 0.4]
    result = calculate(alts, scores, weights)
    assert set(result["ranking"]) == set(alts)
    assert all(0 <= v <= 1.0 for v in result["scores"].values())


def test_unified_method_weighted_score():
    from app.services.methods.weighted_score import calculate
    alts = ["A", "B", "C"]
    scores = [{"A": 9, "B": 7, "C": 5}, {"A": 8, "B": 9, "C": 6}]
    weights = [0.6, 0.4]
    result = calculate(alts, scores, weights)
    assert result["ranking"][0] in alts
    assert abs(sum(result["scores"].values()) - 1.0) < 0.01


def test_unified_method_ahp():
    from app.services.methods.ahp import calculate
    alts = ["A", "B", "C"]
    scores = [{"A": 9, "B": 7, "C": 5}, {"A": 8, "B": 9, "C": 6}]
    weights = [0.6, 0.4]
    result = calculate(alts, scores, weights)
    assert "cr" in result["details"]
    assert set(result["ranking"]) == set(alts)


def test_unified_method_delphi():
    from app.services.methods.delphi import calculate
    alts = ["A", "B", "C"]
    scores = [{"A": 9, "B": 7, "C": 5}, {"A": 8, "B": 9, "C": 6}]
    weights = [0.6, 0.4]
    result = calculate(alts, scores, weights)
    assert set(result["ranking"]) == set(alts)


def test_all_methods_same_interface():
    """All methods must return ranking, scores, details."""
    from app.services.methods.borda import calculate as borda
    from app.services.methods.condorcet import calculate as condorcet
    from app.services.methods.weighted_score import calculate as weighted
    from app.services.methods.ahp import calculate as ahp
    from app.services.methods.delphi import calculate as delphi

    alts = ["X", "Y", "Z"]
    scores = [{"X": 8, "Y": 6, "Z": 4}, {"X": 7, "Y": 8, "Z": 5}]
    weights = [0.55, 0.45]

    for fn in [borda, condorcet, weighted, ahp, delphi]:
        result = fn(alts, scores, weights)
        assert "ranking" in result, f"{fn.__module__} missing 'ranking'"
        assert "scores" in result, f"{fn.__module__} missing 'scores'"
        assert "details" in result, f"{fn.__module__} missing 'details'"
        assert set(result["ranking"]) == set(alts)
