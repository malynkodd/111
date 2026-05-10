from __future__ import annotations
from collections import defaultdict

METHOD_NAME = "Зважений середній бал"
METHOD_CLASS = "scoring"


def calculate(alternatives: list, expert_scores: list, competency_weights: list) -> dict:
    """
    Args:
        alternatives: list of alternative names
        expert_scores: list of dicts {alt_name: score} per expert
        competency_weights: normalized weights summing to 1.0
    Returns:
        {"ranking": [...], "scores": {...}, "details": {...}}
    """
    totals = defaultdict(float)
    denom = sum(competency_weights) or 1.0
    for score_map, weight in zip(expert_scores, competency_weights):
        for alt in alternatives:
            totals[alt] += score_map.get(alt, 0) * weight
    for alt in totals:
        totals[alt] /= denom

    ranking = sorted(alternatives, key=lambda a: -totals.get(a, 0))
    total_sum = sum(totals.values()) or 1.0
    normalized = {a: totals[a] / total_sum for a in alternatives}

    return {
        "ranking": ranking,
        "scores": normalized,
        "details": {"raw_scores": dict(totals)},
    }
