import datetime as dt
import secrets

import jwt
import pytest
from flask import g

from app.api.auth import token_required
from app.extensions import db
from app.models import User

PASSWORD = secrets.token_urlsafe(16)


def register(client, username="student1", password=PASSWORD):
    return client.post("/api/v1/auth/register", json={"username": username, "password": password})


def login(client, username="student1", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def secure_client(app, client):
    @app.get("/secure")
    @token_required
    def secure():
        return {"username": g.current_user.username}

    return client


def test_register_creates_user_with_hashed_password(client):
    response = register(client)

    assert response.status_code == 201
    assert response.get_json()["username"] == "student1"
    user = db.session.query(User).filter_by(username="student1").one()
    assert user.password_hash != PASSWORD


def test_register_rejects_short_password(client):
    response = register(client, password="a" * 7)

    assert response.status_code == 400


def test_register_rejects_missing_username(client):
    response = register(client, username="   ")

    assert response.status_code == 400


def test_register_rejects_non_json_body(client):
    response = client.post("/api/v1/auth/register", data="not json", content_type="text/plain")

    assert response.status_code == 400


def test_register_rejects_duplicate_username(client):
    register(client)

    response = register(client)

    assert response.status_code == 409


def test_login_returns_token_for_valid_credentials(app, client):
    register(client)

    response = login(client)

    assert response.status_code == 200
    payload = jwt.decode(response.get_json()["token"], app.config["SECRET_KEY"], algorithms=["HS256"])
    assert payload["sub"] == str(db.session.query(User).one().id)


def test_login_rejects_wrong_password_and_unknown_user_the_same_way(client):
    register(client)

    wrong_password = login(client, password=secrets.token_urlsafe(16))
    unknown_user = login(client, username="nobody")

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.get_json() == unknown_user.get_json()


def test_logout_returns_ok(client):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200


def test_protected_route_accepts_valid_token(secure_client):
    register(secure_client)
    token = login(secure_client).get_json()["token"]

    response = secure_client.get("/secure", headers=bearer(token))

    assert response.status_code == 200
    assert response.get_json() == {"username": "student1"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Token abc"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
def test_protected_route_rejects_missing_or_malformed_token(secure_client, headers):
    response = secure_client.get("/secure", headers=headers)

    assert response.status_code == 401


def test_protected_route_rejects_expired_token(app, secure_client):
    register(secure_client)
    user = db.session.query(User).one()
    expired = jwt.encode(
        {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)},
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )

    response = secure_client.get("/secure", headers=bearer(expired))

    assert response.status_code == 401


def test_protected_route_rejects_token_signed_with_other_key(app, secure_client):
    register(secure_client)
    user = db.session.query(User).one()
    forged = jwt.encode(
        {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)},
        "another-secret-key-long-enough-for-hs256",
        algorithm="HS256",
    )

    response = secure_client.get("/secure", headers=bearer(forged))

    assert response.status_code == 401


def test_protected_route_rejects_token_for_deleted_user(secure_client):
    register(secure_client)
    token = login(secure_client).get_json()["token"]
    db.session.delete(db.session.query(User).one())
    db.session.commit()

    response = secure_client.get("/secure", headers=bearer(token))

    assert response.status_code == 401
