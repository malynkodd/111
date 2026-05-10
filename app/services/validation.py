"""Input validation functions for completeness and transitivity."""
from __future__ import annotations


def validate_scores_complete(
    expert_ids: list,
    alt_ids: list,
    score_map: dict,
    round_no: int,
) -> list[str]:
    """
    Check that every (expert, alternative) pair has a non-zero score for the given round.
    Returns a list of error messages (empty = valid).
    """
    errors = []
    for eid in expert_ids:
        for aid in alt_ids:
            val = score_map.get((eid, aid, round_no))
            if val is None or val == 0:
                errors.append(f"Експерт {eid}: відсутня оцінка для альтернативи {aid}")
    return errors


def validate_score_range(value: float, min_val: float = 0.0, max_val: float = 10.0) -> bool:
    """Return True if value is within [min_val, max_val]."""
    return min_val <= value <= max_val


def validate_competency_weights(weights: list[float]) -> list[str]:
    """Validate that all competency weights are in (0, 1] and sum > 0."""
    errors = []
    for i, w in enumerate(weights):
        if not (0 < w <= 1.0):
            errors.append(f"Вага експерта {i + 1} поза межами (0, 1]: {w}")
    if sum(weights) <= 0:
        errors.append("Сума вагових коефіцієнтів має бути більшою за 0")
    return errors


def check_transitivity(pairwise_comparisons: dict) -> tuple[bool, list]:
    """
    Check transitivity of pairwise comparisons.
    pairwise_comparisons: {('A','B'): 1, ...} where 1=first better, -1=second better.
    Returns (is_transitive, violations).
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
