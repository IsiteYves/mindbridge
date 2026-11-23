import datetime as dt

from app.extensions import db
from app.models import Assignment, User
from app.services.reminders import send_due_reminders

ASSIGNMENTS = "/api/v1/assignments"


def make_assignment_due_in(client, headers, days, status=None):
    deadline = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)).isoformat()
    assignment_id = client.post(ASSIGNMENTS, json={"course": "CS", "title": "Report", "deadline": deadline}, headers=headers).get_json()["id"]
    if status:
        client.patch(f"{ASSIGNMENTS}/{assignment_id}", json={"status": status}, headers=headers)
    return assignment_id


def test_sends_reminders_for_each_tracked_offset(app, client, make_user_headers):
    headers = make_user_headers("student1")
    for days in (5, 2, 1, 0):
        make_assignment_due_in(client, headers, days)
    make_assignment_due_in(client, headers, 3)  

    result = send_due_reminders()
    assert result["sent"] == 4
    assert len(app.config["SENT_REMINDERS"]) == 4


def test_an_overdue_assignment_sends_once_per_day_not_once_ever(app, client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment_due_in(client, headers, -3)

    today = dt.datetime.now(dt.timezone.utc).date()
    first = send_due_reminders(today=today)
    second = send_due_reminders(today=today)
    assert first["sent"] == 1
    assert second["sent"] == 0  

    tomorrow = today + dt.timedelta(days=1)
    third = send_due_reminders(today=tomorrow)
    assert third["sent"] == 1  


def test_a_done_assignment_is_never_reminded(app, client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment_due_in(client, headers, -3, status="done")

    result = send_due_reminders()
    assert result["sent"] == 0


def test_an_offset_the_student_turned_off_is_not_sent(app, client, make_user_headers):
    headers = make_user_headers("student1")
    client.patch("/api/v1/notifications/preferences", json={"offset_days": 2, "enabled": False}, headers=headers)
    make_assignment_due_in(client, headers, 2)
    make_assignment_due_in(client, headers, 1)

    result = send_due_reminders()
    assert result["sent"] == 1  


def test_overdue_is_sent_even_if_every_offset_preference_is_disabled(app, client, make_user_headers):
    headers = make_user_headers("student1")
    for offset in (5, 2, 1, 0):
        client.patch("/api/v1/notifications/preferences", json={"offset_days": offset, "enabled": False}, headers=headers)
    make_assignment_due_in(client, headers, -1)

    result = send_due_reminders()
    assert result["sent"] == 1


def test_running_the_worker_twice_in_one_day_sends_each_item_only_once(app, client, make_user_headers):
    """The regression test for the NULL-milestone uniqueness gap. See this
    file's module docstring."""
    headers = make_user_headers("student1")
    make_assignment_due_in(client, headers, 5)
    make_assignment_due_in(client, headers, -2)

    first = send_due_reminders()
    second = send_due_reminders()

    assert first["sent"] == 2
    assert second["sent"] == 0
    assert len(app.config["SENT_REMINDERS"]) == 2


def test_a_milestone_level_reminder_is_independent_of_its_assignments_deadline(app, client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment_due_in(client, headers, 20)
    client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=5)).isoformat()},
        headers=headers,
    )

    result = send_due_reminders()
    assert result["sent"] == 1  


def test_a_done_milestone_is_never_reminded_even_if_its_assignment_is_open(app, client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment_due_in(client, headers, 20)
    milestone_id = client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()},
        headers=headers,
    ).get_json()["id"]
    client.patch(f"/api/v1/milestones/{milestone_id}", json={"status": "done"}, headers=headers)

    result = send_due_reminders()
    assert result["sent"] == 0


def test_reminders_are_private_each_users_worker_pass_only_reaches_their_own_email(app, client, make_user_headers):
    headers_a = make_user_headers("student1")
    make_user_headers("student2")
    make_assignment_due_in(client, headers_a, -1)

    send_due_reminders()
    recipients = {r["to"] for r in app.config["SENT_REMINDERS"]}
    assert recipients == {"student1@example.com"}




def test_importing_a_genuinely_new_assignment_sends_a_new_item_reminder(app, client, make_user_headers, monkeypatch):
    from app.services import canvas as canvas_service

    headers = make_user_headers("student1")
    monkeypatch.setattr(
        canvas_service.CanvasClient,
        "list_courses",
        lambda self: [{"id": "1", "name": "CS101"}],
    )
    monkeypatch.setattr(
        canvas_service.CanvasClient,
        "list_assignments",
        lambda self, course_id: [
            {"canvas_id": "a1", "title": "Essay", "deadline": "2026-12-01T00:00:00Z", "rubric": []}
        ],
    )

    client.post("/api/v1/canvas/import", json={"token": "fake-token", "course_ids": ["1"]}, headers=headers)
    assert any(r["subject"].startswith("New Item") for r in app.config["SENT_REMINDERS"])


def test_re_importing_an_existing_assignment_does_not_send_a_second_new_item_reminder(app, client, make_user_headers, monkeypatch):
    from app.services import canvas as canvas_service

    headers = make_user_headers("student1")
    monkeypatch.setattr(canvas_service.CanvasClient, "list_courses", lambda self: [{"id": "1", "name": "CS101"}])
    monkeypatch.setattr(
        canvas_service.CanvasClient,
        "list_assignments",
        lambda self, course_id: [
            {"canvas_id": "a1", "title": "Essay", "deadline": "2026-12-01T00:00:00Z", "rubric": []}
        ],
    )

    client.post("/api/v1/canvas/import", json={"token": "fake-token", "course_ids": ["1"]}, headers=headers)
    before = len(app.config["SENT_REMINDERS"])
    client.post("/api/v1/canvas/import", json={"token": "fake-token", "course_ids": ["1"]}, headers=headers)
    assert len(app.config["SENT_REMINDERS"]) == before


def test_manually_adding_a_milestone_does_not_send_a_new_item_reminder(app, client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment_due_in(client, headers, 20)
    client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat()},
        headers=headers,
    )
    assert app.config["SENT_REMINDERS"] == []