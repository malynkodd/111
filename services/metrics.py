
from __future__ import annotations
import math
import statistics

def build_rankings_from_scores(latest_scores, alternatives):
    rankings = []
    for expert_id, score_map in latest_scores.items():
        ordered = sorted(alternatives, key=lambda a: (-score_map.get(a, 0), a))
        rankings.append(ordered)
    return rankings

def kendall_w_from_rankings(rankings, alternatives):
    if not rankings:
        return 0.0
    m = len(rankings)
    n = len(alternatives)
    ranks_sum = {a: 0 for a in alternatives}
    for ranking in rankings:
        for idx, alt in enumerate(ranking, start=1):
            ranks_sum[alt] += idx
    mean_rank = sum(ranks_sum.values()) / n
    s = sum((ranks_sum[a] - mean_rank) ** 2 for a in alternatives)
    denominator = (m ** 2) * (n ** 3 - n)
    if denominator == 0:
        return 0.0
    return 12 * s / denominator

def variation_coefficient(latest_scores, expert_data, alternatives):
    result = {}
    for alt in alternatives:
        values = [score_map.get(alt, 0) for score_map in latest_scores.values()]
        mean = statistics.mean(values) if values else 0
        stdev = statistics.pstdev(values) if len(values) > 1 else 0
        result[alt] = (stdev / mean) if mean else 0.0
    return result

def entropy_metric(latest_scores, alternatives):
    result = {}
    for alt in alternatives:
        values = [score_map.get(alt, 0) for score_map in latest_scores.values()]
        total = sum(values) or 1.0
        probs = [v / total for v in values if v > 0]
        ent = -sum(p * math.log(p, 2) for p in probs)
        result[alt] = ent
    return result
