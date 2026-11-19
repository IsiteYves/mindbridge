import datetime as dt

from app.extensions import db
from app.models import FocusSession, User

FOCUS = "/api/v1/focus-sessions"
ASSIGNMENTS = "/api/v1/assignments"


def make_milestone(client, headers):
    assignment_id = client.post(
        ASSIGNMENTS,
        json={"course": "CS", "title": "Report", "deadline": "2026-11-20T23:59:00+00:00"},
        headers=headers,
    ).get_json()["id"]
    return client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": "2026-11-10T00:00:00+00:00"},
        headers=headers,
    ).get_json()["id"]


def test_starting_a_session_requires_a_token(client):
    assert client.post(FOCUS, json={}).status_code == 401


def test_starts_a_session_with_the_default_length(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.post(FOCUS, json={}, headers=headers)
    assert response.status_code == 201
    body = response.get_json()
    assert body["planned_minutes"] == 25
    assert body["milestone_id"] is None
    assert body["ended_at"] is None
    assert body["completed"] is False


def test_a_custom_planned_length_is_honoured(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.post(FOCUS, json={"planned_minutes": 50}, headers=headers)
    assert response.get_json()["planned_minutes"] == 50


def test_planned_minutes_is_range_checked(client, make_user_headers):
    headers = make_user_headers("student1")
    for bad in (0, 4, 121, "25", 25.5, True):
        assert client.post(FOCUS, json={"planned_minutes": bad}, headers=headers).status_code == 400, bad


def test_a_session_can_be_tied_to_the_students_own_milestone(client, make_user_headers):
    headers = make_user_headers("student1")
    milestone_id = make_milestone(client, headers)

    response = client.post(FOCUS, json={"milestone_id": milestone_id}, headers=headers)
    assert response.status_code == 201
    assert response.get_json()["milestone_id"] == milestone_id


def test_a_session_cannot_be_tied_to_someone_elses_milestone(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    milestone_id = make_milestone(client, owner)

    response = client.post(FOCUS, json={"milestone_id": milestone_id}, headers=intruder)
    assert response.status_code == 400


def test_a_session_cannot_be_tied_to_a_milestone_that_does_not_exist(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.post(FOCUS, json={"milestone_id": 999999}, headers=headers)
    assert response.status_code == 400


def test_ending_a_session_marks_it_completed_by_default(client, make_user_headers):
    headers = make_user_headers("student1")
    session_id = client.post(FOCUS, json={}, headers=headers).get_json()["id"]

    response = client.patch(f"{FOCUS}/{session_id}/end", json={}, headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["completed"] is True
    assert body["ended_at"] is not None


def test_ending_a_session_can_record_it_as_not_completed(client, make_user_headers):
    headers = make_user_headers("student1")
    session_id = client.post(FOCUS, json={}, headers=headers).get_json()["id"]

    response = client.patch(f"{FOCUS}/{session_id}/end", json={"completed": False}, headers=headers)
    assert response.get_json()["completed"] is False


def test_a_session_cannot_be_ended_twice(client, make_user_headers):
    headers = make_user_headers("student1")
    session_id = client.post(FOCUS, json={}, headers=headers).get_json()["id"]
    client.patch(f"{FOCUS}/{session_id}/end", json={}, headers=headers)

    response = client.patch(f"{FOCUS}/{session_id}/end", json={}, headers=headers)
    assert response.status_code == 409


def test_ending_a_session_is_private_to_its_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    session_id = client.post(FOCUS, json={}, headers=owner).get_json()["id"]

    assert client.patch(f"{FOCUS}/{session_id}/end", json={}, headers=intruder).status_code == 404


def test_today_lists_only_todays_sessions_for_the_current_user(client, make_user_headers):
    headers = make_user_headers("student1")
    other = make_user_headers("student2")
    client.post(FOCUS, json={}, headers=headers)
    client.post(FOCUS, json={}, headers=headers)
    client.post(FOCUS, json={}, headers=other)

    listed = client.get(f"{FOCUS}/today", headers=headers).get_json()
    assert len(listed) == 2


def test_today_excludes_a_session_started_on_a_different_day(app, client, make_user_headers):
    headers = make_user_headers("student1")
    user = db.session.query(User).filter_by(email="student1@example.com").one()
    yesterday = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
    db.session.add(FocusSession(user_id=user.id, started_at=yesterday, planned_minutes=25))
    db.session.commit()

    listed = client.get(f"{FOCUS}/today", headers=headers).get_json()
    assert listed == []
