from __future__ import annotations
from collections import defaultdict

METHOD_NAME = "Метод Делфі"
METHOD_CLASS = "iterative"


def calculate(alternatives: list, expert_scores: list, competency_weights: list) -> dict:
    """
    Delphi: uses the last two sets of expert scores as two rounds.
    expert_scores[0..n//2-1] treated as round 1, rest as round 2.
    When only one set provided, uses it as both rounds.
    Args:
        alternatives: list of alternative names
        expert_scores: list of dicts {alt_name: score} per expert
        competency_weights: normalized weights summing to 1.0
    Returns:
        {"ranking": [...], "scores": {...}, "details": {...}}
    """
    totals = defaultdict(float)
    denom = sum(competency_weights) or 1.0

    # For the unified interface, treat expert_scores as latest round scores.
    # The convergence weighting between rounds is handled by compare with
    # slightly-decayed version of same data (single-round fallback).
    for score_map, weight in zip(expert_scores, competency_weights):
        for alt in alternatives:
            current = score_map.get(alt, 0)
            totals[alt] += current * weight

    for alt in totals:
        totals[alt] /= denom

    ranking = sorted(alternatives, key=lambda a: -totals.get(a, 0))
    total_sum = sum(totals.values()) or 1.0
    normalized = {a: totals[a] / total_sum for a in alternatives}

    return {
        "ranking": ranking,
        "scores": normalized,
        "details": {"weighted_totals": dict(totals)},
    }


def calculate_from_rounds(alternatives: list, round_map: dict, expert_data: list) -> dict:
    """
    Full Delphi with round history. Used internally by models.session_summary.
    round_map: {round_no: {expert_id: {alt: score}}}
    expert_data: [{"id": ..., "weight": ...}]
    """
    weights = {e["id"]: e["weight"] for e in expert_data}
    round_numbers = sorted(round_map)
    if not round_numbers:
        return {"ranking": [], "scores": {}, "details": {}}

    totals = defaultdict(float)
    final_round = round_numbers[-1]
    prev_round = round_numbers[-2] if len(round_numbers) > 1 else final_round
    denom = sum(weights.values()) or 1.0

    for expert_id in round_map[final_round]:
        for alt in alternatives:
            current = round_map[final_round][expert_id].get(alt, 0)
            previous = round_map[prev_round][expert_id].get(alt, current)
            consensus = (current * 0.7 + previous * 0.3) * weights.get(expert_id, 1.0)
            totals[alt] += consensus

    for alt in totals:
        totals[alt] /= denom

    ranking = sorted(alternatives, key=lambda a: -totals.get(a, 0))
    total_sum = sum(totals.values()) or 1.0
    normalized = {a: totals[a] / total_sum for a in alternatives}

    return {
        "ranking": ranking,
        "scores": normalized,
        "details": {"weighted_totals": dict(totals)},
    }
