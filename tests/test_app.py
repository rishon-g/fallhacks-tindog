import sqlite3

import pytest

import app as barkr


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(barkr, "DB_PATH", str(tmp_path / "test.db"))
    with barkr.app.app_context():
        barkr.bootstrap()
    barkr.app.config["TESTING"] = True
    return barkr.app.test_client()


def register(client, username, **extra):
    data = {
        "username": username,
        "password": "pw",
        "confirmation": "pw",
        "dog_name": username + "dog",
        "favorite_artist": "Drake",
    }
    data.update(extra)
    return client.post("/register", data=data)


def test_register_ignores_non_ascii_age(client):
    assert register(client, "a", dog_age="²").status_code == 302
    row = sqlite3.connect(barkr.DB_PATH).execute("SELECT age FROM dogs").fetchone()
    assert row == (None,)


def test_swipe_rejects_bad_dog_id(client):
    register(client, "a")
    resp = client.post("/swipe", data={"dog_id": "abc", "action": "like"})
    assert resp.status_code == 302


def test_swipe_rejects_own_dog(client):
    register(client, "a")
    client.post("/swipe", data={"dog_id": "1", "action": "like"})
    assert sqlite3.connect(barkr.DB_PATH).execute("SELECT COUNT(*) FROM likes").fetchone() == (0,)


def test_login_rejects_wrong_password(client):
    register(client, "a")
    resp = client.post("/login", data={"username": "a", "password": "nope"})
    assert resp.status_code == 200
    assert b"Invalid username or password." in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_logout_clears_session(client):
    register(client, "a")
    resp = client.post("/login", data={"username": "a", "password": "pw"})
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" in sess
    client.get("/logout")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
