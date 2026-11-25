"""End-to-end tests for POST /assignments/:id/milestones/review."""

import datetime as dt

from app.services.agent import llm

ASSIGNMENTS = "/api/v1/assignments"

FUTURE_DEADLINE = "2026-12-20T23:59:00+00:00"


def make_assignment(client, headers, deadline=FUTURE_DEADLINE):
    response = client.post(ASSIGNMENTS, json={"course": "CS", "title": "Report", "deadline": deadline}, headers=headers)
    return response.get_json()["id"]


def add_milestone(client, headers, assignment_id, title="Draft", target_date="2026-12-10T00:00:00+00:00", weight=None):
    body = {"title": title, "target_date": target_date}
    if weight is not None:
        body["weight"] = weight
    return client.post(f"{ASSIGNMENTS}/{assignment_id}/milestones", json=body, headers=headers).get_json()["id"]


def review(client, headers, assignment_id):
    return client.post(f"{ASSIGNMENTS}/{assignment_id}/milestones/review", headers=headers)


# ── Access control


def test_review_requires_a_token(client):
    assert review(client, {}, 1).status_code == 401


def test_review_is_scoped_to_the_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner)

    assert review(client, intruder, assignment_id).status_code == 404


def test_review_404s_for_an_assignment_that_does_not_exist(client, make_user_headers):
    headers = make_user_headers("student1")
    assert review(client, headers, 999999).status_code == 404


# ── Always-available, rule-based behaviour (no AI provider needed) ──────────


def test_a_plan_with_no_findings_says_what_was_checked(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, title="Draft")

    response = review(client, headers, assignment_id)
    assert response.status_code == 200
    body = response.get_json()
    assert body["findings"] == []
    assert body["summary"] == "Milestones cover the rubric and finish before the deadline."
    assert body["replan_suggestion"] is None
    assert "generated_at" in body


def test_a_heavy_criterion_whose_milestone_has_a_different_weight_is_flagged(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    payload = {"criteria": [{"title": "Stakeholder research", "weight": 40}], "replace": False}
    client.post(f"{ASSIGNMENTS}/{assignment_id}/milestones/from-rubric", json=payload, headers=headers)
    # from-rubric names the milestone after its criterion; give it a clearly different weight.
    milestone_id = client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()[0]["id"]
    client.patch(f"/api/v1/milestones/{milestone_id}", json={"weight": 10}, headers=headers)

    body = review(client, headers, assignment_id).get_json()
    assert any("Stakeholder research" in f["message"] for f in body["findings"])


def test_an_overdue_milestone_produces_a_replan_suggestion(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    # A deadline comfortably in the future, with one milestone dated in the past.
    assignment_id = make_assignment(client, headers, deadline="2026-12-20T23:59:00+00:00")
    overdue_id = add_milestone(client, headers, assignment_id, title="Behind schedule", target_date="2020-01-01T00:00:00+00:00")

    body = review(client, headers, assignment_id).get_json()
    assert body["replan_suggestion"] is not None
    assert overdue_id in body["replan_suggestion"]["milestone_ids"]
    assert len(body["replan_suggestion"]["new_target_dates"]) == len(body["replan_suggestion"]["milestone_ids"])


def test_the_replan_suggestion_is_never_applied_to_the_real_milestone(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    overdue_id = add_milestone(client, headers, assignment_id, target_date="2020-01-01T00:00:00+00:00")

    review(client, headers, assignment_id)

    unchanged = client.get(f"/api/v1/milestones/{overdue_id}", headers=headers).get_json()
    assert unchanged["target_date"].startswith("2020-01-01")


def test_a_done_milestone_is_never_flagged_as_overdue(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    done_id = add_milestone(client, headers, assignment_id, target_date="2020-01-01T00:00:00+00:00")
    client.patch(f"/api/v1/milestones/{done_id}", json={"status": "done"}, headers=headers)

    body = review(client, headers, assignment_id).get_json()
    assert body["replan_suggestion"] is None


# ── AI-assisted pass: present, absent, and failing


def test_review_still_succeeds_with_no_api_key_configured(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id)

    assert review(client, headers, assignment_id).status_code == 200


def test_a_configured_provider_can_add_one_more_finding(app, client, make_user_headers, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_MODEL", "test-model")
    monkeypatch.setattr(llm, "_call_once", lambda *a, **k: "The rubric mentions sources; no milestone covers that.")

    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id)

    body = review(client, headers, assignment_id).get_json()
    assert any("sources" in f["message"] and f["severity"] == "info" for f in body["findings"])


def test_a_failing_provider_degrades_to_rule_based_findings_without_erroring(app, client, make_user_headers, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_MODEL", "test-model")

    def always_fails(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(llm, "_call_once", always_fails)

    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id)

    response = review(client, headers, assignment_id)
    assert response.status_code == 200
    assert "AI-assisted" in response.get_json()["summary"]


def test_the_ai_pass_never_sends_the_students_name_or_email(app, client, make_user_headers, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_MODEL", "test-model")
    sent_text = {}

    def capture(assignment_title, rubric, milestones):
        sent_text["payload"] = str(assignment_title) + str(rubric) + str(milestones)
        return ""

    monkeypatch.setattr(llm, "_call_once", capture)

    headers = make_user_headers("VeryDistinctiveName")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id)
    review(client, headers, assignment_id)

    assert "VeryDistinctiveName" not in sent_text["payload"]
    assert "@example.com" not in sent_text["payload"]


def test_a_plan_where_every_milestone_is_done_says_so_without_findings(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    milestone_id = add_milestone(client, headers, assignment_id, title="Draft")
    client.patch(f"/api/v1/milestones/{milestone_id}", json={"status": "done"}, headers=headers)

    body = review(client, headers, assignment_id).get_json()
    assert body["findings"] == []
    assert body["summary"] == "All milestones are done. Nothing left to balance."


def test_applying_the_suggestion_resolves_the_crowding_finding(app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    headers = make_user_headers("student1")
    now = dt.datetime.now(dt.timezone.utc)
    deadline_at = now + dt.timedelta(days=5)
    assignment_id = make_assignment(client, headers, deadline=deadline_at.isoformat())
    first = add_milestone(client, headers, assignment_id, title="Draft", target_date=(deadline_at - dt.timedelta(hours=20)).isoformat())
    second = add_milestone(client, headers, assignment_id, title="Final", target_date=(deadline_at - dt.timedelta(hours=30)).isoformat())

    before = review(client, headers, assignment_id).get_json()
    assert any("last two days" in f["message"] for f in before["findings"])
    suggestion = before["replan_suggestion"]
    assert suggestion is not None
    assert set(suggestion["milestone_ids"]) == {first, second}

    for milestone_id, target in zip(suggestion["milestone_ids"], suggestion["new_target_dates"]):
        response = client.patch(f"/api/v1/milestones/{milestone_id}", json={"target_date": target}, headers=headers)
        assert response.status_code == 200, response.get_json()

    after = review(client, headers, assignment_id).get_json()
    assert not any("last two days" in f["message"] for f in after["findings"])
