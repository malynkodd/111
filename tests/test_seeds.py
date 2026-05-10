"""Tests for the 3 example sessions seeding (Step 4)."""
import pytest
from app.models import get_conn


def test_example_sessions_created(app):
    """3 example sessions should exist after app init."""
    with app.app_context():
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchall()
        conn.close()
    assert len(rows) == 3, f"Expected 3 example sessions, got {len(rows)}"


def test_example_sessions_completed(app):
    """All example sessions should have status='completed'."""
    with app.app_context():
        conn = get_conn()
        rows = conn.execute(
            "SELECT status FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchall()
        conn.close()
    assert all(r["status"] == "completed" for r in rows)


def test_example_sessions_have_scores(app):
    """Each example session should have scores for 2 rounds."""
    with app.app_context():
        conn = get_conn()
        sessions = conn.execute(
            "SELECT id FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchall()
        for sess in sessions:
            sid = sess["id"]
            rounds = conn.execute(
                "SELECT DISTINCT round_no FROM scores WHERE session_id=?", (sid,)
            ).fetchall()
            assert len(rounds) == 2, f"Session {sid} should have 2 rounds, got {len(rounds)}"
        conn.close()


def test_example_sessions_have_alternatives(app):
    """Each example session should have at least 4 alternatives."""
    with app.app_context():
        conn = get_conn()
        sessions = conn.execute(
            "SELECT id FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchall()
        for sess in sessions:
            sid = sess["id"]
            alts = conn.execute(
                "SELECT COUNT(*) AS c FROM alternatives WHERE session_id=?", (sid,)
            ).fetchone()
            assert alts["c"] >= 4, f"Session {sid} should have >=4 alternatives"
        conn.close()


def test_example_sessions_have_experts(app):
    """Each example session should have at least 4 experts."""
    with app.app_context():
        conn = get_conn()
        sessions = conn.execute(
            "SELECT id FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchall()
        for sess in sessions:
            sid = sess["id"]
            exp_count = conn.execute(
                "SELECT COUNT(*) AS c FROM experts WHERE session_id=?", (sid,)
            ).fetchone()
            assert exp_count["c"] >= 4, f"Session {sid} should have >=4 experts"
        conn.close()


def test_example_sessions_appear_in_history(client):
    """Example sessions should appear on the /sessions/history page."""
    r = client.get("/sessions/history", follow_redirects=True)
    assert r.status_code == 200
    # History redirects to index with status=completed
    assert "Завершена".encode() in r.data or "completed".encode() in r.data


def test_seeding_idempotent(app):
    """Calling seed_example_sessions again should not create duplicates."""
    with app.app_context():
        from app.services.seeds import seed_example_sessions
        seed_example_sessions()
        conn = get_conn()
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchone()["c"]
        conn.close()
    assert count == 3


def test_example_scores_locked(app):
    """All seeded scores should be locked (is_locked=1)."""
    with app.app_context():
        conn = get_conn()
        sessions = conn.execute(
            "SELECT id FROM sessions WHERE title LIKE 'EXAMPLE_%'"
        ).fetchall()
        for sess in sessions:
            sid = sess["id"]
            unlocked = conn.execute(
                "SELECT COUNT(*) AS c FROM scores WHERE session_id=? AND is_locked=0", (sid,)
            ).fetchone()
            assert unlocked["c"] == 0, f"Session {sid} has unlocked scores"
        conn.close()
