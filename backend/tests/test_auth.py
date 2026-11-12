import datetime as dt
import secrets

import jwt
import pytest
from flask import g

from app.api.auth import token_required
from app.extensions import db
from app.models import User

PASSWORD = "Sturdy-pass1"
EMAIL = "student1@example.com"


def register(client, email=EMAIL, password=PASSWORD, confirm=None, name="Student One"):
    payload = {"name": name, "email": email, "password": password, "confirm_password": password if confirm is None else confirm}
    return client.post("/api/v1/auth/register", json=payload)


def verify(client, code, email=EMAIL):
    return client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def sent_code(app, purpose="signup", to=EMAIL):
    matches = [m for m in app.config["SENT_CODES"] if m["purpose"] == purpose and m["to"] == to]
    return matches[-1]["code"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def verified_user(app, client, email=EMAIL):
    register(client, email=email)
    verify(client, sent_code(app), email=email)


@pytest.fixture
def secure_client(app, client):
    @app.get("/secure")
    @token_required
    def secure():
        return {"email": g.current_user.email}

    return client


def test_register_sends_a_code_and_stores_a_hash(app, client):
    response = register(client)

    assert response.status_code == 201
    user = db.session.query(User).filter_by(email=EMAIL).one()
    assert user.email_verified is False
    assert user.password_hash != PASSWORD
    assert len(sent_code(app)) == 6


def test_email_is_normalized_to_lowercase(client):
    response = register(client, email="  Student1@Example.COM ")

    assert response.get_json()["email"] == EMAIL


@pytest.mark.parametrize(
    "password, fragment",
    [
        ("Ab1!", "at least 6 characters"),
        ("sturdy-pass1", "an uppercase letter"),
        ("STURDY-PASS1", "a lowercase letter"),
        ("Sturdypass1", "a special character"),
    ],
)
def test_register_rejects_weak_passwords(client, password, fragment):
    response = register(client, password=password)

    assert response.status_code == 400
    assert fragment in response.get_json()["error"]


def test_register_rejects_mismatched_confirmation(client):
    response = register(client, confirm="Sturdy-pass2")

    assert response.status_code == 400
    assert "do not match" in response.get_json()["error"]


@pytest.mark.parametrize("email", ["", "not-an-email", "a@b", "a b@c.d"])
def test_register_rejects_invalid_email(client, email):
    assert register(client, email=email).status_code == 400


def test_register_requires_a_name(client):
    assert register(client, name="   ").status_code == 400


def test_register_rejects_non_json_body(client):
    response = client.post("/api/v1/auth/register", data="not json", content_type="text/plain")

    assert response.status_code == 400


def test_register_rejects_duplicate_email(client):
    register(client)

    response = register(client)

    assert response.status_code == 409


def test_login_is_refused_until_the_email_is_verified(client):
    register(client)

    response = login(client)

    assert response.status_code == 403


def test_verify_email_with_correct_code_returns_a_token(app, client):
    register(client)

    response = verify(client, sent_code(app))

    assert response.status_code == 200
    assert response.get_json()["token"]
    assert db.session.query(User).filter_by(email=EMAIL).one().email_verified is True


def test_wrong_code_is_rejected(app, client):
    register(client)
    wrong = "000000" if sent_code(app) != "000000" else "111111"

    response = verify(client, wrong)

    assert response.status_code == 400


def test_code_is_locked_after_five_wrong_attempts(app, client):
    register(client)
    wrong = "000000" if sent_code(app) != "000000" else "111111"
    for _ in range(5):
        verify(client, wrong)

    response = verify(client, sent_code(app))

    assert response.status_code == 400


def test_code_cannot_be_used_twice(app, client):
    register(client)
    code = sent_code(app)
    verify(client, code)

    assert login(client).status_code == 200
    assert verify(client, code).status_code == 400


def test_expired_code_is_rejected(app, client):
    register(client)
    user = db.session.query(User).filter_by(email=EMAIL).one()
    from app.models import VerificationCode

    record = db.session.query(VerificationCode).filter_by(user_id=user.id).one()
    record.expires_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
    db.session.commit()

    assert verify(client, sent_code(app)).status_code == 400


def test_resend_is_rate_limited_by_cooldown(app, client):
    register(client)

    response = client.post("/api/v1/auth/resend-code", json={"email": EMAIL})

    assert response.status_code == 429
    assert len([m for m in app.config["SENT_CODES"] if m["purpose"] == "signup"]) == 1


def test_login_rejects_wrong_password_and_unknown_email_the_same_way(app, client):
    verified_user(app, client)

    wrong_password = login(client, password="Other-pass2")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()


def test_login_returns_token_with_user_subject(app, client):
    verified_user(app, client)

    response = login(client)

    assert response.status_code == 200
    payload = jwt.decode(response.get_json()["token"], app.config["SECRET_KEY"], algorithms=["HS256"])
    assert payload["sub"] == str(db.session.query(User).one().id)


def test_forgot_password_answers_the_same_for_unknown_emails(app, client):
    verified_user(app, client)

    known = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.get_json() == unknown.get_json()
    assert [m["to"] for m in app.config["SENT_CODES"] if m["purpose"] == "reset"] == [EMAIL]


def test_reset_password_changes_the_password_and_burns_the_code(app, client):
    verified_user(app, client)
    client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    code = sent_code(app, purpose="reset")
    new_password = "Fresh-pass3"

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"email": EMAIL, "code": code, "password": new_password, "confirm_password": new_password},
    )

    assert response.status_code == 200
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password=new_password).status_code == 200
    reuse = client.post(
        "/api/v1/auth/reset-password",
        json={"email": EMAIL, "code": code, "password": "Third-pass4", "confirm_password": "Third-pass4"},
    )
    assert reuse.status_code == 400


def test_reset_password_enforces_the_password_rules(app, client):
    verified_user(app, client)
    client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"email": EMAIL, "code": sent_code(app, purpose="reset"), "password": "weak", "confirm_password": "weak"},
    )

    assert response.status_code == 400


def test_logout_returns_ok(client):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200


def test_protected_route_accepts_valid_token(app, secure_client):
    verified_user(app, secure_client)
    token = login(secure_client).get_json()["token"]

    response = secure_client.get("/secure", headers=bearer(token))

    assert response.status_code == 200
    assert response.get_json() == {"email": EMAIL}


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
    verified_user(app, secure_client)
    user = db.session.query(User).one()
    expired = jwt.encode(
        {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)},
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )

    response = secure_client.get("/secure", headers=bearer(expired))

    assert response.status_code == 401


def test_protected_route_rejects_token_signed_with_other_key(app, secure_client):
    verified_user(app, secure_client)
    user = db.session.query(User).one()
    forged = jwt.encode(
        {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)},
        "another-secret-key-long-enough-for-hs256",
        algorithm="HS256",
    )

    response = secure_client.get("/secure", headers=bearer(forged))

    assert response.status_code == 401


def test_protected_route_rejects_token_for_deleted_user(app, secure_client):
    verified_user(app, secure_client)
    token = login(secure_client).get_json()["token"]
    db.session.delete(db.session.query(User).one())
    db.session.commit()

    response = secure_client.get("/secure", headers=bearer(token))

    assert response.status_code == 401
