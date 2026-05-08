
from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
import sqlite3
from datetime import datetime
from io import BytesIO
from services.methods import (
    weighted_score_method,
    borda_method,
    condorcet_method,
    delphi_method,
    ahp_like_method,
)
from services.metrics import kendall_w_from_rankings, variation_coefficient, entropy_metric, build_rankings_from_scores
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "expert_system.db")

app = Flask(__name__)
app.secret_key = "demo-secret-key"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alternatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS experts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            competence REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            expert_id INTEGER NOT NULL,
            alternative_id INTEGER NOT NULL,
            round_no INTEGER NOT NULL DEFAULT 1,
            score REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (expert_id) REFERENCES experts(id),
            FOREIGN KEY (alternative_id) REFERENCES alternatives(id)
        );
        """
    )
    conn.commit()
    conn.close()


def seed_demo() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM sessions")
    if cur.fetchone()["c"] > 0:
        conn.close()
        return

    cur.execute(
        "INSERT INTO sessions (title, description, created_at) VALUES (?, ?, ?)",
        (
            "Вибір платформи цифрового врядування",
            "Демонстраційна сесія колективного експертного оцінювання з чотирма альтернативами.",
            datetime.now().strftime("%Y-%m-%d %H:%M"),
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


def session_summary(session_id: int):
    conn = get_conn()
    cur = conn.cursor()

    session = cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    alternatives = cur.execute("SELECT * FROM alternatives WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
    experts = cur.execute("SELECT * FROM experts WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
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
    conn.close()

    alt_names = [row["name"] for row in alternatives]
    expert_data = [{"id": e["id"], "name": e["full_name"], "weight": e["competence"]} for e in experts]
    round_map = {}
    for row in scores:
        round_map.setdefault(row["round_no"], {}).setdefault(row["expert_id"], {})[row["alternative_name"]] = row["score"]

    methods = {}
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
    else:
        w = 0.0
        cv = {}
        ent = {}

    return session, alternatives, experts, scores, methods, w, cv, ent


@app.route("/")
def index():
    conn = get_conn()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", sessions=sessions)


@app.route("/session/<int:session_id>")
def session_view(session_id: int):
    session, alternatives, experts, scores, methods, w, cv, ent = session_summary(session_id)
    return render_template(
        "session.html",
        session=session,
        alternatives=alternatives,
        experts=experts,
        scores=scores,
        methods=methods,
        kendall_w=w,
        cv=cv,
        entropy=ent,
    )


@app.route("/create", methods=["GET", "POST"])
def create_session():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        alternatives = [v.strip() for v in request.form["alternatives"].splitlines() if v.strip()]
        experts = [v.strip() for v in request.form["experts"].splitlines() if v.strip()]
        competencies = [v.strip() for v in request.form["competencies"].splitlines() if v.strip()]

        if not title or len(alternatives) < 2 or len(experts) < 2 or len(experts) != len(competencies):
            flash("Перевірте дані: потрібно щонайменше 2 альтернативи, 2 експерти і однакова кількість ваг.")
            return redirect(url_for("create_session"))

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (title, description, created_at) VALUES (?, ?, ?)",
            (title, description, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        session_id = cur.lastrowid
        alt_ids = []
        for alt in alternatives:
            cur.execute("INSERT INTO alternatives (session_id, name) VALUES (?, ?)", (session_id, alt))
            alt_ids.append(cur.lastrowid)
        expert_ids = []
        for name, comp in zip(experts, competencies):
            cur.execute(
                "INSERT INTO experts (session_id, full_name, competence) VALUES (?, ?, ?)",
                (session_id, name, float(comp)),
            )
            expert_ids.append(cur.lastrowid)

        for expert_id in expert_ids:
            for alt_id in alt_ids:
                cur.execute(
                    "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?, ?, ?, 1, 0)",
                    (session_id, expert_id, alt_id),
                )
        conn.commit()
        conn.close()
        return redirect(url_for("session_view", session_id=session_id))

    return render_template("create.html")


@app.route("/score/<int:session_id>", methods=["POST"])
def update_scores(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    round_no = int(request.form.get("round_no", "1"))
    cur.execute("DELETE FROM scores WHERE session_id = ? AND round_no = ?", (session_id, round_no))
    expert_ids = [row["id"] for row in cur.execute("SELECT id FROM experts WHERE session_id = ?", (session_id,)).fetchall()]
    alt_ids = [row["id"] for row in cur.execute("SELECT id FROM alternatives WHERE session_id = ?", (session_id,)).fetchall()]
    for expert_id in expert_ids:
        for alt_id in alt_ids:
            key = f"score_{expert_id}_{alt_id}"
            score = float(request.form.get(key, "0"))
            cur.execute(
                "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?, ?, ?, ?, ?)",
                (session_id, expert_id, alt_id, round_no, score),
            )
    conn.commit()
    conn.close()
    return redirect(url_for("session_view", session_id=session_id))


@app.route("/report/<int:session_id>")
def report(session_id: int):
    session, alternatives, experts, scores, methods, w, cv, ent = session_summary(session_id)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    pdf.setFont("Arial-Bold", 14)
    pdf.drawString(40, y, "Звіт сесії експертного оцінювання")
    y -= 25
    pdf.setFont("Arial", 11)
    pdf.drawString(40, y, f"Назва: {session['title']}")
    y -= 20
    pdf.drawString(40, y, f"Опис: {session['description'][:95]}")
    y -= 25
    pdf.drawString(40, y, f"Коефіцієнт конкордації Кендалла W: {w:.3f}")
    y -= 25

    for method_name, result in methods.items():
        pdf.setFont("Arial-Bold", 12)
        pdf.drawString(40, y, method_name)
        y -= 18
        pdf.setFont("Arial", 11)
        for alt_name, value in result["scores"].items():
            pdf.drawString(55, y, f"{alt_name}: {value:.3f}")
            y -= 15
        pdf.drawString(55, y, f"Рекомендована альтернатива: {result['winner']}")
        y -= 22
        if y < 100:
            pdf.showPage()
            y = height - 50

    pdf.setFont("Arial-Bold", 12)
    pdf.drawString(40, y, "Додаткові показники")
    y -= 18
    pdf.setFont("Arial", 11)
    for alt in cv:
        pdf.drawString(55, y, f"{alt} - CV={cv[alt]:.3f}, H={ent[alt]:.3f}")
        y -= 15

    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"session_{session_id}_report.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    init_db()
    seed_demo()
    app.run(debug=True, port=5000)
