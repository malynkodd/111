import os
import tempfile
import pytest
from app import create_app


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    application = create_app(db_path=db_path)
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    yield application
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def organizer_client(client):
    client.post("/auth/register", data={"username": "org1", "password": "pass123", "role": "organizer"})
    client.post("/auth/login", data={"username": "org1", "password": "pass123"})
    return client


@pytest.fixture
def expert_client(client):
    client.post("/auth/register", data={"username": "exp1", "password": "pass123", "role": "expert"})
    client.post("/auth/login", data={"username": "exp1", "password": "pass123"})
    return client


@pytest.fixture
def observer_client(client):
    client.post("/auth/register", data={"username": "obs1", "password": "pass123", "role": "observer"})
    client.post("/auth/login", data={"username": "obs1", "password": "pass123"})
    return client
