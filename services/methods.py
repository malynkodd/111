
from __future__ import annotations
from collections import defaultdict

def _weights_map(expert_data):
    return {e["id"]: e["weight"] for e in expert_data}

def _ranking_for_expert(score_map, alternatives):
    ordered = sorted(alternatives, key=lambda a: (-score_map.get(a, 0), a))
    return ordered

def weighted_score_method(latest_scores, expert_data, alternatives):
    weights = _weights_map(expert_data)
    totals = defaultdict(float)
    denom = sum(weights.values()) or 1.0
    for expert_id, score_map in latest_scores.items():
        for alt in alternatives:
            totals[alt] += score_map.get(alt, 0) * weights.get(expert_id, 1.0)
    for alt in totals:
        totals[alt] /= denom
    winner = max(totals, key=totals.get)
    return {"scores": dict(totals), "winner": winner}

def borda_method(latest_scores, expert_data, alternatives):
    weights = _weights_map(expert_data)
    n = len(alternatives)
    totals = defaultdict(float)
    for expert_id, score_map in latest_scores.items():
        ranking = _ranking_for_expert(score_map, alternatives)
        for i, alt in enumerate(ranking):
            totals[alt] += (n - i - 1) * weights.get(expert_id, 1.0)
    winner = max(totals, key=totals.get)
    return {"scores": dict(totals), "winner": winner}

def condorcet_method(latest_scores, expert_data, alternatives):
    weights = _weights_map(expert_data)
    wins = {a: 0.0 for a in alternatives}
    for i, a in enumerate(alternatives):
        for b in alternatives[i + 1:]:
            score_a = 0.0
            score_b = 0.0
            for expert_id, score_map in latest_scores.items():
                weight = weights.get(expert_id, 1.0)
                sa = score_map.get(a, 0)
                sb = score_map.get(b, 0)
                if sa > sb:
                    score_a += weight
                elif sb > sa:
                    score_b += weight
            if score_a > score_b:
                wins[a] += 1
            elif score_b > score_a:
                wins[b] += 1
            else:
                wins[a] += 0.5
                wins[b] += 0.5
    winner = max(wins, key=wins.get)
    return {"scores": wins, "winner": winner}

def delphi_method(round_map, expert_data, alternatives):
    weights = _weights_map(expert_data)
    round_numbers = sorted(round_map)
    if not round_numbers:
        return {"scores": {}, "winner": ""}
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
    winner = max(totals, key=totals.get)
    return {"scores": dict(totals), "winner": winner}

def _pairwise_scale(v1, v2):
    if v2 == 0:
        return 9.0
    ratio = v1 / v2
    if ratio >= 1:
        return min(9.0, max(1.0, ratio))
    return 1 / min(9.0, max(1.0, 1 / ratio))

def ahp_like_method(latest_scores, expert_data, alternatives):
    weights = _weights_map(expert_data)
    weighted = weighted_score_method(latest_scores, expert_data, alternatives)["scores"]
    n = len(alternatives)
    matrix = [[1.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = _pairwise_scale(weighted[alternatives[i]], weighted[alternatives[j]])
    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    normalized = [[matrix[i][j] / col_sums[j] for j in range(n)] for i in range(n)]
    priorities = {alternatives[i]: sum(normalized[i]) / n for i in range(n)}
    winner = max(priorities, key=priorities.get)
    return {"scores": priorities, "winner": winner}
