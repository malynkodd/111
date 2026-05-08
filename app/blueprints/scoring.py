from __future__ import annotations
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session as flask_session, flash,
)
from app.models import get_conn
from app.blueprints.auth import login_required
from app.services.methods import check_transitivity

bp = Blueprint("scoring", __name__)


@bp.route("/score/<int:session_id>", methods=["GET", "POST"])
@login_required
def score(session_id: int):
    conn = get_conn()
    sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    experts = conn.execute(
        "SELECT * FROM experts WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    alts = conn.execute(
        "SELECT * FROM alternatives WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    round_no = int(sess["current_round"] or 1) if sess else 1

    if request.method == "POST":
        round_no = int(request.form.get("round_no", round_no))
        role = flask_session.get("role")
        user_id = flask_session.get("user_id")

        # Determine which experts this user can score
        if role == "organizer":
            allowed_expert_ids = [e["id"] for e in experts]
        elif role == "expert":
            my_expert = conn.execute(
                "SELECT id FROM experts WHERE session_id=? AND user_id=?", (session_id, user_id)
            ).fetchone()
            allowed_expert_ids = [my_expert["id"]] if my_expert else []
        else:
            conn.close()
            flash("Немає прав для заповнення оцінок.")
            return redirect(url_for("sessions.detail", session_id=session_id))

        conn.execute(
            "DELETE FROM scores WHERE session_id=? AND round_no=? AND expert_id IN ({})".format(
                ",".join("?" * len(allowed_expert_ids))
            ),
            [session_id, round_no] + allowed_expert_ids,
        )

        # Check transitivity for pairwise comparisons
        pairwise: dict = {}
        for expert_id in allowed_expert_ids:
            for i, alt_i in enumerate(alts):
                for j, alt_j in enumerate(alts):
                    if i >= j:
                        continue
                    pw_key = f"pw_{expert_id}_{alt_i['id']}_{alt_j['id']}"
                    pw_val = request.form.get(pw_key)
                    if pw_val is not None:
                        pairwise[(alt_i["name"], alt_j["name"])] = int(pw_val)

        if pairwise:
            is_transitive, violations = check_transitivity(pairwise)
            if not is_transitive:
                for v in violations[:3]:
                    flash(f"Попередження: порушення транзитивності — {v[0]} > {v[1]} > {v[2]}, але {v[2]} > {v[0]}.")

        for expert_id in allowed_expert_ids:
            for alt in alts:
                key = f"score_{expert_id}_{alt['id']}"
                raw = request.form.get(key, "0")
                try:
                    score_val = float(raw) if raw.strip() else 0.0
                except ValueError:
                    score_val = 0.0
                conn.execute(
                    "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score) VALUES (?,?,?,?,?)",
                    (session_id, expert_id, alt["id"], round_no, score_val),
                )
        # Update session's current_round to the round we just scored
        conn.execute("UPDATE sessions SET current_round=? WHERE id=?", (round_no, session_id))
        conn.commit()
        conn.close()
        flash("Оцінки збережено.")
        return redirect(url_for("sessions.detail", session_id=session_id))

    # Load existing scores for the form
    scores_raw = conn.execute(
        "SELECT * FROM scores WHERE session_id=? AND round_no=?", (session_id, round_no)
    ).fetchall()
    score_map: dict = {}
    for row in scores_raw:
        score_map[(row["expert_id"], row["alternative_id"])] = row["score"]
    conn.close()

    role = flask_session.get("role")
    user_id = flask_session.get("user_id")
    if role == "expert":
        conn2 = get_conn()
        my_expert = conn2.execute(
            "SELECT id FROM experts WHERE session_id=? AND user_id=?", (session_id, user_id)
        ).fetchone()
        conn2.close()
        allowed_expert_ids = [my_expert["id"]] if my_expert else []
    elif role == "organizer":
        allowed_expert_ids = [e["id"] for e in experts]
    else:
        allowed_expert_ids = []

    return render_template(
        "scoring/form.html",
        sess=sess,
        session_id=session_id,
        experts=experts,
        alts=alts,
        round_no=round_no,
        score_map=score_map,
        allowed_expert_ids=allowed_expert_ids,
    )
