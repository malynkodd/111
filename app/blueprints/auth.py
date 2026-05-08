from __future__ import annotations
from functools import wraps
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import get_conn

bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Decorators ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Будь ласка, увійдіть у систему.")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Будь ласка, увійдіть у систему.")
                return redirect(url_for("auth.login", next=request.path))
            if session.get("role") not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Routes ────────────────────────────────────────────────────────────────────

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form.get("role", "observer")
        if role not in ("organizer", "expert", "observer"):
            role = "observer"
        if not username or not password:
            flash("Введіть ім'я користувача та пароль.")
            return redirect(url_for("auth.register"))
        conn = get_conn()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            flash("Такий користувач вже існує.")
            return redirect(url_for("auth.register"))
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        conn.commit()
        conn.close()
        flash("Реєстрацію завершено. Увійдіть у систему.")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or request.form.get("next") or url_for("sessions.index")
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(next_url)
        flash("Невірне ім'я користувача або пароль.")
        return redirect(url_for("auth.login", next=next_url))
    return render_template("auth/login.html", next=next_url)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
