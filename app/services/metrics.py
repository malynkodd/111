from __future__ import annotations
import math
import statistics
from collections import defaultdict

try:
    from scipy.stats import chi2 as _chi2_dist
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


def build_rankings_from_scores(latest_scores: dict, alternatives: list) -> list:
    rankings = []
    for expert_id, score_map in latest_scores.items():
        ordered = sorted(alternatives, key=lambda a: (-score_map.get(a, 0), a))
        rankings.append(ordered)
    return rankings


def kendall_w_from_rankings(rankings: list, alternatives: list) -> float:
    if not rankings:
        return 0.0
    m = len(rankings)
    n = len(alternatives)
    if n <= 1:
        return 1.0
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


def chi_squared_test(kendall_w: float, m: int, n: int) -> dict:
    """
    Chi-squared significance test for Kendall's W.
    χ² = W * m * (n - 1), df = n - 1
    Returns {"chi_squared": float, "df": int, "p_value": float, "significant": bool}
    """
    if n <= 1 or m <= 0:
        return {"chi_squared": 0.0, "df": max(0, n - 1), "p_value": 1.0, "significant": False}
    chi_sq = kendall_w * m * (n - 1)
    df = n - 1
    if _SCIPY_AVAILABLE:
        p_value = float(1.0 - _chi2_dist.cdf(chi_sq, df))
    else:
        p_value = _chi2_p_normal_approx(chi_sq, df)
    return {
        "chi_squared": round(chi_sq, 4),
        "df": df,
        "p_value": round(p_value, 4),
        "significant": p_value < 0.05,
    }


def _chi2_p_normal_approx(x: float, k: int) -> float:
    # Normal approximation for chi-squared p-value (not full Wilson-Hilferty).
    # Accurate enough for df >= 5. For small df, install scipy for exact values.
    if x <= 0 or k <= 0:
        return 1.0
    mu = k
    sigma2 = 2 * k
    z = (x - mu) / math.sqrt(sigma2)
    return max(0.0, min(1.0, 0.5 * math.erfc(z / math.sqrt(2))))


def variation_coefficient(latest_scores: dict, expert_data: list, alternatives: list) -> dict:
    result = {}
    for alt in alternatives:
        values = [score_map.get(alt, 0) for score_map in latest_scores.values()]
        mean = statistics.mean(values) if values else 0
        stdev = statistics.pstdev(values) if len(values) > 1 else 0
        result[alt] = (stdev / mean) if mean else 0.0
    return result


def entropy_metric(latest_scores: dict, alternatives: list) -> dict:
    result = {}
    for alt in alternatives:
        values = [score_map.get(alt, 0) for score_map in latest_scores.values()]
        total = sum(values) or 1.0
        probs = [v / total for v in values if v > 0]
        ent = -sum(p * math.log(p, 2) for p in probs)
        result[alt] = ent
    return result


def round_statistics(scores_dict: dict, alt_names: list) -> dict:
    """
    Returns for each alternative: median, q1, q3, iqr, mean, std.
    scores_dict: {expert_id: {alt_name: score}}
    """
    result = {}
    for alt in alt_names:
        values = sorted(score_map.get(alt, 0) for score_map in scores_dict.values())
        if not values:
            result[alt] = {"median": 0, "q1": 0, "q3": 0, "iqr": 0, "mean": 0, "std": 0}
            continue
        n = len(values)
        med = statistics.median(values)
        mean = statistics.mean(values)
        std = statistics.pstdev(values) if n > 1 else 0.0
        q1_idx = (n - 1) * 0.25
        q3_idx = (n - 1) * 0.75
        lo, hi = int(q1_idx), int(q3_idx)
        q1 = values[lo] + (q1_idx - lo) * (values[min(lo + 1, n - 1)] - values[lo])
        q3 = values[hi] + (q3_idx - hi) * (values[min(hi + 1, n - 1)] - values[hi])
        result[alt] = {
            "median": round(med, 3),
            "q1": round(q1, 3),
            "q3": round(q3, 3),
            "iqr": round(q3 - q1, 3),
            "mean": round(mean, 3),
            "std": round(std, 3),
        }
    return result


