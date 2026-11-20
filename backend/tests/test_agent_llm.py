"""These test app/services/agent/llm.py's configuration gate"""

import pytest

from app.services.agent import llm

RUBRIC = [{"title": "Research", "description": None, "weight": 40}]
MILESTONES = [{"id": 1, "title": "Draft", "description": None, "target_date": None, "status": "not_started", "weight": None, "position": 0}]


def test_not_configured_without_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.configured() is False


def test_configured_with_an_api_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert llm.configured() is True


def test_skips_the_call_entirely_when_not_configured(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(llm, "_call_once", lambda *a, **k: calls.append(1) or "should not run")

    findings, attempted, error = llm.qualitative_review("Report", RUBRIC, MILESTONES)
    assert findings == []
    assert attempted is False
    assert error is None
    assert calls == []


def test_a_successful_reply_becomes_one_info_finding(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_call_once", lambda *a, **k: "The rubric asks for interviews; no milestone covers that yet.")

    findings, attempted, error = llm.qualitative_review("Report", RUBRIC, MILESTONES)
    assert len(findings) == 1
    assert findings[0]["severity"] == "info"
    assert findings[0]["milestone_id"] is None
    assert "interviews" in findings[0]["message"]
    assert attempted is True
    assert error is None


def test_an_empty_reply_produces_no_finding_but_counts_as_attempted(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_call_once", lambda *a, **k: "")

    findings, attempted, error = llm.qualitative_review("Report", RUBRIC, MILESTONES)
    assert findings == []
    assert attempted is True
    assert error is None


def test_a_single_failure_is_retried_and_can_still_succeed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    attempts = {"count": 0}

    def flaky(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("timeout")
        return "Looks reasonably complete."

    monkeypatch.setattr(llm, "_call_once", flaky)
    findings, attempted, error = llm.qualitative_review("Report", RUBRIC, MILESTONES)
    assert attempts["count"] == 2
    assert error is None
    assert len(findings) == 1


def test_two_failures_give_up_cleanly_without_raising(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def always_fails(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(llm, "_call_once", always_fails)
    findings, attempted, error = llm.qualitative_review("Report", RUBRIC, MILESTONES)
    assert findings == []
    assert attempted is True
    assert error == "provider unavailable"


def test_a_reply_longer_than_the_cap_is_truncated():
    long_text = "word " * 200
    cleaned = llm._clean_reply(long_text)
    assert len(cleaned) <= llm.MAX_REPLY_CHARACTERS
    assert cleaned.endswith("…")


def test_whitespace_in_a_reply_is_collapsed():
    assert llm._clean_reply("  line one\n\n   line two  ") == "line one line two"


def test_build_model_requires_agent_model_to_be_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("AGENT_MODEL", raising=False)
    with pytest.raises(RuntimeError):
        llm._build_model()
