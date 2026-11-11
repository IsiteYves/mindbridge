import datetime as dt

import pytest

from app import scheduling
from app.extensions import db
from app.models import Reminder

NOW = dt.datetime(2026, 11, 10, 8, 0, tzinfo=dt.timezone.utc)
ASSIGNMENTS = "/api/v1/assignments"
SCHEDULE = "/api/v1/schedule"
REMINDERS = "/api/v1/reminders"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(scheduling, "utc_now", lambda: NOW)


def iso(days=0, hours=0):
    return (NOW + dt.timedelta(days=days, hours=hours)).isoformat()


def make_assignment(client, headers, deadline, title="Report", **extra):
    response = client.post(
        ASSIGNMENTS, json={"course": "HCI", "title": title, "deadline": deadline, **extra}, headers=headers
    )
    return response.get_json()["id"]


def add_milestone(client, headers, assignment_id, target, title="Draft", **extra):
    response = client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": title, "target_date": target, **extra},
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


def levels(body):
    return {(a["kind"], a["title"]): a["level"] for a in body["deadline_alerts"]}


def test_requires_authentication(client):
    assert client.get(REMINDERS).status_code == 401
    assert client.get(f"{REMINDERS}/upcoming").status_code == 401
    assert client.post(f"{REMINDERS}/1/dismiss").status_code == 401
    assert client.post(f"{REMINDERS}/1/snooze").status_code == 401


