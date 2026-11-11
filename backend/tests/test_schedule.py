import datetime as dt

import pytest

from app import scheduling
from app.extensions import db
from app.models import Reminder, StudySession, User, WellnessCheckin

NOW = dt.datetime(2026, 11, 10, 8, 0, tzinfo=dt.timezone.utc)
ASSIGNMENTS = "/api/v1/assignments"
SCHEDULE = "/api/v1/schedule"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(scheduling, "utc_now", lambda: NOW)


def iso(days=0, hours=0):
    return (NOW + dt.timedelta(days=days, hours=hours)).isoformat()


def parse(value):
    return dt.datetime.fromisoformat(value)


def make_assignment(client, headers, deadline_days=30):
    response = client.post(
        ASSIGNMENTS,
        json={"course": "HCI", "title": "Report", "deadline": iso(days=deadline_days)},
        headers=headers,
    )
    return response.get_json()["id"]


def add_milestone(client, headers, assignment_id, days=5, title="Draft", **extra):
    response = client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": title, "target_date": iso(days=days), **extra},
        headers=headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


def generate(client, headers, **body):
    return client.post(f"{SCHEDULE}/generate", json=body, headers=headers)


def per_day_counts(sessions):
    counts = {}
    for s in sessions:
        day = parse(s["start_time"]).date()
        counts[day] = counts.get(day, 0) + 1
    return counts


def test_requires_authentication(client):
    assert client.get(SCHEDULE).status_code == 401
    assert client.post(f"{SCHEDULE}/generate").status_code == 401
    assert client.patch(f"{SCHEDULE}/sessions/1", json={"status": "completed"}).status_code == 401


def test_get_schedule_is_empty_before_generating(client, make_user_headers):
    headers = make_user_headers("student1")

    response = client.get(SCHEDULE, headers=headers)

    assert response.status_code == 200
    assert response.get_json() == {"plan": None, "sessions": []}


