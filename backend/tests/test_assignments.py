from app.extensions import db
from app.models import Assignment, Milestone

BASE = "/api/v1/assignments"
DEADLINE = "2026-11-20T23:59:00+02:00"


def create(client, headers, **overrides):
    payload = {"course": "Software Engineering", "title": "Project report", "deadline": DEADLINE}
    payload.update(overrides)
    return client.post(BASE, json=payload, headers=headers)


def test_create_requires_authentication(client):
    response = client.post(BASE, json={"course": "CS", "title": "Lab"})

    assert response.status_code == 401


def test_create_returns_assignment_with_default_status(client, make_user_headers):
    response = create(client, make_user_headers("student1"))

    assert response.status_code == 201
    body = response.get_json()
    assert body["course"] == "Software Engineering"
    assert body["title"] == "Project report"
    assert body["status"] == "not_started"
    assert body["deadline"] == "2026-11-20T21:59:00+00:00"
    assert body["canvas_id"] is None


def test_create_requires_a_deadline(client, make_user_headers):
    response = create(client, make_user_headers("student1"), deadline=None)

    assert response.status_code == 400


def test_create_rejects_invalid_input(client, make_user_headers):
    headers = make_user_headers("student1")

    assert create(client, headers, title="   ").status_code == 400
    assert create(client, headers, course=None).status_code == 400
    assert create(client, headers, status="finished").status_code == 400
    assert create(client, headers, deadline="2026-11-20T23:59:00").status_code == 400
    assert create(client, headers, deadline="next friday").status_code == 400
    assert create(client, headers, canvas_id="").status_code == 400


def test_create_rejects_duplicate_canvas_id_for_same_user(client, make_user_headers):
    headers = make_user_headers("student1")
    assert create(client, headers, canvas_id=" 4411").status_code == 201

    response = create(client, headers, canvas_id="4411")

    assert response.status_code == 409


def test_same_canvas_id_is_allowed_for_different_users(client, make_user_headers):
    assert create(client, make_user_headers("student1"), canvas_id="4411").status_code == 201

    response = create(client, make_user_headers("student2"), canvas_id="4411")

    assert response.status_code == 201


def test_list_returns_only_own_assignments_ordered_by_deadline(client, make_user_headers):
    mine = make_user_headers("student1")
    create(client, mine, title="Later", deadline="2026-12-01T00:00:00+00:00")
    create(client, mine, title="Sooner", deadline="2026-11-10T00:00:00+00:00")
    create(client, make_user_headers("student2"), title="Not mine")

    titles = [a["title"] for a in client.get(BASE, headers=mine).get_json()["items"]]

    assert titles == ["Sooner", "Later"]


def test_get_update_and_delete_own_assignment(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = create(client, headers).get_json()["id"]

    assert client.get(f"{BASE}/{assignment_id}", headers=headers).status_code == 200

    updated = client.patch(f"{BASE}/{assignment_id}", json={"status": "in_progress", "deadline": None}, headers=headers)
    assert updated.status_code == 400

    updated = client.patch(f"{BASE}/{assignment_id}", json={"status": "in_progress"}, headers=headers)
    assert updated.status_code == 200
    assert updated.get_json()["status"] == "in_progress"

    assert client.delete(f"{BASE}/{assignment_id}", headers=headers).status_code == 204
    assert client.get(f"{BASE}/{assignment_id}", headers=headers).status_code == 404


def test_other_users_assignment_is_not_found(client, make_user_headers):
    assignment_id = create(client, make_user_headers("student1")).get_json()["id"]
    intruder = make_user_headers("student2")

    assert client.get(f"{BASE}/{assignment_id}", headers=intruder).status_code == 404
    assert client.patch(f"{BASE}/{assignment_id}", json={"title": "x"}, headers=intruder).status_code == 404
    assert client.delete(f"{BASE}/{assignment_id}", headers=intruder).status_code == 404


def test_update_rejects_invalid_values(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = create(client, headers).get_json()["id"]

    assert client.patch(f"{BASE}/{assignment_id}", json={"status": "bogus"}, headers=headers).status_code == 400
    assert client.patch(f"{BASE}/{assignment_id}", json={"title": ""}, headers=headers).status_code == 400
    assert client.patch(f"{BASE}/{assignment_id}", json={"deadline": "tomorrow"}, headers=headers).status_code == 400


def test_deadline_cannot_move_before_an_existing_milestone(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = create(client, headers).get_json()["id"]
    client.post(
        f"{BASE}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": "2026-11-15T00:00:00+00:00"},
        headers=headers,
    )

    response = client.patch(
        f"{BASE}/{assignment_id}", json={"deadline": "2026-11-10T00:00:00+00:00"}, headers=headers
    )

    assert response.status_code == 400


def test_delete_removes_milestones(app, client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = create(client, headers).get_json()["id"]
    client.post(
        f"{BASE}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": "2026-11-15T00:00:00+00:00"},
        headers=headers,
    )

    client.delete(f"{BASE}/{assignment_id}", headers=headers)

    assert db.session.query(Assignment).count() == 0
    assert db.session.query(Milestone).count() == 0


def test_the_list_is_paginated_with_a_default_of_fifteen(client, make_user_headers):
    headers = make_user_headers("student1")
    for index in range(17):
        create(client, headers, title=f"Task {index:02d}", deadline=f"2026-12-{index + 1:02d}T00:00:00+00:00")

    first = client.get(BASE, headers=headers).get_json()
    assert first["total"] == 17
    assert first["limit"] == 15
    assert len(first["items"]) == 15

    second = client.get(f"{BASE}?offset=15", headers=headers).get_json()
    assert [a["title"] for a in second["items"]] == ["Task 15", "Task 16"]


def test_the_list_refuses_an_unbounded_page(client, make_user_headers):
    headers = make_user_headers("student1")
    assert client.get(f"{BASE}?limit=500", headers=headers).status_code == 400


def test_the_list_filters_by_name_and_state_on_the_server(client, make_user_headers):
    headers = make_user_headers("student1")
    create(client, headers, title="Poster design", deadline="2026-12-01T00:00:00+00:00")
    done = create(client, headers, title="Poster review", deadline="2026-12-02T00:00:00+00:00").get_json()
    client.patch(f"{BASE}/{done['id']}", json={"status": "done"}, headers=headers)
    create(client, headers, title="Essay", deadline="2026-12-03T00:00:00+00:00")

    by_name = client.get(f"{BASE}?q=poster", headers=headers).get_json()
    assert by_name["total"] == 2

    pending = client.get(f"{BASE}?state=pending&q=poster", headers=headers).get_json()
    assert [a["title"] for a in pending["items"]] == ["Poster design"]

    closed = client.get(f"{BASE}?state=closed", headers=headers).get_json()
    assert [a["title"] for a in closed["items"]] == ["Poster review"]


def test_the_list_rejects_an_unknown_state(client, make_user_headers):
    headers = make_user_headers("student1")
    assert client.get(f"{BASE}?state=whatever", headers=headers).status_code == 400