def _rank_list(ranking: list) -> dict:
    """Convert ordered list to {item: rank} dict (1 = best)."""
    return {alt: i + 1 for i, alt in enumerate(ranking)}


def kendall_tau(ranking1: list, ranking2: list) -> float:
    """Kendall τ-b between two rankings."""
    if len(ranking1) != len(ranking2) or not ranking1:
        return 0.0
    r1 = _rank_list(ranking1)
    r2 = _rank_list(ranking2)
    alts = list(r1.keys())
    n = len(alts)
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            d1 = r1[alts[i]] - r1[alts[j]]
            d2 = r2[alts[i]] - r2[alts[j]]
            prod = d1 * d2
            if prod > 0:
                concordant += 1
            elif prod < 0:
                discordant += 1
    denom = n * (n - 1) / 2
    if denom == 0:
        return 0.0
    return (concordant - discordant) / denom


def spearman_rho(ranking1: list, ranking2: list) -> float:
    """Spearman ρ between two rankings."""
    if len(ranking1) != len(ranking2) or not ranking1:
        return 0.0
    r1 = _rank_list(ranking1)
    r2 = _rank_list(ranking2)
    n = len(ranking1)
    d_sq = sum((r1[alt] - r2[alt]) ** 2 for alt in r1)
    denom = n * (n ** 2 - 1)
    if denom == 0:
        return 0.0
    return 1 - 6 * d_sq / denom


def methods_correlation_matrix(methods_results: dict) -> dict:
    """
    Correlation matrix between all method results.
    methods_results: {'Method Name': {'ranking': [...]}, ...}
    Returns: {'Method A': {'Method B': {'tau': 0.85, 'rho': 0.90}}, ...}
    """
    names = list(methods_results.keys())
    matrix = {}
    for a in names:
        matrix[a] = {}
        r_a = methods_results[a].get("ranking", [])
        for b in names:
            r_b = methods_results[b].get("ranking", [])
            if a == b:
                matrix[a][b] = {"tau": 1.0, "rho": 1.0}
            else:
                matrix[a][b] = {
                    "tau": round(kendall_tau(r_a, r_b), 3),
                    "rho": round(spearman_rho(r_a, r_b), 3),
                }
    return matrix


def detect_outlier_experts(
    scores_by_expert: dict,
    alt_names: list,
    threshold: float = 2.0,
) -> list:
    """
    Detect outlier experts whose average deviation from group mean
    exceeds threshold standard deviations.
    Returns list of (expert_id, deviation_score).
    """
    if not scores_by_expert or not alt_names:
        return []

    group_means = {}
    for alt in alt_names:
        vals = [sm.get(alt, 0) for sm in scores_by_expert.values()]
        group_means[alt] = statistics.mean(vals) if vals else 0.0

    deviations = {}
    for expert_id, score_map in scores_by_expert.items():
        diffs = [abs(score_map.get(alt, 0) - group_means[alt]) for alt in alt_names]
        deviations[expert_id] = statistics.mean(diffs) if diffs else 0.0

    dev_values = list(deviations.values())
    if len(dev_values) < 2:
        return []
    mean_dev = statistics.mean(dev_values)
    std_dev = statistics.pstdev(dev_values)
    if std_dev == 0:
        return []

    outliers = []
    for expert_id, dev in deviations.items():
        z = (dev - mean_dev) / std_dev
        if z > threshold:
            outliers.append((expert_id, round(z, 3)))
    return sorted(outliers, key=lambda x: -x[1])


def consensus_ranking(methods_results: dict, alt_names: list) -> list:
    """
    Consensus ranking via median of ranks across all methods.
    Returns list of alternatives from best to worst.
    """
    if not methods_results or not alt_names:
        return alt_names[:]

    rank_lists = defaultdict(list)
    for result in methods_results.values():
        ranking = result.get("ranking", [])
        if not ranking:
            continue
        for i, alt in enumerate(ranking):
            rank_lists[alt].append(i + 1)

    median_ranks = {}
    for alt in alt_names:
        ranks = rank_lists.get(alt, [len(alt_names)])
        median_ranks[alt] = statistics.median(ranks)

    return sorted(alt_names, key=lambda a: median_ranks.get(a, len(alt_names)))