def test_generate_places_sessions_before_each_target_date(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    early = add_milestone(client, headers, assignment_id, days=2, title="Outline")
    late = add_milestone(client, headers, assignment_id, days=6, title="Final")

    response = generate(client, headers)

    assert response.status_code == 201
    body = response.get_json()
    assert body["plan"]["status"] == "active"
    assert body["at_risk"] == []
    targets = {early: iso(days=2), late: iso(days=6)}
    by_milestone = {early: [], late: []}
    for s in body["sessions"]:
        by_milestone[s["milestone_id"]].append(s)
        assert parse(s["end_time"]) <= parse(targets[s["milestone_id"]])
        assert parse(s["start_time"]) >= NOW
        assert s["status"] == "planned"
    assert len(by_milestone[early]) == 2
    assert len(by_milestone[late]) == 2
    assert client.get(SCHEDULE, headers=headers).get_json()["sessions"] == body["sessions"]


def test_done_milestones_and_done_assignments_are_not_scheduled(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, status="done")
    finished_assignment = make_assignment(client, headers)
    add_milestone(client, headers, finished_assignment)
    client.patch(f"{ASSIGNMENTS}/{finished_assignment}", json={"status": "done"}, headers=headers)

    assert generate(client, headers).get_json()["sessions"] == []


def test_higher_stress_gives_shorter_and_lighter_days(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    for i in range(4):
        add_milestone(client, headers, assignment_id, days=3, title=f"M{i}")

    calm = generate(client, headers, stress_level=1).get_json()
    stressed = generate(client, headers, stress_level=5).get_json()

    assert calm["adaptation"]["block_minutes"] > stressed["adaptation"]["block_minutes"]
    assert calm["adaptation"]["max_daily_study_minutes"] > stressed["adaptation"]["max_daily_study_minutes"]
    assert max(per_day_counts(stressed["sessions"]).values()) <= stressed["adaptation"]["max_sessions_per_day"]
    for s in stressed["sessions"]:
        length = parse(s["end_time"]) - parse(s["start_time"])
        assert length == dt.timedelta(minutes=stressed["adaptation"]["block_minutes"])


def test_stress_comes_from_request_then_recent_checkin_then_default(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id)

    assert generate(client, headers).get_json()["adaptation"]["stress_source"] == "default"

    user = db.session.query(User).filter_by(username="student1").one()
    db.session.add(WellnessCheckin(user=user, checkin_date=NOW.date(), mood="low", stress_level=5))
    db.session.commit()

    from_checkin = generate(client, headers).get_json()["adaptation"]
    assert (from_checkin["stress_level"], from_checkin["stress_source"]) == (5, "checkin")

    explicit = generate(client, headers, stress_level=2).get_json()["adaptation"]
    assert (explicit["stress_level"], explicit["stress_source"]) == (2, "request")


def test_stale_checkin_is_ignored(client, make_user_headers):
    headers = make_user_headers("student1")
    user = db.session.query(User).filter_by(username="student1").one()
    db.session.add(WellnessCheckin(user=user, checkin_date=NOW.date() - dt.timedelta(days=5), mood="low", stress_level=5))
    db.session.commit()

    assert generate(client, headers).get_json()["adaptation"]["stress_source"] == "default"


def test_work_is_spread_across_days(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    for i in range(3):
        add_milestone(client, headers, assignment_id, days=6, title=f"M{i}")

    sessions = generate(client, headers, stress_level=1).get_json()["sessions"]

    assert len(per_day_counts(sessions)) >= 3


def test_milestone_that_cannot_fit_is_reported_at_risk(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    tight = add_milestone(client, headers, assignment_id, days=0, title="Today", **{})
    # Target a few hours from now: only a couple of blocks can possibly fit.
    client.patch(f"/api/v1/milestones/{tight}", json={"target_date": iso(hours=2)}, headers=headers)

    body = generate(client, headers, stress_level=1, blocks_per_milestone=8).get_json()

    assert len(body["sessions"]) < 8
    assert body["at_risk"][0]["milestone_id"] == tight
    assert body["at_risk"][0]["unscheduled_blocks"] == 8 - len(body["sessions"])
    assert body["at_risk"][0]["milestone_title"] == "Today"
    assert body["at_risk"][0]["milestone_target_date"] == iso(hours=2)


def test_overdue_milestone_is_scheduled_first(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    overdue = add_milestone(client, headers, assignment_id, days=-1, title="Late")
    add_milestone(client, headers, assignment_id, days=4, title="Later")

    sessions = generate(client, headers).get_json()["sessions"]

    assert sessions[0]["milestone_id"] == overdue
    assert parse(sessions[0]["start_time"]) >= NOW


def test_milestones_beyond_the_horizon_are_deferred(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, deadline_days=60)
    add_milestone(client, headers, assignment_id, days=40)

    body = generate(client, headers, horizon_days=7).get_json()

    assert body["sessions"] == []
    assert body["deferred_milestones"] == 1


def test_utc_offset_and_start_hour_shape_the_day(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, days=5)

    sessions = generate(client, headers, utc_offset_minutes=120, start_hour=10).get_json()["sessions"]

    local_starts = [parse(s["start_time"]) + dt.timedelta(hours=2) for s in sessions]
    assert all(start.hour >= 10 for start in local_starts)


def test_regenerating_replaces_future_sessions_and_marks_past_as_missed(client, make_user_headers, monkeypatch):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, days=5)
    first = generate(client, headers).get_json()
    first_ids = {s["id"] for s in first["sessions"]}

    later = NOW + dt.timedelta(days=1, hours=12)
    monkeypatch.setattr(scheduling, "utc_now", lambda: later)
    second = generate(client, headers).get_json()

    assert second["missed_sessions"] >= 1
    assert second["plan"]["id"] != first["plan"]["id"]
    assert all(parse(s["start_time"]) >= later for s in second["sessions"])
    assert not first_ids & {s["id"] for s in second["sessions"]}
    kept = db.session.query(StudySession).filter(StudySession.id.in_(first_ids)).all()
    assert kept and all(s.status == "missed" for s in kept)
    assert client.get(SCHEDULE, headers=headers).get_json()["plan"]["id"] == second["plan"]["id"]


def test_completed_sessions_count_toward_progress(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    milestone_id = add_milestone(client, headers, assignment_id, days=5)
    first = generate(client, headers, blocks_per_milestone=3).get_json()
    session_id = first["sessions"][0]["id"]
    client.patch(f"{SCHEDULE}/sessions/{session_id}", json={"status": "completed"}, headers=headers)

    second = generate(client, headers, blocks_per_milestone=3).get_json()

    assert len([s for s in second["sessions"] if s["milestone_id"] == milestone_id]) == 2
    assert db.session.get(StudySession, session_id).status == "completed"


def test_each_session_gets_a_reminder_before_it_starts(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, days=5)

    sessions = generate(client, headers, reminder_lead_minutes=30).get_json()["sessions"]

    assert sessions
    for s in sessions:
        reminder = s["reminder"]
        assert reminder["status"] == "pending"
        expected = max(parse(s["start_time"]) - dt.timedelta(minutes=30), NOW)
        assert parse(reminder["remind_at"]) == expected
    assert db.session.query(Reminder).count() == len(sessions)


@pytest.mark.parametrize(
    "body",
    [
        {"stress_level": 0},
        {"stress_level": 6},
        {"stress_level": "high"},
        {"stress_level": True},
        {"daily_minutes": 10},
        {"horizon_days": 0},
        {"horizon_days": 61},
        {"blocks_per_milestone": 9},
        {"start_hour": 19},
        {"utc_offset_minutes": 900},
        {"reminder_lead_minutes": -1},
        {"daily_minutes": "120"},
    ],
)
def test_generate_rejects_invalid_options(client, make_user_headers, body):
    headers = make_user_headers("student1")

    assert generate(client, headers, **body).status_code == 400


def test_update_session_status_and_dismisses_reminder(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id)
    session_id = generate(client, headers).get_json()["sessions"][0]["id"]

    response = client.patch(f"{SCHEDULE}/sessions/{session_id}", json={"status": "completed"}, headers=headers)

    assert response.status_code == 200
    assert response.get_json()["status"] == "completed"
    assert response.get_json()["reminder"]["status"] == "dismissed"
    assert client.patch(f"{SCHEDULE}/sessions/{session_id}", json={"status": "missed"}, headers=headers).status_code == 400


def test_other_users_cannot_see_or_change_sessions(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner)
    add_milestone(client, owner, assignment_id)
    session_id = generate(client, owner).get_json()["sessions"][0]["id"]

    assert client.patch(f"{SCHEDULE}/sessions/{session_id}", json={"status": "skipped"}, headers=intruder).status_code == 404
    assert generate(client, intruder).get_json()["sessions"] == []
    assert client.get(SCHEDULE, headers=owner).get_json()["sessions"]
    assert db.session.get(StudySession, session_id).status == "planned"


def test_plan_sessions_pure_function_is_deterministic():
    class M:
        def __init__(self, id, target):
            self.id, self.target_date = id, target

    milestones = [M(2, NOW + dt.timedelta(days=4)), M(1, NOW + dt.timedelta(days=2))]

    first = scheduling.plan_sessions(milestones, now=NOW)
    second = scheduling.plan_sessions(list(reversed(milestones)), now=NOW)

    assert first.placements == second.placements
    assert first.at_risk == []
