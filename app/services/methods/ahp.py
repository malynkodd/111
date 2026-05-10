from __future__ import annotations

METHOD_NAME = "Метод парних порівнянь (AHP)"
METHOD_CLASS = "pairwise"


def _pairwise_scale(v1: float, v2: float) -> float:
    if v2 == 0:
        return 9.0
    ratio = v1 / v2
    if ratio >= 1:
        return min(9.0, max(1.0, ratio))
    return 1 / min(9.0, max(1.0, 1 / ratio))


def calculate(alternatives: list, expert_scores: list, competency_weights: list) -> dict:
    """
    AHP-like method: build pairwise comparison matrix from weighted scores,
    then derive priorities via eigenvector approximation.
    Args:
        alternatives: list of alternative names
        expert_scores: list of dicts {alt_name: score} per expert
        competency_weights: normalized weights summing to 1.0
    Returns:
        {"ranking": [...], "scores": {...}, "details": {...}}
    """
    from collections import defaultdict

    # Compute weighted aggregate scores first
    totals = defaultdict(float)
    denom = sum(competency_weights) or 1.0
    for score_map, weight in zip(expert_scores, competency_weights):
        for alt in alternatives:
            totals[alt] += score_map.get(alt, 0) * weight
    for alt in totals:
        totals[alt] /= denom

    n = len(alternatives)
    if n == 0:
        return {"ranking": [], "scores": {}, "details": {}}

    matrix = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = _pairwise_scale(
                    totals.get(alternatives[i], 0),
                    totals.get(alternatives[j], 0),
                )

    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    normalized = [
        [matrix[i][j] / col_sums[j] if col_sums[j] else 0 for j in range(n)]
        for i in range(n)
    ]
    priorities = {alternatives[i]: sum(normalized[i]) / n for i in range(n)}

    # Consistency ratio (simplified)
    weighted_sum = [
        sum(matrix[i][j] * priorities[alternatives[j]] for j in range(n))
        for i in range(n)
    ]
    lambda_max = sum(
        weighted_sum[i] / priorities[alternatives[i]]
        for i in range(n)
        if priorities[alternatives[i]] > 0
    ) / n
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0
    ri_table = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
    ri = ri_table.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0

    ranking = sorted(alternatives, key=lambda a: -priorities.get(a, 0))
    total_sum = sum(priorities.values()) or 1.0
    normalized_scores = {a: priorities[a] / total_sum for a in alternatives}

    return {
        "ranking": ranking,
        "scores": normalized_scores,
        "details": {
            "priorities": priorities,
            "lambda_max": round(lambda_max, 4),
            "ci": round(ci, 4),
            "cr": round(cr, 4),
            "consistent": cr < 0.1,
        },
    }
