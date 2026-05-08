import pytest


def test_register_page_loads(client):
    r = client.get("/auth/register")
    assert r.status_code == 200


def test_login_page_loads(client):
    r = client.get("/auth/login")
    assert r.status_code == 200


def test_register_creates_user(client):
    r = client.post(
        "/auth/register",
        data={"username": "testuser", "password": "pass123", "role": "organizer"},
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_login_success(client):
    client.post("/auth/register", data={"username": "u1", "password": "p1", "role": "organizer"})
    r = client.post(
        "/auth/login",
        data={"username": "u1", "password": "p1"},
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_login_wrong_password(client):
    client.post("/auth/register", data={"username": "u2", "password": "correct", "role": "expert"})
    r = client.post(
        "/auth/login",
        data={"username": "u2", "password": "wrong"},
        follow_redirects=True,
    )
    assert "Невірне".encode() in r.data


def test_logout(client):
    client.post("/auth/register", data={"username": "u3", "password": "p3", "role": "observer"})
    client.post("/auth/login", data={"username": "u3", "password": "p3"})
    r = client.get("/auth/logout", follow_redirects=True)
    assert r.status_code == 200


def test_duplicate_registration(client):
    client.post("/auth/register", data={"username": "dup", "password": "p", "role": "expert"})
    r = client.post(
        "/auth/register",
        data={"username": "dup", "password": "p2", "role": "expert"},
        follow_redirects=True,
    )
    assert "вже існує".encode() in r.data


def test_create_session_requires_organizer(observer_client):
    r = observer_client.post(
        "/create",
        data={
            "title": "Test",
            "description": "desc",
            "alternatives": "A\nB",
            "experts": "E1\nE2",
            "competencies": "0.9\n0.8",
        },
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_create_session_as_organizer(organizer_client):
    r = organizer_client.post(
        "/create",
        data={
            "title": "TestSess",
            "description": "desc",
            "max_rounds": "2",
            "alternatives": "A\nB\nC",
            "experts": "E1\nE2",
            "competencies": "0.9\n0.8",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_unauthenticated_create_redirects(client):
    r = client.get("/create", follow_redirects=False)
    assert r.status_code == 302
