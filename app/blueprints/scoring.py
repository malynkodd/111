from __future__ import annotations
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session as flask_session, flash,
)
from app.models import get_conn
from app.blueprints.auth import login_required
from app.services.validation import check_transitivity

bp = Blueprint("scoring", __name__)


def _get_locked_expert_ids(conn, session_id: int, expert_ids: list, round_no: int) -> set:
    """Return the set of expert_ids that have a locked response for the given round."""
    locked = set()
    for eid in expert_ids:
        row = conn.execute(
            "SELECT is_locked FROM scores "
            "WHERE session_id=? AND expert_id=? AND round_no=? AND is_locked=1 LIMIT 1",
            (session_id, eid, round_no),
        ).fetchone()
        if row:
            locked.add(eid)
    return locked


@bp.route("/score/<int:session_id>", methods=["GET", "POST"])
@login_required
def score(session_id: int):
    conn = get_conn()
    sess = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not sess:
        conn.close()
        flash("Сесію не знайдено.")
        return redirect(url_for("sessions.index"))

    experts = conn.execute(
        "SELECT * FROM experts WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    alts = conn.execute(
        "SELECT * FROM alternatives WHERE session_id=? ORDER BY id", (session_id,)
    ).fetchall()
    round_no = int(sess["current_round"] or 1)

    role = flask_session.get("role")
    user_id = flask_session.get("user_id")

    if role == "organizer":
        allowed_expert_ids = [e["id"] for e in experts]
        my_expert_id = None
    elif role == "expert":
        my_expert = conn.execute(
            "SELECT id FROM experts WHERE session_id=? AND user_id=?", (session_id, user_id)
        ).fetchone()
        if not my_expert:
            conn.close()
            flash("Вас не призначено експертом у цій сесії.")
            return redirect(url_for("sessions.detail", session_id=session_id))
        my_expert_id = my_expert["id"]
        allowed_expert_ids = [my_expert_id]
    else:
        conn.close()
        flash("Немає прав для заповнення оцінок.")
        return redirect(url_for("sessions.detail", session_id=session_id))

    if request.method == "POST":
        round_no = int(request.form.get("round_no", round_no))

        # Determine which experts are already locked for this round
        locked_ids = _get_locked_expert_ids(conn, session_id, allowed_expert_ids, round_no)

        # For expert role: if already locked → reject
        if role == "expert" and my_expert_id in locked_ids:
            conn.close()
            flash("Вашу оцінку вже зараховано. Зміна оцінки після подання неможлива.", "warning")
            return redirect(url_for("scoring.score", session_id=session_id))

        # For organizer: only update scores of non-locked experts
        submittable_ids = [eid for eid in allowed_expert_ids if eid not in locked_ids]
        if not submittable_ids:
            conn.close()
            flash("Всі оцінки вже заблоковано для цього раунду.", "warning")
            return redirect(url_for("sessions.detail", session_id=session_id))

        # Check transitivity for pairwise comparisons
        pairwise: dict = {}
        for expert_id in submittable_ids:
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

        # Delete only unlocked scores and re-insert with lock
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        for expert_id in submittable_ids:
            conn.execute(
                "DELETE FROM scores WHERE session_id=? AND round_no=? AND expert_id=? AND is_locked=0",
                (session_id, round_no, expert_id),
            )
            for alt in alts:
                key = f"score_{expert_id}_{alt['id']}"
                raw = request.form.get(key, "0")
                try:
                    score_val = float(raw) if raw.strip() else 0.0
                except ValueError:
                    score_val = 0.0
                conn.execute(
                    "INSERT INTO scores (session_id, expert_id, alternative_id, round_no, score, is_locked, submitted_at) "
                    "VALUES (?,?,?,?,?,1,?)",
                    (session_id, expert_id, alt["id"], round_no, score_val, now_str),
                )

        conn.execute("UPDATE sessions SET current_round=? WHERE id=?", (round_no, session_id))
        conn.commit()
        conn.close()
        flash("Оцінки збережено та заблоковано.")
        return redirect(url_for("sessions.detail", session_id=session_id))

    # GET: load existing scores
    scores_raw = conn.execute(
        "SELECT * FROM scores WHERE session_id=? AND round_no=?", (session_id, round_no)
    ).fetchall()
    score_map: dict = {}
    for row in scores_raw:
        score_map[(row["expert_id"], row["alternative_id"])] = row["score"]

    locked_ids = _get_locked_expert_ids(conn, session_id, allowed_expert_ids, round_no)
    conn.close()

    # For expert role: compute is_locked flag for template
    is_locked = False
    if role == "expert" and my_expert_id in locked_ids:
        is_locked = True

    return render_template(
        "scoring/form.html",
        sess=sess,
        session_id=session_id,
        experts=experts,
        alts=alts,
        round_no=round_no,
        score_map=score_map,
        allowed_expert_ids=allowed_expert_ids,
        locked_ids=locked_ids,
        is_locked=is_locked,
    )
