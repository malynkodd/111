from __future__ import annotations
from collections import defaultdict

METHOD_NAME = "Метод Борда"
METHOD_CLASS = "ranking"


def calculate(alternatives: list, expert_scores: list, competency_weights: list) -> dict:
    """
    Borda count: alternative ranked i-th gets (n-i) points, weighted by competency.
    Args:
        alternatives: list of alternative names
        expert_scores: list of dicts {alt_name: score} per expert
        competency_weights: normalized weights summing to 1.0
    Returns:
        {"ranking": [...], "scores": {...}, "details": {...}}
    """
    n = len(alternatives)
    totals = defaultdict(float)
    for score_map, weight in zip(expert_scores, competency_weights):
        ranking = sorted(alternatives, key=lambda a: (-score_map.get(a, 0), a))
        for i, alt in enumerate(ranking):
            totals[alt] += (n - i - 1) * weight

    ranking = sorted(alternatives, key=lambda a: -totals.get(a, 0))
    total_sum = sum(totals.values()) or 1.0
    normalized = {a: totals[a] / total_sum for a in alternatives}

    return {
        "ranking": ranking,
        "scores": normalized,
        "details": {"borda_points": dict(totals)},
    }
