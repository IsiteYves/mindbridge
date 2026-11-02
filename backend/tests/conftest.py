import os

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("TEST_DATABASE_URL is not set (see .env.example)")
    if "test" not in database_url.rsplit("/", 1)[-1]:
        pytest.fail("TEST_DATABASE_URL must point at a database whose name contains 'test'")

    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key-long-enough-for-hs256", "SQLALCHEMY_DATABASE_URI": database_url})
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
