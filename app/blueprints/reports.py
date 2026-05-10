from __future__ import annotations
from io import BytesIO

from flask import Blueprint, send_file
from app.models import session_summary
from app.services.pdf_report import generate_report
from app.blueprints.auth import login_required

bp = Blueprint("reports", __name__)


@bp.route("/report/<int:session_id>")
@login_required
def report(session_id: int):
    data = session_summary(session_id)
    buffer = BytesIO()
    generate_report(data, buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"session_{session_id}_report.pdf",
        mimetype="application/pdf",
    )