def test_deadline_alerts_are_classified_by_urgency(client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment(client, headers, iso(hours=-5), title="Overdue")
    make_assignment(client, headers, iso(hours=10), title="Urgent")
    make_assignment(client, headers, iso(hours=48), title="Soon")
    make_assignment(client, headers, iso(hours=90), title="Later")
    make_assignment(client, headers, iso(days=30), title="Far away")

    body = client.get(f"{REMINDERS}/upcoming?hours=120", headers=headers).get_json()

    assert levels(body) == {
        ("assignment", "Overdue"): "overdue",
        ("assignment", "Urgent"): "urgent",
        ("assignment", "Soon"): "soon",
        ("assignment", "Later"): "upcoming",
    }
    assert [a["title"] for a in body["deadline_alerts"]] == ["Overdue", "Urgent", "Soon", "Later"]
    urgent = next(a for a in body["deadline_alerts"] if a["title"] == "Urgent")
    assert urgent["hours_remaining"] == 10.0


def test_default_window_is_72_hours(client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment(client, headers, iso(hours=70), title="Inside")
    make_assignment(client, headers, iso(hours=80), title="Outside")

    body = client.get(f"{REMINDERS}/upcoming", headers=headers).get_json()

    assert body["window_hours"] == 72
    assert [a["title"] for a in body["deadline_alerts"]] == ["Inside"]


def test_done_work_and_long_overdue_work_produce_no_alerts(client, make_user_headers):
    headers = make_user_headers("student1")
    finished = make_assignment(client, headers, iso(hours=5), title="Finished")
    client.patch(f"{ASSIGNMENTS}/{finished}", json={"status": "done"}, headers=headers)
    make_assignment(client, headers, iso(days=-30), title="Ancient")
    open_assignment = make_assignment(client, headers, iso(days=20), title="Open")
    add_milestone(client, headers, open_assignment, iso(hours=6), title="Done step", status="done")

    assert client.get(f"{REMINDERS}/upcoming", headers=headers).get_json()["deadline_alerts"] == []


def test_milestone_alerts_are_included(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20), title="Report")
    add_milestone(client, headers, assignment_id, iso(hours=20), title="Outline")

    body = client.get(f"{REMINDERS}/upcoming", headers=headers).get_json()

    alert = body["deadline_alerts"][0]
    assert (alert["kind"], alert["title"], alert["level"]) == ("milestone", "Outline", "urgent")
    assert alert["assignment_id"] == assignment_id


def test_upcoming_rejects_invalid_window(client, make_user_headers):
    headers = make_user_headers("student1")

    for hours in ("0", "abc", "-4", "721"):
        assert client.get(f"{REMINDERS}/upcoming?hours={hours}", headers=headers).status_code == 400


def test_session_reminders_flag_what_is_due(client, make_user_headers, monkeypatch):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    sessions = client.post(f"{SCHEDULE}/generate", json={}, headers=headers).get_json()["sessions"]
    first_start = dt.datetime.fromisoformat(sessions[0]["start_time"])

    monkeypatch.setattr(scheduling, "utc_now", lambda: first_start - dt.timedelta(minutes=5))
    body = client.get(f"{REMINDERS}/upcoming?hours=1", headers=headers).get_json()

    assert body["session_reminders"][0]["due"] is True
    assert body["session_reminders"][0]["session"]["milestone_title"] == "Draft"


def test_finished_sessions_do_not_produce_reminders(client, make_user_headers, monkeypatch):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    sessions = client.post(f"{SCHEDULE}/generate", json={}, headers=headers).get_json()["sessions"]
    client.patch(f"{SCHEDULE}/sessions/{sessions[0]['id']}", json={"status": "completed"}, headers=headers)
    last_end = dt.datetime.fromisoformat(sessions[-1]["end_time"])

    body = client.get(f"{REMINDERS}/upcoming?hours=720", headers=headers).get_json()
    assert sessions[0]["id"] not in [r["study_session_id"] for r in body["session_reminders"]]

    monkeypatch.setattr(scheduling, "utc_now", lambda: last_end + dt.timedelta(minutes=1))
    assert client.get(f"{REMINDERS}/upcoming?hours=720", headers=headers).get_json()["session_reminders"] == []


def test_list_reminders_can_filter_by_status(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    client.post(f"{SCHEDULE}/generate", json={}, headers=headers)
    reminder_id = client.get(REMINDERS, headers=headers).get_json()[0]["id"]
    client.post(f"{REMINDERS}/{reminder_id}/dismiss", headers=headers)

    dismissed = client.get(f"{REMINDERS}?status=dismissed", headers=headers).get_json()
    pending = client.get(f"{REMINDERS}?status=pending", headers=headers).get_json()

    assert [r["id"] for r in dismissed] == [reminder_id]
    assert reminder_id not in [r["id"] for r in pending]
    assert client.get(f"{REMINDERS}?status=sent", headers=headers).status_code == 400


def test_dismiss_reminder(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    client.post(f"{SCHEDULE}/generate", json={}, headers=headers)
    reminder_id = client.get(REMINDERS, headers=headers).get_json()[0]["id"]

    response = client.post(f"{REMINDERS}/{reminder_id}/dismiss", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["status"] == "dismissed"
    assert db.session.get(Reminder, reminder_id).status == "dismissed"


def test_snooze_moves_reminder_and_reopens_it(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    client.post(f"{SCHEDULE}/generate", json={}, headers=headers)
    reminder_id = client.get(REMINDERS, headers=headers).get_json()[0]["id"]
    client.post(f"{REMINDERS}/{reminder_id}/dismiss", headers=headers)

    response = client.post(f"{REMINDERS}/{reminder_id}/snooze", json={"minutes": 45}, headers=headers)

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "pending"
    assert dt.datetime.fromisoformat(body["remind_at"]) == NOW + dt.timedelta(minutes=45)


def test_snooze_validation(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    client.post(f"{SCHEDULE}/generate", json={}, headers=headers)
    reminder_id = client.get(REMINDERS, headers=headers).get_json()[0]["id"]

    for minutes in (1, 5000, "30", True):
        response = client.post(f"{REMINDERS}/{reminder_id}/snooze", json={"minutes": minutes}, headers=headers)
        assert response.status_code == 400
    # Default snooze works with an empty body.
    assert client.post(f"{REMINDERS}/{reminder_id}/snooze", headers=headers).status_code == 200


def test_snooze_cannot_pass_the_end_of_the_session(client, make_user_headers, monkeypatch):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, iso(days=20))
    add_milestone(client, headers, assignment_id, iso(days=3))
    session = client.post(f"{SCHEDULE}/generate", json={}, headers=headers).get_json()["sessions"][0]
    end = dt.datetime.fromisoformat(session["end_time"])
    monkeypatch.setattr(scheduling, "utc_now", lambda: end - dt.timedelta(minutes=10))

    response = client.post(f"{REMINDERS}/{session['reminder']['id']}/snooze", json={"minutes": 30}, headers=headers)

    assert response.status_code == 400


def test_other_users_reminders_are_not_found(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner, iso(days=20), title="Private")
    add_milestone(client, owner, assignment_id, iso(days=3))
    client.post(f"{SCHEDULE}/generate", json={}, headers=owner)
    reminder_id = client.get(REMINDERS, headers=owner).get_json()[0]["id"]

    assert client.post(f"{REMINDERS}/{reminder_id}/dismiss", headers=intruder).status_code == 404
    assert client.post(f"{REMINDERS}/{reminder_id}/snooze", headers=intruder).status_code == 404
    assert client.get(REMINDERS, headers=intruder).get_json() == []
    assert client.get(f"{REMINDERS}/upcoming", headers=intruder).get_json()["deadline_alerts"] == []
    assert db.session.get(Reminder, reminder_id).status == "pending"
