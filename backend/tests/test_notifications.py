import datetime as dt

from app.extensions import db
from app.models import Assignment, Reminder, ReminderPreference, User

NOTIFICATIONS = "/api/v1/notifications"


# Preferences


def test_a_new_account_has_all_four_offsets_enabled_by_default(client, make_user_headers):
    headers = make_user_headers("student1")

    response = client.get(f"{NOTIFICATIONS}/preferences", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert {(p["offset_days"], p["enabled"]) for p in body} == {(5, True), (2, True), (1, True), (0, True)}


def test_preferences_require_a_token(client):
    assert client.get(f"{NOTIFICATIONS}/preferences").status_code == 401


def test_turning_an_offset_off_persists(client, make_user_headers):
    headers = make_user_headers("student1")

    patched = client.patch(f"{NOTIFICATIONS}/preferences", json={"offset_days": 2, "enabled": False}, headers=headers)
    assert patched.status_code == 200
    assert patched.get_json() == {"offset_days": 2, "enabled": False}

    listed = client.get(f"{NOTIFICATIONS}/preferences", headers=headers).get_json()
    assert {p["offset_days"]: p["enabled"] for p in listed}[2] is False
    # The other three are untouched.
    assert {p["offset_days"]: p["enabled"] for p in listed}[5] is True


def test_preferences_are_private_to_their_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")

    client.patch(f"{NOTIFICATIONS}/preferences", json={"offset_days": 1, "enabled": False}, headers=owner)

    listed = client.get(f"{NOTIFICATIONS}/preferences", headers=intruder).get_json()
    assert {p["offset_days"]: p["enabled"] for p in listed}[1] is True


def test_an_account_with_no_seeded_rows_still_gets_a_complete_default_list(client, make_user_headers):
    # Simulates an account that predates this feature: delete its seeded rows
    # and confirm the endpoint still returns all four, defaulting to enabled.
    headers = make_user_headers("student1")
    user = db.session.query(User).filter_by(email="student1@example.com").one()
    db.session.query(ReminderPreference).filter_by(user_id=user.id).delete()
    db.session.commit()

    listed = client.get(f"{NOTIFICATIONS}/preferences", headers=headers).get_json()
    assert len(listed) == 4
    assert all(p["enabled"] for p in listed)


def test_offset_days_is_restricted_to_the_allowed_set(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.patch(f"{NOTIFICATIONS}/preferences", json={"offset_days": 3, "enabled": True}, headers=headers)
    assert response.status_code == 400


def test_enabled_must_be_a_boolean(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.patch(f"{NOTIFICATIONS}/preferences", json={"offset_days": 1, "enabled": "yes"}, headers=headers)
    assert response.status_code == 400


# Inbox

def _make_assignment(user):
    assignment = Assignment(user=user, course="CS", title="Report", deadline=dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc))
    db.session.add(assignment)
    db.session.commit()
    return assignment


def test_inbox_is_empty_before_anything_has_been_sent(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.get(NOTIFICATIONS, headers=headers)
    assert response.status_code == 200
    assert response.get_json() == []


def test_inbox_lists_only_sent_and_undismissed_reminders(app, client, make_user_headers):
    headers = make_user_headers("student1")
    user = db.session.query(User).filter_by(email="student1@example.com").one()
    assignment = _make_assignment(user)

    sent = Reminder(
        user=user, assignment=assignment, kind="deadline", offset_days=1,
        fired_for_date=dt.date(2026, 11, 19), sent_at=dt.datetime.now(dt.timezone.utc),
    )
    unsent = Reminder(
        user=user, assignment=assignment, kind="deadline", offset_days=2,
        fired_for_date=dt.date(2026, 11, 18), sent_at=None,
    )
    dismissed = Reminder(
        user=user, assignment=assignment, kind="deadline", offset_days=5,
        fired_for_date=dt.date(2026, 11, 15), sent_at=dt.datetime.now(dt.timezone.utc),
        dismissed_at=dt.datetime.now(dt.timezone.utc),
    )
    db.session.add_all([sent, unsent, dismissed])
    db.session.commit()

    listed = client.get(NOTIFICATIONS, headers=headers).get_json()
    assert [item["id"] for item in listed] == [sent.id]


def test_dismiss_removes_a_reminder_from_the_inbox(client, make_user_headers):
    headers = make_user_headers("student1")
    user = db.session.query(User).filter_by(email="student1@example.com").one()
    assignment = _make_assignment(user)
    reminder = Reminder(
        user=user, assignment=assignment, kind="deadline", offset_days=1,
        fired_for_date=dt.date(2026, 11, 19), sent_at=dt.datetime.now(dt.timezone.utc),
    )
    db.session.add(reminder)
    db.session.commit()

    response = client.post(f"{NOTIFICATIONS}/{reminder.id}/dismiss", headers=headers)
    assert response.status_code == 200
    assert client.get(NOTIFICATIONS, headers=headers).get_json() == []


def test_dismiss_is_private_to_its_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    user = db.session.query(User).filter_by(email="student1@example.com").one()
    assignment = _make_assignment(user)
    reminder = Reminder(
        user=user, assignment=assignment, kind="deadline", offset_days=1,
        fired_for_date=dt.date(2026, 11, 19), sent_at=dt.datetime.now(dt.timezone.utc),
    )
    db.session.add(reminder)
    db.session.commit()

    assert client.post(f"{NOTIFICATIONS}/{reminder.id}/dismiss", headers=intruder).status_code == 404
    assert client.get(NOTIFICATIONS, headers=owner).get_json()[0]["id"] == reminder.id


def test_dismissing_an_unsent_reminder_is_refused(client, make_user_headers):
    headers = make_user_headers("student1")
    user = db.session.query(User).filter_by(email="student1@example.com").one()
    assignment = _make_assignment(user)
    reminder = Reminder(
        user=user, assignment=assignment, kind="deadline", offset_days=2,
        fired_for_date=dt.date(2026, 11, 18), sent_at=None,
    )
    db.session.add(reminder)
    db.session.commit()

    assert client.post(f"{NOTIFICATIONS}/{reminder.id}/dismiss", headers=headers).status_code == 409


def test_put_preferences_saves_every_offset_at_once(client, make_user_headers):
    headers = make_user_headers("student1")
    body = {"preferences": [{"offset_days": offset, "enabled": offset != 2} for offset in (5, 2, 1, 0)]}
    response = client.put("/api/v1/notifications/preferences", json=body, headers=headers)
    assert response.status_code == 200
    saved = {item["offset_days"]: item["enabled"] for item in response.get_json()}
    assert saved == {5: True, 2: False, 1: True, 0: True}


def test_put_preferences_rejects_an_unknown_offset(client, make_user_headers):
    headers = make_user_headers("student1")
    body = {"preferences": [{"offset_days": 9, "enabled": True}]}
    assert client.put("/api/v1/notifications/preferences", json=body, headers=headers).status_code == 400


def test_dismiss_all_clears_only_the_chosen_kinds(app, client, make_user_headers):
    from app.extensions import db
    from app.models import Reminder

    headers = make_user_headers("student1")
    now = dt.datetime.now(dt.timezone.utc)
    assignment_id = client.post(
        "/api/v1/assignments",
        json={"course": "CS", "title": "Report", "deadline": "2026-12-20T23:59:00+00:00"},
        headers=headers,
    ).get_json()["id"]
    with app.app_context():
        user_id = client.get("/api/v1/auth/me", headers=headers).get_json()["id"]
        for kind in ("deadline", "new_item", "new_item"):
            db.session.add(
                Reminder(
                    user_id=user_id,
                    assignment_id=assignment_id,
                    kind=kind,
                    offset_days=None,
                    fired_for_date=now.date(),
                    sent_at=now,
                )
            )
        db.session.commit()

    dismissed = client.post("/api/v1/notifications/dismiss-all", json={"kinds": ["new_item"]}, headers=headers)
    assert dismissed.get_json()["dismissed"] == 2
    remaining = client.get("/api/v1/notifications", headers=headers).get_json()
    assert [item["kind"] for item in remaining] == ["deadline"]
    assert remaining[0]["title"] == "Report"
    assert remaining[0]["course"] == "CS"


def test_dismiss_all_rejects_unknown_kinds(client, make_user_headers):
    headers = make_user_headers("student1")
    assert client.post("/api/v1/notifications/dismiss-all", json={"kinds": ["bogus"]}, headers=headers).status_code == 400
