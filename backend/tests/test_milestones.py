from app.extensions import db
from app.models import Milestone

ASSIGNMENTS = "/api/v1/assignments"
MILESTONES = "/api/v1"
DEADLINE = "2026-11-20T23:59:00+00:00"


def make_assignment(client, headers, deadline=DEADLINE):
    response = client.post(
        ASSIGNMENTS,
        json={"course": "CS", "title": "Report", "deadline": deadline},
        headers=headers,
    )
    return response.get_json()["id"]


def add_milestone(client, headers, assignment_id, **overrides):
    payload = {"title": "Draft", "target_date": "2026-11-10T00:00:00+00:00"}
    payload.update(overrides)
    return client.post(f"{ASSIGNMENTS}/{assignment_id}/milestones", json=payload, headers=headers)


def test_create_milestone_returns_defaults(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)

    response = add_milestone(client, headers, assignment_id, description="  Outline  ")

    assert response.status_code == 201
    body = response.get_json()
    assert body["assignment_id"] == assignment_id
    assert body["description"] == "Outline"
    assert body["status"] == "not_started"
    assert body["target_date"] == "2026-11-10T00:00:00+00:00"


def test_create_milestone_rejects_invalid_input(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)

    assert add_milestone(client, headers, assignment_id, title="").status_code == 400
    assert add_milestone(client, headers, assignment_id, target_date=None).status_code == 400
    assert add_milestone(client, headers, assignment_id, target_date="2026-11-10").status_code == 400
    assert add_milestone(client, headers, assignment_id, description="x" * 2001).status_code == 400
    assert add_milestone(client, headers, assignment_id, status="finished").status_code == 400


def test_milestone_cannot_be_after_assignment_deadline(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)

    response = add_milestone(client, headers, assignment_id, target_date="2026-12-01T00:00:00+00:00")

    assert response.status_code == 400


def test_list_returns_milestones_ordered_by_target_date(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, title="Final", target_date="2026-11-18T00:00:00+00:00")
    add_milestone(client, headers, assignment_id, title="First", target_date="2026-11-05T00:00:00+00:00")

    titles = [m["title"] for m in client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()]

    assert titles == ["First", "Final"]


def test_get_update_and_delete_own_milestone(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    milestone_id = add_milestone(client, headers, assignment_id).get_json()["id"]

    assert client.get(f"{MILESTONES}/milestones/{milestone_id}", headers=headers).status_code == 200

    updated = client.patch(
        f"{MILESTONES}/milestones/{milestone_id}",
        json={"status": "done", "description": None, "target_date": "2026-11-12T00:00:00+00:00"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["status"] == "done"
    assert updated.get_json()["description"] is None

    assert client.delete(f"{MILESTONES}/milestones/{milestone_id}", headers=headers).status_code == 204
    assert client.get(f"{MILESTONES}/milestones/{milestone_id}", headers=headers).status_code == 404
    assert db.session.query(Milestone).count() == 0


def test_update_milestone_rejects_date_after_deadline(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    milestone_id = add_milestone(client, headers, assignment_id).get_json()["id"]

    response = client.patch(
        f"{MILESTONES}/milestones/{milestone_id}",
        json={"target_date": "2026-12-01T00:00:00+00:00"},
        headers=headers,
    )

    assert response.status_code == 400


def test_other_users_milestones_are_not_found(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner)
    milestone_id = add_milestone(client, owner, assignment_id).get_json()["id"]

    assert client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=intruder).status_code == 404
    assert add_milestone(client, intruder, assignment_id).status_code == 404
    assert client.get(f"{MILESTONES}/milestones/{milestone_id}", headers=intruder).status_code == 404
    assert client.patch(f"{MILESTONES}/milestones/{milestone_id}", json={"title": "x"}, headers=intruder).status_code == 404
    assert client.delete(f"{MILESTONES}/milestones/{milestone_id}", headers=intruder).status_code == 404
