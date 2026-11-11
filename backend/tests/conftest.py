import os

import pytest

from app import create_app
from app.extensions import db

STRONG_PASSWORD = "Sturdy-pass1"


@pytest.fixture
def app():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("TEST_DATABASE_URL is not set (see .env.example)")
    if "test" not in database_url.rsplit("/", 1)[-1]:
        pytest.fail("TEST_DATABASE_URL must point at a database whose name contains 'test'")

    sent_codes = []
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-long-enough-for-hs256",
            "SQLALCHEMY_DATABASE_URI": database_url,
            # Replaces SMTP so tests can read the codes that would have been emailed.
            "MAILER": lambda to, purpose, code: sent_codes.append({"to": to, "purpose": purpose, "code": code}),
            "SENT_CODES": sent_codes,
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user_headers(client, app):
    """Register, verify through the emailed code, and return Bearer headers for a new account."""

    def _make(name):
        email = f"{name}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={"name": name, "email": email, "password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD},
        )
        code = app.config["SENT_CODES"][-1]["code"]
        token = client.post("/api/v1/auth/verify-email", json={"email": email, "code": code}).get_json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
