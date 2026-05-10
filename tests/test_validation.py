import pytest
from app.services.validation import validate_score_range, validate_scores_complete


def test_score_range_valid():
    ok, _ = validate_score_range(5.0)
    assert ok


def test_score_range_below_zero():
    ok, msg = validate_score_range(-1)
    assert not ok
    assert msg


def test_score_range_above_ten():
    ok, msg = validate_score_range(11)
    assert not ok
    assert msg


def test_score_range_boundary():
    assert validate_score_range(0)[0]
    assert validate_score_range(10)[0]


def test_score_range_non_numeric():
    ok, msg = validate_score_range("abc")
    assert not ok
    assert msg


def test_scores_complete_all_filled():
    score_map = {
        (1, 100, 1): 8.0,
        (1, 200, 1): 7.0,
        (2, 100, 1): 6.0,
        (2, 200, 1): 9.0,
    }
    errors = validate_scores_complete([1, 2], [100, 200], score_map, round_no=1)
    assert errors == []


def test_scores_complete_missing_pair():
    score_map = {(1, 100, 1): 8.0, (1, 200, 1): 7.0}
    errors = validate_scores_complete([1, 2], [100, 200], score_map, round_no=1)
    assert len(errors) == 2  # both pairs for expert 2


def test_scores_complete_zero_treated_as_missing():
    score_map = {(1, 100, 1): 0, (1, 200, 1): 7.0}
    errors = validate_scores_complete([1], [100, 200], score_map, round_no=1)
    assert len(errors) == 1
