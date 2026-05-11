from __future__ import annotations
from datetime import datetime
from math import ceil

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session as flask_session, flash,
)
from app.models import get_conn, session_summary
from app.blueprints.auth import login_required, role_required

bp = Blueprint("sessions", __name__)

PAGE_SIZE = 10


@bp.route("/")
def index():
    conn = get_conn()
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "all")
    sort = request.args.get("sort", "newest")
    page = max(1, int(request.args.get("page", 1)))

    query = "SELECT * FROM sessions WHERE 1=1"
    params: list = []
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
    if status_filter in ("active", "completed"):
        query += " AND status = ?"
        params.append(status_filter)

    order = "DESC" if sort == "newest" else "ASC"
    query += f" ORDER BY id {order}"

    total = conn.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]
    offset = (page - 1) * PAGE_SIZE
    query += f" LIMIT {PAGE_SIZE} OFFSET {offset}"
    sessions_list = conn.execute(query, params).fetchall()
    conn.close()

    total_pages = ceil(total / PAGE_SIZE) if total else 1
    return render_template(
        "sessions/index.html",
        sessions=sessions_list,
        search=search,
        status_filter=status_filter,
        sort=sort,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/session/<int:session_id>")
def detail(session_id: int):
    from flask import abort
    data = session_summary(session_id)
    if data["sess"] is None:
        abort(404)
    return render_template(
        "sessions/detail.html",
        **data,
        current_user_role=flask_session.get("role"),
        current_user_id=flask_session.get("user_id"),
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("organizer")
def create():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        alternatives = [v.strip() for v in request.form["alternatives"].splitlines() if v.strip()]
        experts = [v.strip() for v in request.form["experts"].splitlines() if v.strip()]
        competencies = [v.strip() for v in request.form["competencies"].splitlines() if v.strip()]
        max_rounds = int(request.form.get("max_rounds", 3))

        if not title or len(alternatives) < 2 or len(experts) < 2 or len(experts) != len(competencies):
            flash("Перевірте дані: ≥2 альтернативи, ≥2 експерти, однакова кількість ваг.")
            return redirect(url_for("sessions.create"))

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (title, description, created_at, status, max_rounds, current_round, created_by)"
            " VALUES (?, ?, ?, 'active', ?, 1, ?)",
            (title, description, datetime.now().strftime("%Y-%m-%d %H:%M"),
             max_rounds, flask_session.get("user_id")),
        )
        sess_id = cur.lastrowid
        alt_ids = []
        for alt in alternatives:
            cur.execute("INSERT INTO alternatives (session_id, name) VALUES (?, ?)", (sess_id, alt))
            alt_ids.append(cur.lastrowid)
        expert_ids = []
        for name, comp in zip(experts, competencies):
            linked_user_id = None
            display_name = name
            if "@" in name:
                parts = name.rsplit("@", 1)
                display_name = parts[0].strip()
                username = parts[1].strip()
                row = cur.execute(
                    "SELECT id FROM users WHERE username=?", (username,)
                ).fetchone()
                if row:
                    linked_user_id = row["id"]
                else:
                    flash(f"Користувача @{username} не знайдено — експерт '{display_name}' створений без прив'язки.")
            cur.execute(
                "INSERT INTO experts (session_id, full_name, competence, user_id) VALUES (?, ?, ?, ?)",
                (sess_id, display_name, float(comp), linked_user_id),
            )
            expert_ids.append(cur.lastrowid)
        for expert_id in expert_ids:
            for alt_id in alt_ids:
                cur.execute(
                    "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?, ?, ?, 1, 0)",
                    (sess_id, expert_id, alt_id),
                )
        conn.commit()
        conn.close()
        return redirect(url_for("sessions.detail", session_id=sess_id))
    return render_template("sessions/create.html")


@bp.route("/session/<int:session_id>/complete", methods=["POST"])
@login_required
@role_required("organizer")
def complete_session(session_id: int):
    conn = get_conn()
    conn.execute("UPDATE sessions SET status = 'completed' WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    flash("Сесію завершено.")
    return redirect(url_for("sessions.detail", session_id=session_id))


@bp.route("/session/<int:session_id>/next-round", methods=["POST"])
@login_required
@role_required("organizer")
def next_round(session_id: int):
    conn = get_conn()
    sess = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if sess and sess["current_round"] < sess["max_rounds"]:
        new_round = sess["current_round"] + 1
        conn.execute(
            "UPDATE sessions SET current_round = ? WHERE id = ?", (new_round, session_id)
        )
        experts = conn.execute(
            "SELECT id FROM experts WHERE session_id = ?", (session_id,)
        ).fetchall()
        alts = conn.execute(
            "SELECT id FROM alternatives WHERE session_id = ?", (session_id,)
        ).fetchall()
        for exp in experts:
            for alt in alts:
                exists = conn.execute(
                    "SELECT id FROM scores WHERE session_id=? AND expert_id=? AND alternative_id=? AND round_no=?",
                    (session_id, exp["id"], alt["id"], new_round),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?,?,?,?,0)",
                        (session_id, exp["id"], alt["id"], new_round),
                    )
        conn.commit()
        flash(f"Розпочато раунд {new_round}.")
    else:
        flash("Досягнуто максимальну кількість раундів.")
    conn.close()
    return redirect(url_for("sessions.detail", session_id=session_id))


@bp.route("/sessions/history")
def history():
    return redirect(url_for("sessions.index", status="completed"))


# Expert competence routes

@bp.route("/session/<int:session_id>/competence", methods=["GET", "POST"])
@login_required
def competence(session_id: int):
    conn = get_conn()
    experts = conn.execute(
        "SELECT * FROM experts WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    if request.method == "POST":
        role = flask_session.get("role")
        for exp in experts:
            self_key = f"self_{exp['id']}"
            peer_key = f"peer_{exp['id']}"
            if self_key in request.form or peer_key in request.form:
                self_val = float(request.form.get(self_key, 0)) / 100.0 if request.form.get(self_key) else None
                peer_val = float(request.form.get(peer_key, 0)) / 100.0 if role == "organizer" and request.form.get(peer_key) else None

                existing = conn.execute(
                    "SELECT id FROM expert_competence WHERE expert_id=? AND session_id=?",
                    (exp["id"], session_id),
                ).fetchone()
                if existing:
                    if self_val is not None:
                        conn.execute(
                            "UPDATE expert_competence SET self_assessment=? WHERE expert_id=? AND session_id=?",
                            (self_val, exp["id"], session_id),
                        )
                    if peer_val is not None:
                        conn.execute(
                            "UPDATE expert_competence SET peer_assessment=? WHERE expert_id=? AND session_id=?",
                            (peer_val, exp["id"], session_id),
                        )
                else:
                    conn.execute(
                        "INSERT INTO expert_competence (expert_id, session_id, self_assessment, peer_assessment) VALUES (?,?,?,?)",
                        (exp["id"], session_id, self_val, peer_val),
                    )
                # Recalculate final_weight
                row = conn.execute(
                    "SELECT * FROM expert_competence WHERE expert_id=? AND session_id=?",
                    (exp["id"], session_id),
                ).fetchone()
                if row:
                    sa = row["self_assessment"]
                    pa = row["peer_assessment"]
                    if sa is not None and pa is not None:
                        fw = 0.6 * sa + 0.4 * pa
                    elif sa is not None:
                        fw = sa
                    else:
                        fw = pa
                    conn.execute(
                        "UPDATE expert_competence SET final_weight=? WHERE expert_id=? AND session_id=?",
                        (fw, exp["id"], session_id),
                    )
        conn.commit()
        flash("Компетентності збережено.")
        return redirect(url_for("sessions.detail", session_id=session_id))

    competences = conn.execute(
        "SELECT * FROM expert_competence WHERE session_id=?", (session_id,)
    ).fetchall()
    conn.close()
    comp_map = {c["expert_id"]: c for c in competences}
    return render_template(
        "sessions/competence.html",
        session_id=session_id,
        experts=experts,
        comp_map=comp_map,
        current_user_role=flask_session.get("role"),
    )


# Round feedback routes

@bp.route("/feedback/<int:session_id>/<int:round_no>")
@login_required
def feedback(session_id: int, round_no: int):
    from app.services.metrics import round_statistics
    conn = get_conn()
    sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    alts = conn.execute(
        "SELECT * FROM alternatives WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    alt_names = [a["name"] for a in alts]
    experts = conn.execute(
        "SELECT * FROM experts WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()

    scores_raw = conn.execute(
        """SELECT s.*, a.name AS alt_name
           FROM scores s JOIN alternatives a ON a.id=s.alternative_id
           WHERE s.session_id=? AND s.round_no=?""",
        (session_id, round_no),
    ).fetchall()
    scores_dict: dict = {}
    for row in scores_raw:
        scores_dict.setdefault(row["expert_id"], {})[row["alt_name"]] = row["score"]

    stats = round_statistics(scores_dict, alt_names)

    user_id = flask_session.get("user_id")
    my_expert = conn.execute(
        "SELECT * FROM experts WHERE session_id=? AND user_id=?", (session_id, user_id)
    ).fetchone()

    my_scores = {}
    if my_expert:
        my_scores = scores_dict.get(my_expert["id"], {})
        existing_fb = conn.execute(
            "SELECT * FROM round_feedback WHERE session_id=? AND expert_id=? AND round_no=?",
            (session_id, my_expert["id"], round_no),
        ).fetchone()
        if not existing_fb:
            from datetime import datetime as dt
            conn.execute(
                "INSERT INTO round_feedback (session_id, expert_id, round_no, viewed_at) VALUES (?,?,?,?)",
                (session_id, my_expert["id"], round_no, dt.now().strftime("%Y-%m-%d %H:%M")),
            )
            conn.commit()

    # Count ready experts
    total_experts = len(experts)
    ready_count = conn.execute(
        "SELECT COUNT(*) FROM round_feedback WHERE session_id=? AND round_no=? AND ready_for_next=1",
        (session_id, round_no),
    ).fetchone()[0]
    viewed_count = conn.execute(
        "SELECT COUNT(*) FROM round_feedback WHERE session_id=? AND round_no=? AND viewed_at IS NOT NULL",
        (session_id, round_no),
    ).fetchone()[0]

    conn.close()
    return render_template(
        "scoring/feedback.html",
        sess=sess,
        session_id=session_id,
        round_no=round_no,
        alt_names=alt_names,
        stats=stats,
        my_scores=my_scores,
        my_expert=my_expert,
        total_experts=total_experts,
        ready_count=ready_count,
        viewed_count=viewed_count,
        current_user_role=flask_session.get("role"),
    )


@bp.route("/feedback/<int:session_id>/<int:round_no>/ready", methods=["POST"])
@login_required
def mark_ready(session_id: int, round_no: int):
    user_id = flask_session.get("user_id")
    conn = get_conn()
    expert = conn.execute(
        "SELECT * FROM experts WHERE session_id=? AND user_id=?", (session_id, user_id)
    ).fetchone()
    if expert:
        comment = request.form.get("comment", "")
        existing_fb = conn.execute(
            "SELECT id FROM round_feedback WHERE session_id=? AND expert_id=? AND round_no=?",
            (session_id, expert["id"], round_no),
        ).fetchone()
        if existing_fb:
            conn.execute(
                "UPDATE round_feedback SET ready_for_next=1, comment=? WHERE id=?",
                (comment, existing_fb["id"]),
            )
        else:
            from datetime import datetime as dt
            conn.execute(
                "INSERT INTO round_feedback (session_id, expert_id, round_no, ready_for_next, comment, viewed_at) VALUES (?,?,?,1,?,?)",
                (session_id, expert["id"], round_no, comment, dt.now().strftime("%Y-%m-%d %H:%M")),
            )
        conn.commit()
        flash("Готовність до наступного раунду підтверджено.")
    conn.close()
    return redirect(url_for("sessions.feedback", session_id=session_id, round_no=round_no))


@bp.route("/session/<int:session_id>/link-expert", methods=["POST"])
@login_required
@role_required("organizer")
def link_expert(session_id: int):
    expert_id = int(request.form["expert_id"])
    username = request.form.get("username", "").strip()
    conn = get_conn()

    expert = conn.execute(
        "SELECT id FROM experts WHERE id=? AND session_id=?", (expert_id, session_id)
    ).fetchone()
    if not expert:
        conn.close()
        flash("Експерта не знайдено.")
        return redirect(url_for("sessions.detail", session_id=session_id))

    if username:
        user = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not user:
            conn.close()
            flash(f"Користувача @{username} не знайдено.")
            return redirect(url_for("sessions.detail", session_id=session_id))
        conn.execute("UPDATE experts SET user_id=? WHERE id=?", (user["id"], expert_id))
        flash(f"Експерта прив'язано до акаунту @{username}.")
    else:
        conn.execute("UPDATE experts SET user_id=NULL WHERE id=?", (expert_id,))
        flash("Прив'язку до акаунту знято.")

    conn.commit()
    conn.close()
    return redirect(url_for("sessions.detail", session_id=session_id))
