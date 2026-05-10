from __future__ import annotations

METHOD_NAME = "Метод Кондорсе"
METHOD_CLASS = "pairwise"


def calculate(alternatives: list, expert_scores: list, competency_weights: list) -> dict:
    """
    Condorcet method: weighted pairwise wins matrix.
    Args:
        alternatives: list of alternative names
        expert_scores: list of dicts {alt_name: score} per expert
        competency_weights: normalized weights summing to 1.0
    Returns:
        {"ranking": [...], "scores": {...}, "details": {...}}
    """
    wins = {a: 0.0 for a in alternatives}
    pairwise_matrix = {a: {b: 0.0 for b in alternatives} for a in alternatives}

    for i, a in enumerate(alternatives):
        for b in alternatives[i + 1:]:
            score_a = score_b = 0.0
            for score_map, weight in zip(expert_scores, competency_weights):
                sa = score_map.get(a, 0)
                sb = score_map.get(b, 0)
                if sa > sb:
                    score_a += weight
                elif sb > sa:
                    score_b += weight
            if score_a > score_b:
                wins[a] += 1
                pairwise_matrix[a][b] = 1.0
            elif score_b > score_a:
                wins[b] += 1
                pairwise_matrix[b][a] = 1.0
            else:
                wins[a] += 0.5
                wins[b] += 0.5
                pairwise_matrix[a][b] = 0.5
                pairwise_matrix[b][a] = 0.5

    max_wins = len(alternatives) - 1 or 1
    ranking = sorted(alternatives, key=lambda a: -wins.get(a, 0))
    normalized = {a: wins[a] / max_wins for a in alternatives}

    return {
        "ranking": ranking,
        "scores": normalized,
        "details": {"wins": wins, "pairwise_matrix": pairwise_matrix},
    }
