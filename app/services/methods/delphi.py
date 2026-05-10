from __future__ import annotations
from collections import defaultdict

from app.utils.math_utils import normalize, safe_divide

METHOD_NAME = "Метод Делфі"
METHOD_CLASS = "iterative"


def calculate(
    alternatives: list,
    expert_scores: list,
    competency_weights: list,
    round_history: list | None = None,
) -> dict:
    """
    Delphi iterative method.

    Args:
        alternatives: list of alternative names
        expert_scores: list of dicts {alt_name: score} per expert (current round)
        competency_weights: normalized weights summing to 1.0
        round_history: optional list of previous-round expert_scores lists
                       (same shape as expert_scores). When provided, the most
                       recent previous round is mixed in via:
                           score = 0.7 * current + 0.3 * previous_round_mean
                       If None or empty → simple weighted average.

    Returns:
        {"ranking": [...], "scores": {...}, "details": {...}}
    """
    denom = sum(competency_weights)

    # Compute per-alternative mean of previous round (across experts) if available.
    prev_means: dict = {}
    if round_history:
        prev_scores = round_history[-1]
        if prev_scores:
            for alt in alternatives:
                vals = [sm.get(alt, 0) for sm in prev_scores]
                prev_means[alt] = safe_divide(sum(vals), len(vals))

    totals: dict = defaultdict(float)
    for score_map, weight in zip(expert_scores, competency_weights):
        for alt in alternatives:
            current = score_map.get(alt, 0)
            if prev_means:
                value = 0.7 * current + 0.3 * prev_means.get(alt, current)
            else:
                value = current
            totals[alt] += value * weight

    for alt in list(totals):
        totals[alt] = safe_divide(totals[alt], denom, default=totals[alt])

    ranking = sorted(alternatives, key=lambda a: -totals.get(a, 0))
    normalized = normalize({a: totals.get(a, 0) for a in alternatives})

    return {
        "ranking": ranking,
        "scores": normalized,
        "details": {
            "weighted_totals": dict(totals),
            "iterative": bool(prev_means),
        },
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
