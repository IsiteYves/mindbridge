import pytest

from app import create_app


def test_a_missing_secret_key_refuses_to_boot():
    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app({"SECRET_KEY": ""})


def test_a_short_secret_key_refuses_to_boot():
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        create_app({"SECRET_KEY": "too-short"})


def test_a_secret_key_exactly_at_the_minimum_length_boots():
    app = create_app({"SECRET_KEY": "x" * 32, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert app is not None


def test_a_secret_key_one_character_under_the_minimum_is_rejected():
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        create_app({"SECRET_KEY": "x" * 31})