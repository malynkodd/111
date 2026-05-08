from __future__ import annotations
import os
import secrets
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KEY_FILE = os.path.join(_APP_DIR, ".secret_key")


def _get_secret_key() -> str:
    """Return a stable secret key: env var > .secret_key file > generate & persist."""
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE) as f:
            key = f.read().strip()
        if key:
            return key
    key = secrets.token_hex(32)
    try:
        with open(_KEY_FILE, "w") as f:
            f.write(key)
    except OSError:
        pass
    return key


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
    )
    app.secret_key = _get_secret_key()

    if db_path:
        app.config["DB_PATH"] = db_path

    from app.models import init_db, seed_demo, DB_PATH
    _db = db_path or DB_PATH
    init_db(_db)
    seed_demo(_db)

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.sessions import bp as sessions_bp
    from app.blueprints.scoring import bp as scoring_bp
    from app.blueprints.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(scoring_bp)
    app.register_blueprint(reports_bp)

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    return app
