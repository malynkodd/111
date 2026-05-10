"""Cross-method comparison: consensus ranking, Kendall τ, Spearman ρ between methods."""
from __future__ import annotations
from .metrics import kendall_tau, spearman_rho, consensus_ranking


def methods_comparison(methods_results: dict, alt_names: list) -> dict:
    """
    Full cross-method comparison report.
    Args:
        methods_results: {"Method Name": {"ranking": [...], "scores": {...}}, ...}
        alt_names: list of alternative names
    Returns:
        {"consensus_ranking": [...], "correlation_matrix": {...}, "agreement_score": float}
    """
    if not methods_results:
        return {"consensus_ranking": alt_names[:], "correlation_matrix": {}, "agreement_score": 0.0}

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

    consensus = consensus_ranking(methods_results, alt_names)

    # Overall agreement score: mean of all off-diagonal tau values
    off_diag = [
        matrix[a][b]["tau"]
        for a in names for b in names if a != b
    ]
    agreement = sum(off_diag) / len(off_diag) if off_diag else 1.0

    return {
        "consensus_ranking": consensus,
        "correlation_matrix": matrix,
        "agreement_score": round(agreement, 3),
    }
