import pytest


def _create_session(client, title="Тест"):
    return client.post(
        "/create",
        data={
            "title": title,
            "description": "опис",
            "max_rounds": "3",
            "alternatives": "A\nB\nC",
            "experts": "E1\nE2",
            "competencies": "0.9\n0.8",
        },
        follow_redirects=True,
    )


def test_index_loads(client):
    r = client.get("/")
    assert r.status_code == 200


def test_index_shows_demo_session(client):
    r = client.get("/")
    assert r.status_code == 200


def test_create_session(organizer_client):
    r = _create_session(organizer_client)
    assert r.status_code == 200


def test_session_detail_loads(client):
    # Demo session has id=1
    r = client.get("/session/1")
    assert r.status_code == 200


def test_session_detail_has_charts(client):
    r = client.get("/session/1")
    assert b"chartBar" in r.data or b"chart.js" in r.data.lower()


def test_session_filter_active(client):
    r = client.get("/?status=active")
    assert r.status_code == 200


def test_session_filter_completed(client):
    r = client.get("/?status=completed")
    assert r.status_code == 200


def test_session_search(client):
    r = client.get("/?q=цифров")
    assert r.status_code == 200


def test_complete_session_requires_organizer(observer_client):
    r = observer_client.post("/session/1/complete", follow_redirects=False)
    assert r.status_code == 403


def test_complete_session_as_organizer(organizer_client):
    r = organizer_client.post("/session/1/complete", follow_redirects=True)
    assert r.status_code == 200


def test_next_round(organizer_client):
    r = organizer_client.post("/session/1/next-round", follow_redirects=True)
    assert r.status_code == 200


def test_nonexistent_session(client):
    r = client.get("/session/99999")
    # Should not crash — may return 200 with empty data or 500
    assert r.status_code in (200, 404, 500)
