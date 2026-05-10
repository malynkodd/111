"""Tests for the response locking feature (Step 5)."""
import pytest
from app.models import get_conn


def _setup_session(organizer_client, app):
    """Create a session with 2 alternatives and 2 experts."""
    r = organizer_client.post(
        "/create",
        data={
            "title": "Lock Test Session",
            "description": "Testing locking",
            "max_rounds": "2",
            "alternatives": "Alt A\nAlt B",
            "experts": "Expert One\nExpert Two",
            "competencies": "0.9\n0.8",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200

    with app.app_context():
        conn = get_conn()
        # Get the session just created (it will have title "Lock Test Session")
        sess = conn.execute(
            "SELECT id FROM sessions WHERE title='Lock Test Session' LIMIT 1"
        ).fetchone()
        assert sess is not None, "Session was not created — check validation"
        session_id = sess["id"]

        # Get both experts
        experts = conn.execute(
            "SELECT id FROM experts WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        expert_ids = [e["id"] for e in experts]

        alt_ids = [
            row["id"] for row in conn.execute(
                "SELECT id FROM alternatives WHERE session_id=? ORDER BY id", (session_id,)
            ).fetchall()
        ]
        conn.close()

    return session_id, expert_ids, alt_ids


@pytest.fixture
def org_client(client):
    client.post("/auth/register", data={"username": "org_lock", "password": "pass", "role": "organizer"})
    client.post("/auth/login", data={"username": "org_lock", "password": "pass"})
    return client


def test_score_submission_locks_response(org_client, app):
    """Submitting scores should set is_locked=1 on all inserted rows."""
    session_id, expert_ids, alt_ids = _setup_session(org_client, app)

    # Build POST data for all experts and alts
    post_data = {"round_no": "1"}
    for eid in expert_ids:
        for aid in alt_ids:
            post_data[f"score_{eid}_{aid}"] = "8"

    r = org_client.post(f"/score/{session_id}", data=post_data, follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        conn = get_conn()
        rows = conn.execute(
            "SELECT is_locked FROM scores WHERE session_id=? AND round_no=1 AND is_locked=1",
            (session_id,),
        ).fetchall()
        conn.close()

    assert len(rows) > 0
    assert all(row["is_locked"] == 1 for row in rows)


def test_locked_response_cannot_be_modified(org_client, app):
    """Second submission for the same round must be rejected."""
    session_id, expert_ids, alt_ids = _setup_session(org_client, app)

    post_data = {"round_no": "1"}
    for eid in expert_ids:
        for aid in alt_ids:
            post_data[f"score_{eid}_{aid}"] = "8"

    # First submission
    org_client.post(f"/score/{session_id}", data=post_data, follow_redirects=True)

    # Attempt second submission
    post_data2 = {"round_no": "1"}
    for eid in expert_ids:
        for aid in alt_ids:
            post_data2[f"score_{eid}_{aid}"] = "3"

    r = org_client.post(f"/score/{session_id}", data=post_data2, follow_redirects=True)
    assert r.status_code == 200
    assert "заблоковано".encode() in r.data or "неможлива".encode() in r.data


def test_locked_response_score_unchanged(org_client, app):
    """After rejection, original score values must be preserved."""
    session_id, expert_ids, alt_ids = _setup_session(org_client, app)
    eid = expert_ids[0]

    post_data = {"round_no": "1"}
    for e in expert_ids:
        post_data[f"score_{e}_{alt_ids[0]}"] = "9"
        post_data[f"score_{e}_{alt_ids[1]}"] = "7"

    org_client.post(f"/score/{session_id}", data=post_data, follow_redirects=True)

    # Try to change — should be rejected
    post_data2 = {"round_no": "1"}
    for e in expert_ids:
        post_data2[f"score_{e}_{alt_ids[0]}"] = "1"
        post_data2[f"score_{e}_{alt_ids[1]}"] = "1"

    org_client.post(f"/score/{session_id}", data=post_data2, follow_redirects=True)

    with app.app_context():
        conn = get_conn()
        rows = conn.execute(
            "SELECT alternative_id, score FROM scores "
            "WHERE session_id=? AND expert_id=? AND round_no=1 AND is_locked=1",
            (session_id, eid),
        ).fetchall()
        conn.close()

    score_map = {row["alternative_id"]: row["score"] for row in rows}
    assert score_map.get(alt_ids[0]) == 9.0, f"Expected 9.0, got {score_map.get(alt_ids[0])}"
    assert score_map.get(alt_ids[1]) == 7.0, f"Expected 7.0, got {score_map.get(alt_ids[1])}"


def test_submitted_at_is_set(org_client, app):
    """submitted_at should be populated for all locked scores after submission."""
    session_id, expert_ids, alt_ids = _setup_session(org_client, app)

    post_data = {"round_no": "1"}
    for eid in expert_ids:
        for aid in alt_ids:
            post_data[f"score_{eid}_{aid}"] = "8"

    org_client.post(f"/score/{session_id}", data=post_data, follow_redirects=True)

    with app.app_context():
        conn = get_conn()
        rows = conn.execute(
            "SELECT submitted_at FROM scores "
            "WHERE session_id=? AND round_no=1 AND is_locked=1",
            (session_id,),
        ).fetchall()
        conn.close()

    assert len(rows) > 0
    assert all(row["submitted_at"] is not None for row in rows)


def test_score_form_shows_lock_badge(org_client, app):
    """GET /score/<id> should show locked badge for experts already submitted."""
    session_id, expert_ids, alt_ids = _setup_session(org_client, app)

    post_data = {"round_no": "1"}
    for eid in expert_ids:
        for aid in alt_ids:
            post_data[f"score_{eid}_{aid}"] = "8"

    org_client.post(f"/score/{session_id}", data=post_data, follow_redirects=True)

    r = org_client.get(f"/score/{session_id}")
    assert r.status_code == 200
    # The template renders "Заблоковано" badge for locked experts
    assert "Заблоковано".encode() in r.data


def test_expert_role_locked_response_rejected(client, app):
    """Expert who already submitted cannot resubmit: flash message shown."""
    # Register an expert user
    client.post("/auth/register", data={"username": "expert_user", "password": "pass", "role": "expert"})
    client.post("/auth/login", data={"username": "expert_user", "password": "pass"})

    # Get the expert user's ID
    with app.app_context():
        conn = get_conn()
        user = conn.execute("SELECT id FROM users WHERE username='expert_user'").fetchone()
        user_id = user["id"]
        conn.close()

    # Register and login as organizer to create a session
    org = app.test_client()
    org.post("/auth/register", data={"username": "org_for_exp", "password": "pass", "role": "organizer"})
    org.post("/auth/login", data={"username": "org_for_exp", "password": "pass"})
    org.post(
        "/create",
        data={
            "title": "Expert Lock Test",
            "description": "desc",
            "max_rounds": "1",
            "alternatives": "X\nY",
            "experts": "Exp\nExp2",
            "competencies": "0.9\n0.8",
        },
        follow_redirects=True,
    )

    with app.app_context():
        conn = get_conn()
        sess = conn.execute(
            "SELECT id FROM sessions WHERE title='Expert Lock Test' LIMIT 1"
        ).fetchone()
        session_id = sess["id"]
        experts = conn.execute(
            "SELECT id FROM experts WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        alt_ids = [
            row["id"] for row in conn.execute(
                "SELECT id FROM alternatives WHERE session_id=? ORDER BY id", (session_id,)
            ).fetchall()
        ]
        # Link the expert user to the first expert in this session
        conn.execute(
            "UPDATE experts SET user_id=? WHERE id=?",
            (user_id, experts[0]["id"]),
        )
        conn.commit()
        expert_id = experts[0]["id"]
        conn.close()

    # Expert submits once
    client.post(
        f"/score/{session_id}",
        data={
            "round_no": "1",
            f"score_{expert_id}_{alt_ids[0]}": "9",
            f"score_{expert_id}_{alt_ids[1]}": "7",
        },
        follow_redirects=True,
    )

    # Expert tries to submit again
    r = client.post(
        f"/score/{session_id}",
        data={
            "round_no": "1",
            f"score_{expert_id}_{alt_ids[0]}": "1",
            f"score_{expert_id}_{alt_ids[1]}": "1",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "неможлива".encode() in r.data or "заблоковано".encode() in r.data.lower()
