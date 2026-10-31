import os

import pytest

from app import create_app
from app.extensions import db

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://mindbridge:mindbridge@localhost:5432/mindbridge_test",
)


@pytest.fixture
def app():
    assert "test" in TEST_DATABASE_URL.rsplit("/", 1)[-1], "TEST_DATABASE_URL must point at a test database"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL})
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
