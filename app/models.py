from __future__ import annotations
import os
import sqlite3
from datetime import datetime

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_DIR, "expert_system.db")


def get_conn(db_path: str | None = None) -> sqlite3.Connection:
    if db_path is None:
        try:
            from flask import current_app
            db_path = current_app.config.get("DB_PATH", DB_PATH)
        except RuntimeError:
            db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('organizer','expert','observer')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            max_rounds INTEGER DEFAULT 3,
            current_round INTEGER DEFAULT 1,
            created_by INTEGER REFERENCES users(id),
            method_params TEXT DEFAULT '{}',
            is_anonymous INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS alternatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS session_experts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            role TEXT NOT NULL DEFAULT 'expert',
            UNIQUE(session_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS experts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            competence REAL NOT NULL,
            user_id INTEGER REFERENCES users(id),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            expert_id INTEGER NOT NULL,
            alternative_id INTEGER NOT NULL,
            round_no INTEGER NOT NULL DEFAULT 1,
            score REAL NOT NULL,
            is_locked INTEGER NOT NULL DEFAULT 0,
            submitted_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (expert_id) REFERENCES experts(id),
            FOREIGN KEY (alternative_id) REFERENCES alternatives(id)
        );

        CREATE TABLE IF NOT EXISTS expert_competence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expert_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            self_assessment REAL,
            peer_assessment REAL,
            final_weight REAL,
            FOREIGN KEY (expert_id) REFERENCES experts(id),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS round_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            expert_id INTEGER NOT NULL,
            round_no INTEGER NOT NULL,
            viewed_at TEXT,
            comment TEXT,
            ready_for_next INTEGER DEFAULT 0
        );
        """
    )
    # Migrate existing sessions table if columns missing
    for col, definition in [
        ("status", "TEXT DEFAULT 'active'"),
        ("max_rounds", "INTEGER DEFAULT 3"),
        ("current_round", "INTEGER DEFAULT 1"),
        ("created_by", "INTEGER"),
    ]:
        try:
            cur.execute(f"ALTER TABLE sessions ADD COLUMN {col} {definition}")
        except Exception:
            pass
    # Migrate experts table
    try:
        cur.execute("ALTER TABLE experts ADD COLUMN user_id INTEGER")
    except Exception:
        pass
    # Migrate scores table — add locking columns
    for col, definition in [
        ("is_locked", "INTEGER NOT NULL DEFAULT 0"),
        ("submitted_at", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE scores ADD COLUMN {col} {definition}")
        except Exception:
            pass
    # Migrate sessions/alternatives — add spec-required columns
    for sql in [
        "ALTER TABLE sessions ADD COLUMN method_params TEXT DEFAULT '{}'",
        "ALTER TABLE sessions ADD COLUMN is_anonymous INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE alternatives ADD COLUMN description TEXT DEFAULT ''",
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


def seed_demo(db_path: str = DB_PATH) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM sessions")
    if cur.fetchone()["c"] > 0:
        conn.close()
        return

    cur.execute(
        "INSERT INTO sessions (title, description, created_at, status) VALUES (?, ?, ?, ?)",
        (
            "Вибір платформи цифрового врядування",
            "Демонстраційна сесія колективного експертного оцінювання з чотирма альтернативами.",
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            "active",
        ),
    )
    session_id = cur.lastrowid

    alternatives = [
        "Платформа A - базова",
        "Платформа B - збалансована",
        "Платформа C - аналітична",
        "Платформа D - інтегрована",
    ]
    for alt in alternatives:
        cur.execute("INSERT INTO alternatives (session_id, name) VALUES (?, ?)", (session_id, alt))

    experts = [
        ("Експерт 1", 0.95),
        ("Експерт 2", 0.90),
        ("Експерт 3", 0.85),
        ("Експерт 4", 0.80),
        ("Експерт 5", 0.88),
    ]
    for name, competence in experts:
        cur.execute(
            "INSERT INTO experts (session_id, full_name, competence) VALUES (?, ?, ?)",
            (session_id, name, competence),
        )

    cur.execute("SELECT id FROM alternatives WHERE session_id = ? ORDER BY id", (session_id,))
    alt_ids = [row["id"] for row in cur.fetchall()]
    cur.execute("SELECT id FROM experts WHERE session_id = ? ORDER BY id", (session_id,))
    expert_ids = [row["id"] for row in cur.fetchall()]

    round_1 = {
        expert_ids[0]: [8, 9, 7, 10],
        expert_ids[1]: [7, 8, 9, 9],
        expert_ids[2]: [8, 8, 7, 9],
        expert_ids[3]: [6, 8, 8, 9],
        expert_ids[4]: [7, 9, 8, 9],
    }
    round_2 = {
        expert_ids[0]: [7, 8, 8, 10],
        expert_ids[1]: [7, 8, 9, 9],
        expert_ids[2]: [7, 8, 8, 9],
        expert_ids[3]: [7, 8, 8, 9],
        expert_ids[4]: [7, 9, 8, 9],
    }

    for expert_id, values in round_1.items():
        for alt_id, score in zip(alt_ids, values):
            cur.execute(
                "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?, ?, ?, ?, ?)",
                (session_id, expert_id, alt_id, 1, score),
            )
    for expert_id, values in round_2.items():
        for alt_id, score in zip(alt_ids, values):
            cur.execute(
                "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?, ?, ?, ?, ?)",
                (session_id, expert_id, alt_id, 2, score),
            )

    conn.commit()
    conn.close()


def session_summary(session_id: int, db_path: str | None = None):
    from app.services.methods import (
        weighted_score_method, borda_method, condorcet_method,
        delphi_method, ahp_like_method,
    )
    from app.services.metrics import (
        kendall_w_from_rankings, variation_coefficient,
        entropy_metric, build_rankings_from_scores,
        methods_correlation_matrix, detect_outlier_experts,
        consensus_ranking, round_statistics, chi_squared_test,
    )

    conn = get_conn(db_path)
    cur = conn.cursor()

    session = cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    alternatives = cur.execute(
        "SELECT * FROM alternatives WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    experts = cur.execute(
        "SELECT * FROM experts WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    scores = cur.execute(
        """
        SELECT s.*, e.full_name, e.competence, a.name AS alternative_name
        FROM scores s
        JOIN experts e ON e.id = s.expert_id
        JOIN alternatives a ON a.id = s.alternative_id
        WHERE s.session_id = ?
        ORDER BY s.round_no, s.expert_id, s.alternative_id
        """,
        (session_id,),
    ).fetchall()
    competences = cur.execute(
        "SELECT * FROM expert_competence WHERE session_id = ?", (session_id,)
    ).fetchall()
    conn.close()

    alt_names = [row["name"] for row in alternatives]
    expert_data = [{"id": e["id"], "name": e["full_name"], "weight": e["competence"]} for e in experts]
    round_map: dict = {}
    for row in scores:
        round_map.setdefault(row["round_no"], {}).setdefault(row["expert_id"], {})[
            row["alternative_name"]
        ] = row["score"]

    methods: dict = {}
    w = 0.0
    cv: dict = {}
    ent: dict = {}
    corr_matrix: dict = {}
    outliers: list = []
    consensus: list = []
    round_stats: dict = {}

    if round_map:
        latest_round = max(round_map)
        latest_scores = round_map[latest_round]

        methods["Зважений середній бал"] = weighted_score_method(latest_scores, expert_data, alt_names)
        methods["Метод Борда"] = borda_method(latest_scores, expert_data, alt_names)
        methods["Метод Кондорсе"] = condorcet_method(latest_scores, expert_data, alt_names)
        methods["Метод Делфі"] = delphi_method(round_map, expert_data, alt_names)
        methods["Метод парних порівнянь"] = ahp_like_method(latest_scores, expert_data, alt_names)

        rankings = build_rankings_from_scores(latest_scores, alt_names)
        w = kendall_w_from_rankings(rankings, alt_names)
        cv = variation_coefficient(latest_scores, expert_data, alt_names)
        ent = entropy_metric(latest_scores, alt_names)
        corr_matrix = methods_correlation_matrix(methods)
        outliers = detect_outlier_experts(latest_scores, alt_names)
        consensus = consensus_ranking(methods, alt_names)
        round_stats = {
            rn: round_statistics(rscores, alt_names)
            for rn, rscores in round_map.items()
        }

    kendall_w_by_round = {}
    for rn, rscores in round_map.items():
        r = build_rankings_from_scores(rscores, alt_names)
        kendall_w_by_round[rn] = kendall_w_from_rankings(r, alt_names)

    # Chi-squared significance test for Kendall W
    chi_sq_result = chi_squared_test(w, len(experts), len(alt_names))

    # Show the round with the most recent real data, not just current_round
    display_round = max(round_map) if round_map else (session["current_round"] if session else 1)

    return dict(
        sess=session,
        alternatives=alternatives,
        experts=experts,
        scores=scores,
        competences=competences,
        methods=methods,
        kendall_w=w,
        chi_sq=chi_sq_result,
        cv=cv,
        entropy=ent,
        corr_matrix=corr_matrix,
        outliers=outliers,
        consensus=consensus,
        round_stats=round_stats,
        kendall_w_by_round=kendall_w_by_round,
        alt_names=alt_names,
        expert_data=expert_data,
        round_map=round_map,
        display_round=display_round,
    )
