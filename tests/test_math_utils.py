from app.utils.math_utils import (
    normalize, normalize_weights, safe_divide, geometric_mean, rank_list,
)


def test_normalize_sums_to_one():
    result = normalize({"a": 2, "b": 3})
    assert abs(sum(result.values()) - 1.0) < 1e-9


def test_normalize_zero_total():
    result = normalize({"a": 0, "b": 0})
    assert all(v == 0 for v in result.values())


def test_normalize_preserves_keys():
    result = normalize({"x": 1, "y": 2, "z": 3})
    assert set(result.keys()) == {"x", "y", "z"}


def test_safe_divide_normal():
    assert safe_divide(10, 2) == 5.0


def test_safe_divide_by_zero():
    assert safe_divide(5, 0) == 0.0
    assert safe_divide(5, 0, default=99) == 99


def test_geometric_mean():
    result = geometric_mean([1, 4, 16])
    assert abs(result - 4.0) < 1e-6


def test_geometric_mean_with_zero():
    assert geometric_mean([1, 0, 4]) == 0.0


def test_geometric_mean_empty():
    assert geometric_mean([]) == 0.0


def test_rank_list():
    result = rank_list([30, 10, 20])
    assert result == [3, 1, 2]


def test_rank_list_sorted():
    result = rank_list([1, 2, 3, 4])
    assert result == [1, 2, 3, 4]


def test_normalize_weights():
    result = normalize_weights([1, 2, 3, 4])
    assert abs(sum(result) - 1.0) < 1e-9


def test_normalize_weights_zero():
    result = normalize_weights([0, 0, 0])
    assert all(v == 0 for v in result)
