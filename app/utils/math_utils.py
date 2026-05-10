"""Shared math utilities used by multiple services."""
from __future__ import annotations
import math


def normalize(values: dict) -> dict:
    """Normalize a dict of floats so values sum to 1.0."""
    total = sum(values.values())
    if total == 0:
        n = len(values) or 1
        return {k: 1.0 / n for k in values}
    return {k: v / total for k, v in values.items()}


def normalize_weights(weights: list[float]) -> list[float]:
    """Normalize a list of weights to sum to 1.0."""
    total = sum(weights) or 1.0
    return [w / total for w in weights]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def geometric_mean(values: list[float]) -> float:
    if not values or any(v <= 0 for v in values):
        return 0.0
    return math.exp(sum(math.log(v) for v in values) / len(values))


def rank_list(ordered: list) -> dict:
    """Convert ordered list [best, ..., worst] to {item: rank} (1=best)."""
    return {item: i + 1 for i, item in enumerate(ordered)}
