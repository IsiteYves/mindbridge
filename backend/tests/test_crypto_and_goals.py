import pytest
from cryptography.fernet import Fernet

from app.services import crypto, goals


# ── crypto ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())


def test_round_trips_a_secret():
    ciphertext = crypto.encrypt_secret("canvas-token-abc123")
    assert ciphertext != "canvas-token-abc123"
    assert crypto.decrypt_secret(ciphertext) == "canvas-token-abc123"


def test_rejects_an_empty_plaintext():
    with pytest.raises(ValueError):
        crypto.encrypt_secret("")


def test_decrypting_nothing_returns_none():
    assert crypto.decrypt_secret(None) is None
    assert crypto.decrypt_secret("") is None


def test_decrypting_garbage_returns_none_rather_than_raising():
    assert crypto.decrypt_secret("not-a-real-token") is None


def test_decrypting_under_the_wrong_key_returns_none(monkeypatch):
    ciphertext = crypto.encrypt_secret("canvas-token-abc123")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert crypto.decrypt_secret(ciphertext) is None


def test_missing_key_raises_a_configuration_error(monkeypatch):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    with pytest.raises(crypto.EncryptionNotConfigured):
        crypto.encrypt_secret("canvas-token-abc123")


def test_malformed_key_raises_a_configuration_error(monkeypatch):
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "not-a-valid-fernet-key")
    with pytest.raises(crypto.EncryptionNotConfigured):
        crypto.encrypt_secret("canvas-token-abc123")


# ── goals ───────────────────────────────────────────────────────────────────


def test_progress_counts_done_items():
    items = [{"label": "a", "done": True}, {"label": "b", "done": False}, {"label": "c", "done": True}]
    assert goals.progress(items) == (2, 3)


def test_progress_of_an_empty_list_is_zero_of_zero():
    assert goals.progress([]) == (0, 0)
    assert goals.progress(None) == (0, 0)


def test_empty_goal_is_not_complete():
    assert goals.is_complete([]) is False


def test_all_done_is_complete():
    assert goals.is_complete([{"label": "a", "done": True}]) is True


def test_mark_done_does_not_mutate_the_input():
    original = [{"label": "a", "done": False}]
    updated = goals.mark_done(original, 0)
    assert original[0]["done"] is False
    assert updated[0]["done"] is True


def test_mark_done_rejects_an_out_of_range_index():
    with pytest.raises(IndexError):
        goals.mark_done([{"label": "a", "done": False}], 5)


def test_default_items_takes_the_first_n_candidates_and_marks_them_not_done():
    candidates = [{"label": "a"}, {"label": "b"}, {"label": "c"}, {"label": "d"}]
    chosen = goals.default_items(candidates, target_count=3)
    assert [item["label"] for item in chosen] == ["a", "b", "c"]
    assert all(item["done"] is False for item in chosen)


def test_default_items_never_pads_a_short_list():
    chosen = goals.default_items([{"label": "a"}], target_count=3)
    assert len(chosen) == 1
