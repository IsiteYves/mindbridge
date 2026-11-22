from app.extensions import db
from app.models import Milestone

ASSIGNMENTS = "/api/v1/assignments"
MILESTONES = "/api/v1"
DEADLINE = "2026-11-20T23:59:00+00:00"
# Three target dates before DEADLINE, for the ordering tests below.
TARGETS = (
    "2026-11-10T09:00:00+00:00",
    "2026-11-13T09:00:00+00:00",
    "2026-11-17T09:00:00+00:00",
)


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


def test_list_returns_milestones_in_position_order_not_date_order(client, make_user_headers):
    # The list is the student's own reading order (position). The timeline rail
    # sorts by date separately, so the two are allowed to disagree.
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    add_milestone(client, headers, assignment_id, title="Final", target_date="2026-11-18T00:00:00+00:00")
    add_milestone(client, headers, assignment_id, title="First", target_date="2026-11-05T00:00:00+00:00")

    titles = [m["title"] for m in client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()]

    assert titles == ["Final", "First"]


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


# ── Ordering, weight and the reorder endpoint

def _make_three(client, headers, assignment_id):
    """Create three milestones and return their ids in creation order."""
    ids = []
    for index, title in enumerate(("Problem", "Research", "Reflection")):
        response = client.post(
            f"{ASSIGNMENTS}/{assignment_id}/milestones",
            json={"title": title, "target_date": TARGETS[index]},
            headers=headers,
        )
        assert response.status_code == 201, response.get_json()
        ids.append(response.get_json()["id"])
    return ids


def test_new_milestones_are_numbered_in_creation_order(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    _make_three(client, headers, assignment_id)

    listed = client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()
    assert [m["position"] for m in listed] == [0, 1, 2]
    assert [m["title"] for m in listed] == ["Problem", "Research", "Reflection"]


def test_reorder_sets_the_reading_order_without_touching_target_dates(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    first, second, third = _make_three(client, headers, assignment_id)
    before = {m["id"]: m["target_date"] for m in
              client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()}

    response = client.put(
        f"{ASSIGNMENTS}/{assignment_id}/milestones/order",
        json={"milestone_ids": [third, first, second]},
        headers=headers,
    )
    assert response.status_code == 200
    assert [m["id"] for m in response.get_json()] == [third, first, second]
    assert [m["position"] for m in response.get_json()] == [0, 1, 2]
    # Deadlines are the student's commitment; reordering must never move them.
    assert {m["id"]: m["target_date"] for m in response.get_json()} == before


def test_reorder_is_idempotent(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    first, second, third = _make_three(client, headers, assignment_id)
    order = {"milestone_ids": [second, third, first]}

    once = client.put(f"{ASSIGNMENTS}/{assignment_id}/milestones/order", json=order, headers=headers).get_json()
    twice = client.put(f"{ASSIGNMENTS}/{assignment_id}/milestones/order", json=order, headers=headers).get_json()
    assert once == twice


def test_reorder_rejects_a_partial_or_repeated_list(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    first, second, third = _make_three(client, headers, assignment_id)

    for bad in ([first, second], [first, second, third, third], [first, first, second], [], "nope", [1.5]):
        response = client.put(
            f"{ASSIGNMENTS}/{assignment_id}/milestones/order", json={"milestone_ids": bad}, headers=headers
        )
        assert response.status_code == 400, bad


def test_reorder_refuses_a_milestone_from_another_assignment(client, make_user_headers):
    headers = make_user_headers("student1")
    mine = make_assignment(client, headers)
    other = make_assignment(client, headers)
    first, second, third = _make_three(client, headers, mine)
    stranger = client.post(
        f"{ASSIGNMENTS}/{other}/milestones",
        json={"title": "Elsewhere", "target_date": TARGETS[0]},
        headers=headers,
    ).get_json()["id"]

    response = client.put(
        f"{ASSIGNMENTS}/{mine}/milestones/order",
        json={"milestone_ids": [first, second, stranger]},
        headers=headers,
    )
    assert response.status_code == 400


def test_reorder_is_private_to_its_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner)
    ids = _make_three(client, owner, assignment_id)

    response = client.put(
        f"{ASSIGNMENTS}/{assignment_id}/milestones/order",
        json={"milestone_ids": list(reversed(ids))},
        headers=intruder,
    )
    assert response.status_code == 404


def test_deleting_a_milestone_closes_the_gap_in_positions(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    first, second, third = _make_three(client, headers, assignment_id)

    assert client.delete(f"{MILESTONES}/milestones/{second}", headers=headers).status_code == 204

    listed = client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()
    assert [m["position"] for m in listed] == [0, 1]
    assert [m["id"] for m in listed] == [first, third]


def test_weight_is_optional_and_range_checked(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)

    plain = client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Unweighted", "target_date": TARGETS[0]},
        headers=headers,
    )
    assert plain.status_code == 201
    assert plain.get_json()["weight"] is None

    weighted = client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Weighted", "target_date": TARGETS[1], "weight": 30},
        headers=headers,
    )
    assert weighted.status_code == 201
    assert weighted.get_json()["weight"] == 30

    for bad in (-1, 101, "30", 12.5, True):
        response = client.post(
            f"{ASSIGNMENTS}/{assignment_id}/milestones",
            json={"title": "Bad", "target_date": TARGETS[2], "weight": bad},
            headers=headers,
        )
        assert response.status_code == 400, bad


def test_weight_can_be_set_and_cleared_on_an_existing_milestone(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers)
    first = _make_three(client, headers, assignment_id)[0]

    assert client.patch(f"{MILESTONES}/milestones/{first}", json={"weight": 45}, headers=headers).get_json()["weight"] == 45
    assert client.patch(f"{MILESTONES}/milestones/{first}", json={"weight": None}, headers=headers).get_json()["weight"] is None
    assert client.patch(f"{MILESTONES}/milestones/{first}", json={"weight": 101}, headers=headers).status_code == 400
