import datetime as dt

import pytest

from app.extensions import db
from app.models import User, WellnessCheckin
from app.services.adaptive import slack_fraction, stress_average, suggested_target

ASSIGNMENTS = "/api/v1/assignments"
SCHEDULE = "/api/v1/schedule"
REMINDERS = "/api/v1/reminders"


def now():
    return dt.datetime.now(dt.timezone.utc)


def iso(moment):
    return moment.isoformat()


def make_assignment(client, headers, deadline, status="not_started", title="Report"):
    response = client.post(
        ASSIGNMENTS,
        json={"course": "CS", "title": title, "deadline": iso(deadline), "status": status},
        headers=headers,
    )
    return response.get_json()["id"]


def add_milestone(client, headers, assignment_id, target, status="not_started", title="Draft"):
    return client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": title, "target_date": iso(target), "status": status},
        headers=headers,
    ).get_json()["id"]


def add_checkin(user_name, days_ago, stress_level):
    user = db.session.query(User).filter_by(email=f"{user_name}@example.com").one()
    checkin_date = now().date() - dt.timedelta(days=days_ago)
    db.session.add(WellnessCheckin(user_id=user.id, checkin_date=checkin_date, mood="okay", stress_level=stress_level))
    db.session.commit()


# Pure rules


def test_stress_average_is_none_without_checkins():
    assert stress_average([]) is None
    assert stress_average([2, 4]) == 3


@pytest.mark.parametrize(
    "average, expected",
    [(None, 0.0), (1, 0.0), (2.9, 0.0), (3, 0.15), (3.9, 0.15), (4, 0.3), (5, 0.3)],
)
def test_slack_grows_with_stress(average, expected):
    assert slack_fraction(average) == expected


def test_suggested_target_leaves_slack_before_a_future_target():
    start = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)
    target = start + dt.timedelta(days=10)

    assert suggested_target(target, start, 0) == target
    assert suggested_target(target, start, 0.3) == start + dt.timedelta(days=7)


def test_suggested_target_leaves_past_targets_unchanged():
    now_ = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)
    past = now_ - dt.timedelta(days=1)

    assert suggested_target(past, now_, 0.3) == past


# Schedule endpoint


def test_schedule_without_checkins_keeps_targets(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, now() + dt.timedelta(days=10))
    target = now() + dt.timedelta(days=3)
    add_milestone(client, headers, assignment_id, target)

    body = client.get(SCHEDULE, headers=headers).get_json()

    assert body["stress_average"] is None
    assert body["slack_fraction"] == 0
    (item,) = body["milestones"]
    assert item["suggested_date"] == item["target_date"]


def test_high_stress_moves_milestones_earlier(client, make_user_headers):
    headers = make_user_headers("student1")
    add_checkin("student1", 0, 5)
    add_checkin("student1", 1, 4)
    add_checkin("student1", 2, 4)
    assignment_id = make_assignment(client, headers, now() + dt.timedelta(days=10))
    add_milestone(client, headers, assignment_id, now() + dt.timedelta(days=5))

    body = client.get(SCHEDULE, headers=headers).get_json()

    assert body["stress_average"] == 4.33
    assert body["slack_fraction"] == 0.3
    (item,) = body["milestones"]
    assert dt.datetime.fromisoformat(item["suggested_date"]) < dt.datetime.fromisoformat(item["target_date"])


def test_only_the_three_most_recent_checkins_count(client, make_user_headers):
    headers = make_user_headers("student1")
    add_checkin("student1", 0, 1)
    add_checkin("student1", 1, 1)
    add_checkin("student1", 2, 1)
    add_checkin("student1", 3, 5)

    body = client.get(SCHEDULE, headers=headers).get_json()

    assert body["stress_average"] == 1
    assert body["slack_fraction"] == 0


def test_checkins_older_than_the_window_are_ignored(client, make_user_headers):
    headers = make_user_headers("student1")
    add_checkin("student1", 30, 5)

    body = client.get(SCHEDULE, headers=headers).get_json()

    assert body["stress_average"] is None


def test_schedule_skips_done_and_out_of_window_milestones(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, now() + dt.timedelta(days=60))
    add_milestone(client, headers, assignment_id, now() + dt.timedelta(days=2), status="done", title="Done")
    add_milestone(client, headers, assignment_id, now() + dt.timedelta(days=40), title="Far away")
    add_milestone(client, headers, assignment_id, now() + dt.timedelta(days=3), title="Open")

    body = client.get(SCHEDULE, query_string={"days": 14}, headers=headers).get_json()

    assert [item["title"] for item in body["milestones"]] == ["Open"]


def test_schedule_validates_days(client, make_user_headers):
    headers = make_user_headers("student1")

    for value in ("0", "61", "soon"):
        response = client.get(SCHEDULE, query_string={"days": value}, headers=headers)
        assert response.status_code == 400, value


def test_schedule_is_private_to_its_owner(client, make_user_headers):
    owner = make_user_headers("owner")
    other = make_user_headers("other")
    assignment_id = make_assignment(client, owner, now() + dt.timedelta(days=10))
    add_milestone(client, owner, assignment_id, now() + dt.timedelta(days=3))

    assert client.get(SCHEDULE, headers=other).get_json()["milestones"] == []


# Reminders endpoint


def test_reminders_list_deadlines_and_milestones_due_soon(client, make_user_headers):
    headers = make_user_headers("student1")
    soon_deadline = make_assignment(client, headers, now() + dt.timedelta(hours=20), title="Essay")
    far_deadline = make_assignment(client, headers, now() + dt.timedelta(days=20), title="Exam")
    add_milestone(client, headers, far_deadline, now() + dt.timedelta(hours=10), title="Outline")

    body = client.get(REMINDERS, headers=headers).get_json()

    assert [(r["kind"], r["title"]) for r in body] == [("milestone", "Outline"), ("deadline", "Essay")]
    assert body[1]["id"] == soon_deadline
    assert body[0]["hours_left"] < body[1]["hours_left"]


def test_reminders_skip_finished_assignments_and_overdue_deadlines(client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment(client, headers, now() + dt.timedelta(hours=5), status="done", title="Submitted")
    make_assignment(client, headers, now() - dt.timedelta(hours=5), title="Overdue")

    assert client.get(REMINDERS, headers=headers).get_json() == []


def test_reminders_use_adjusted_milestone_dates(client, make_user_headers):
    headers = make_user_headers("student1")
    add_checkin("student1", 0, 5)
    add_checkin("student1", 1, 5)
    assignment_id = make_assignment(client, headers, now() + dt.timedelta(days=10))
    # 4 days out is outside a 72-hour window but high stress pulls it earlier.
    add_milestone(client, headers, assignment_id, now() + dt.timedelta(days=4), title="Draft")

    body = client.get(REMINDERS, headers=headers).get_json()

    assert [r["title"] for r in body] == ["Draft"]


def test_reminders_validate_hours(client, make_user_headers):
    headers = make_user_headers("student1")

    for value in ("0", "337", "x"):
        response = client.get(REMINDERS, query_string={"hours": value}, headers=headers)
        assert response.status_code == 400, value


def test_reminders_require_a_token(client):
    assert client.get(REMINDERS).status_code == 401
    assert client.get(SCHEDULE).status_code == 401
