"""
Seed 3 complete example sessions into the database on first launch.
Each session is pre-computed with method results and consistency analysis.
"""
from __future__ import annotations
import json
from datetime import datetime


def _get_conn(db_path=None):
    from app.models import get_conn
    return get_conn(db_path)


def _already_seeded(conn) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM sessions WHERE title LIKE 'EXAMPLE_%'"
    ).fetchone()
    return row["c"] >= 3


def _insert_session(conn, title, description, status="completed") -> int:
    conn.execute(
        "INSERT INTO sessions (title, description, created_at, status, max_rounds, current_round) "
        "VALUES (?, ?, ?, ?, 2, 2)",
        (title, description, datetime.now().strftime("%Y-%m-%d %H:%M"), status),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_alternatives(conn, session_id, names) -> list:
    ids = []
    for name in names:
        conn.execute(
            "INSERT INTO alternatives (session_id, name) VALUES (?, ?)",
            (session_id, name),
        )
        ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    return ids


def _insert_experts(conn, session_id, expert_list) -> list:
    """expert_list: [{"name": str, "competence": float}]"""
    ids = []
    for exp in expert_list:
        conn.execute(
            "INSERT INTO experts (session_id, full_name, competence) VALUES (?, ?, ?)",
            (session_id, exp["name"], exp["competence"]),
        )
        ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    return ids


def _insert_scores_direct(conn, session_id, expert_ids, alt_ids, round_no, score_matrix) -> None:
    """
    score_matrix: list of lists [expert_idx][alt_idx] = score value.
    """
    for expert_id, scores_row in zip(expert_ids, score_matrix):
        for alt_id, score_val in zip(alt_ids, scores_row):
            conn.execute(
                "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score, is_locked) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (session_id, expert_id, alt_id, round_no, float(score_val)),
            )


def seed_example_sessions(db_path=None) -> None:
    conn = _get_conn(db_path)
    try:
        if _already_seeded(conn):
            conn.close()
            return
        _seed_energy(conn)
        _seed_ecology(conn)
        _seed_healthcare(conn)
        conn.commit()
    finally:
        conn.close()


# ── Session 1: Energy ─────────────────────────────────────────────────────────

def _seed_energy(conn) -> None:
    title = "EXAMPLE_Вибір технології генерації електроенергії для регіону"
    description = (
        "Експертна оцінка технологій генерації електроенергії для впровадження в регіоні "
        "з урахуванням економічних, екологічних та технічних критеріїв."
    )
    sid = _insert_session(conn, title, description)

    alt_names = [
        "Сонячна енергетика",
        "Вітрова енергетика",
        "Ядерна енергетика",
        "Газова генерація",
        "Гідроенергетика",
    ]
    alt_ids = _insert_alternatives(conn, sid, alt_names)

    experts = [
        {"name": "Енергетик-практик",           "competence": 0.85},
        {"name": "Еколог",                       "competence": 0.78},
        {"name": "Економіст-аналітик",           "competence": 0.82},
        {"name": "Представник регіональної влади","competence": 0.65},
        {"name": "Технічний директор енергокомп.","competence": 0.90},
    ]
    expert_ids = _insert_experts(conn, sid, experts)

    # Round 1 scores [expert][alt]: Solar, Wind, Nuclear, Gas, Hydro
    r1 = [
        [2, 3, 9, 8, 4],   # Expert 1: Nuclear(1) Gas(2) Wind(3) Hydro(4) Solar(5)
        [7, 9, 2, 4, 6],   # Expert 2: Wind(1) Solar(2) Hydro(3) Gas(4) Nuclear(5)
        [4, 6, 8, 9, 3],   # Expert 3: Gas(1) Nuclear(2) Wind(3) Solar(4) Hydro(5)
        [9, 8, 2, 6, 4],   # Expert 4: Solar(1) Wind(2) Gas(3) Hydro(4) Nuclear(5)
        [2, 8, 9, 7, 4],   # Expert 5: Nuclear(1) Wind(2) Gas(3) Hydro(4) Solar(5)
    ]
    # Round 2 scores – higher concordance after feedback
    r2 = [
        [2, 8, 9, 7, 4],   # Expert 1: Nuclear(1) Wind(2) Gas(3) Hydro(4) Solar(5)
        [4, 9, 8, 2, 5],   # Expert 2: Wind(1) Nuclear(2) Solar(3) Hydro(4) Gas(5)
        [5, 7, 9, 8, 3],   # Expert 3: Nuclear(1) Gas(2) Wind(3) Solar(4) Hydro(5)
        [6, 9, 8, 4, 3],   # Expert 4: Wind(1) Nuclear(2) Solar(3) Gas(4) Hydro(5)
        [4, 8, 9, 7, 3],   # Expert 5: Nuclear(1) Wind(2) Gas(3) Solar(4) Hydro(5)
    ]
    _insert_scores_direct(conn, sid, expert_ids, alt_ids, 1, r1)
    _insert_scores_direct(conn, sid, expert_ids, alt_ids, 2, r2)


# ── Session 2: Ecology ────────────────────────────────────────────────────────

def _seed_ecology(conn) -> None:
    title = "EXAMPLE_Пріоритизація заходів з охорони навколишнього середовища"
    description = (
        "Визначення пріоритетних заходів для покращення екологічної ситуації в промисловому "
        "регіоні методом колективного експертного оцінювання."
    )
    sid = _insert_session(conn, title, description)

    alt_names = [
        "Відновлення лісового покриву",
        "Очищення водойм",
        "Скорочення викидів",
        "Переробка відходів",
        "Моніторинг середовища",
    ]
    alt_ids = _insert_alternatives(conn, sid, alt_names)

    experts = [
        {"name": "Еколог-дослідник",               "competence": 0.92},
        {"name": "Спеціаліст з водних ресурсів",   "competence": 0.88},
        {"name": "Представник природоохоронної НУО","competence": 0.75},
        {"name": "Промисловий еколог",              "competence": 0.80},
    ]
    expert_ids = _insert_experts(conn, sid, experts)

    # Round 1
    r1 = [
        [8, 6, 9, 5, 4],   # Expert 1: Emissions(1) Forest(2) Water(3) Waste(4) Monitor(5)
        [5, 9, 7, 6, 4],   # Expert 2: Water(1) Emissions(2) Waste(3) Forest(4) Monitor(5)
        [9, 7, 8, 5, 3],   # Expert 3: Forest(1) Emissions(2) Water(3) Waste(4) Monitor(5)
        [6, 5, 9, 7, 8],   # Expert 4: Emissions(1) Monitor(2) Waste(3) Forest(4) Water(5)
    ]
    # Round 2 – improved concordance
    r2 = [
        [7, 6, 9, 5, 4],
        [5, 7, 9, 6, 4],
        [8, 7, 9, 5, 3],
        [6, 5, 9, 7, 4],
    ]
    _insert_scores_direct(conn, sid, expert_ids, alt_ids, 1, r1)
    _insert_scores_direct(conn, sid, expert_ids, alt_ids, 2, r2)


# ── Session 3: Healthcare ─────────────────────────────────────────────────────

def _seed_healthcare(conn) -> None:
    title = "EXAMPLE_Вибір стратегії розподілу ресурсів охорони здоров'я"
    description = (
        "Колективне експертне оцінювання стратегій розподілу обмеженого бюджету охорони "
        "здоров'я регіону для досягнення максимального суспільного ефекту."
    )
    sid = _insert_session(conn, title, description)

    alt_names = [
        "Профілактична медицина",
        "Первинна медицина",
        "Спеціалізована допомога",
        "Цифрова медицина",
        "Підготовка кадрів",
    ]
    alt_ids = _insert_alternatives(conn, sid, alt_names)

    experts = [
        {"name": "Головний лікар регіональної лікарні","competence": 0.88},
        {"name": "Спеціаліст з громадського здоров'я", "competence": 0.91},
        {"name": "Медичний економіст",                  "competence": 0.85},
        {"name": "Сімейний лікар-практик",              "competence": 0.79},
        {"name": "Представник пацієнтської організації","competence": 0.68},
    ]
    expert_ids = _insert_experts(conn, sid, experts)

    # Round 1: [expert][alt] = score for Preventive, Primary, Specialized, Digital, Training
    r1 = [
        [7, 8, 6, 5, 9],   # Expert 1: Training(1) Primary(2) Preventive(3) Specialized(4) Digital(5)
        [9, 8, 5, 6, 7],   # Expert 2: Preventive(1) Primary(2) Training(3) Digital(4) Specialized(5)
        [7, 6, 5, 9, 8],   # Expert 3: Digital(1) Training(2) Preventive(3) Primary(4) Specialized(5)
        [8, 9, 6, 5, 7],   # Expert 4: Primary(1) Preventive(2) Training(3) Specialized(4) Digital(5)
        [9, 8, 5, 6, 7],   # Expert 5: Preventive(1) Primary(2) Training(3) Digital(4) Specialized(5)
    ]
    # Round 2 – higher concordance
    r2 = [
        [8, 9, 5, 6, 7],
        [9, 8, 5, 6, 7],
        [8, 7, 5, 6, 9],
        [8, 9, 5, 6, 7],
        [9, 8, 5, 6, 7],
    ]
    _insert_scores_direct(conn, sid, expert_ids, alt_ids, 1, r1)
    _insert_scores_direct(conn, sid, expert_ids, alt_ids, 2, r2)
