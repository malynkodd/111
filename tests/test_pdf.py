import pytest
from io import BytesIO
from app.services.pdf_report import generate_report


def _sample_data():
    return {
        "session": {
            "id": 1,
            "title": "Тест PDF",
            "description": "Опис тест",
            "created_at": "2025-01-01 12:00",
            "status": "active",
        },
        "alternatives": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}],
        "experts": [
            {"id": 1, "full_name": "Exp 1", "competence": 0.9},
            {"id": 2, "full_name": "Exp 2", "competence": 0.8},
        ],
        "methods": {
            "Зважений бал": {"scores": {"A": 8.1, "B": 7.5, "C": 6.9}, "winner": "A", "ranking": ["A", "B", "C"]},
            "Борда": {"scores": {"A": 3.0, "B": 2.5, "C": 1.5}, "winner": "A", "ranking": ["A", "B", "C"]},
        },
        "kendall_w": 0.75,
        "cv": {"A": 0.1, "B": 0.12, "C": 0.15},
        "entropy": {"A": 1.5, "B": 1.6, "C": 1.4},
        "corr_matrix": {
            "Зважений бал": {"Зважений бал": {"tau": 1.0, "rho": 1.0}, "Борда": {"tau": 0.8, "rho": 0.85}},
            "Борда": {"Зважений бал": {"tau": 0.8, "rho": 0.85}, "Борда": {"tau": 1.0, "rho": 1.0}},
        },
        "outliers": [],
        "consensus": ["A", "B", "C"],
        "kendall_w_by_round": {1: 0.6, 2: 0.75},
        "competences": [],
    }


def test_pdf_generates_non_empty():
    buf = BytesIO()
    generate_report(_sample_data(), buf)
    buf.seek(0)
    content = buf.read()
    assert len(content) > 1000


def test_pdf_is_valid_pdf():
    buf = BytesIO()
    generate_report(_sample_data(), buf)
    buf.seek(0)
    header = buf.read(4)
    assert header == b"%PDF"


def test_pdf_with_empty_methods():
    data = _sample_data()
    data["methods"] = {}
    buf = BytesIO()
    generate_report(data, buf)
    buf.seek(0)
    assert len(buf.read()) > 500


def test_pdf_with_outliers():
    data = _sample_data()
    data["outliers"] = [(1, 2.5), (2, 3.1)]
    buf = BytesIO()
    generate_report(data, buf)
    buf.seek(0)
    assert buf.read(4) == b"%PDF"
