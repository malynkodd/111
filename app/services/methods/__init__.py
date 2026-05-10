"""
Methods package. Exposes:
  1. Unified METHOD_REGISTRY / run_all_methods() for new code
  2. Legacy function API (weighted_score_method etc.) for backward compatibility
"""
from __future__ import annotations
from collections import defaultdict
from . import weighted_score, borda, condorcet, delphi, ahp

# ── Registry (new unified API) ────────────────────────────────────────────────

METHOD_REGISTRY = {
    "weighted_score": weighted_score,
    "borda": borda,
    "condorcet": condorcet,
    "delphi": delphi,
    "ahp": ahp,
}

METHOD_DISPLAY_NAMES = {
    "weighted_score": weighted_score.METHOD_NAME,
    "borda": borda.METHOD_NAME,
    "condorcet": condorcet.METHOD_NAME,
    "delphi": delphi.METHOD_NAME,
    "ahp": ahp.METHOD_NAME,
}


def run_all_methods(alternatives: list, expert_scores: list, competency_weights: list) -> dict:
    """Run all registered methods and return combined results keyed by display name."""
    results = {}
    for name, module in METHOD_REGISTRY.items():
        display = METHOD_DISPLAY_NAMES[name]
        results[display] = module.calculate(alternatives, expert_scores, competency_weights)
    return results


# ── Shared helpers ────────────────────────────────────────────────────────────

def _weights_map(expert_data):
    return {e["id"]: e["weight"] for e in expert_data}


def _to_unified(latest_scores: dict, expert_data: list):
    """Convert legacy {expert_id: {alt: score}} to (expert_scores_list, weights_list)."""
    weight_map = _weights_map(expert_data)
    ids = list(latest_scores.keys())
    expert_scores_list = [latest_scores[eid] for eid in ids]
    raw_weights = [weight_map.get(eid, 1.0) for eid in ids]
    total = sum(raw_weights) or 1.0
    competency_weights = [w / total for w in raw_weights]
    return expert_scores_list, competency_weights


# ── Legacy API (backward compatibility with models.py, tests) ─────────────────

def weighted_score_method(latest_scores, expert_data, alternatives):
    expert_scores, competency_weights = _to_unified(latest_scores, expert_data)
    result = weighted_score.calculate(alternatives, expert_scores, competency_weights)
    raw = result["details"]["raw_scores"]
    winner = result["ranking"][0] if result["ranking"] else ""
    return {"scores": raw, "winner": winner, "ranking": result["ranking"]}


def borda_method(latest_scores, expert_data, alternatives):
    expert_scores, competency_weights = _to_unified(latest_scores, expert_data)
    result = borda.calculate(alternatives, expert_scores, competency_weights)
    points = result["details"]["borda_points"]
    winner = result["ranking"][0] if result["ranking"] else ""
    return {"scores": points, "winner": winner, "ranking": result["ranking"]}


def condorcet_method(latest_scores, expert_data, alternatives):
    expert_scores, competency_weights = _to_unified(latest_scores, expert_data)
    result = condorcet.calculate(alternatives, expert_scores, competency_weights)
    wins = result["details"]["wins"]
    winner = result["ranking"][0] if result["ranking"] else ""
    return {"scores": wins, "winner": winner, "ranking": result["ranking"]}


def delphi_method(round_map, expert_data, alternatives):
    result = delphi.calculate_from_rounds(alternatives, round_map, expert_data)
    raw = result["details"]["weighted_totals"]
    winner = result["ranking"][0] if result["ranking"] else ""
    return {"scores": raw, "winner": winner, "ranking": result["ranking"]}


def ahp_like_method(latest_scores, expert_data, alternatives):
    expert_scores, competency_weights = _to_unified(latest_scores, expert_data)
    result = ahp.calculate(alternatives, expert_scores, competency_weights)
    priorities = result["details"]["priorities"]
    winner = result["ranking"][0] if result["ranking"] else ""
    return {"scores": priorities, "winner": winner, "ranking": result["ranking"]}


def check_transitivity(pairwise_comparisons: dict) -> tuple:
    """
    Check transitivity of pairwise comparisons.
    {('A','B'): 1, ...} where 1=first better, -1=second better, 0=equal.
    Returns (is_transitive: bool, violations: list of tuples).
    """
    alts = set()
    for a, b in pairwise_comparisons:
        alts.add(a)
        alts.add(b)
    alts = list(alts)

    def beats(x, y):
        v = pairwise_comparisons.get((x, y))
        if v is not None:
            return v == 1
        v = pairwise_comparisons.get((y, x))
        if v is not None:
            return v == -1
        return False

    violations = []
    for a in alts:
        for b in alts:
            if a == b:
                continue
            for c in alts:
                if c == a or c == b:
                    continue
                if beats(a, b) and beats(b, c) and beats(c, a):
                    triple = tuple(sorted([a, b, c]))
                    if triple not in violations:
                        violations.append(triple)

    return len(violations) == 0, violations
