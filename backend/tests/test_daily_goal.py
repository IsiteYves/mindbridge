from app.extensions import db
from app.models import DailyGoal, User

DAILY_GOAL = "/api/v1/daily-goal"
ASSIGNMENTS = "/api/v1/assignments"


def make_milestones(client, headers, titles_and_dates):
    assignment_id = client.post(
        ASSIGNMENTS,
        json={"course": "CS", "title": "Report", "deadline": "2026-11-20T23:59:00+00:00"},
        headers=headers,
    ).get_json()["id"]
    for title, target_date in titles_and_dates:
        client.post(
            f"{ASSIGNMENTS}/{assignment_id}/milestones",
            json={"title": title, "target_date": target_date},
            headers=headers,
        )


def test_today_requires_a_token(client):
    assert client.get(f"{DAILY_GOAL}/today").status_code == 401


def test_a_fresh_goal_is_picked_from_the_nearest_due_milestones(client, make_user_headers):
    headers = make_user_headers("student1")
    make_milestones(
        client, headers,
        [
            ("Latest", "2026-11-18T00:00:00+00:00"),
            ("Soonest", "2026-11-05T00:00:00+00:00"),
            ("Middle", "2026-11-10T00:00:00+00:00"),
            ("Also late", "2026-11-19T00:00:00+00:00"),
        ],
    )

    response = client.get(f"{DAILY_GOAL}/today", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["target_count"] == 3
    assert [item["label"] for item in body["items"]] == ["Soonest", "Middle", "Latest"]
    assert all(item["done"] is False for item in body["items"])
    assert body["done_count"] == 0
    assert body["total_count"] == 3


def test_a_goal_with_fewer_than_three_open_milestones_is_not_padded(client, make_user_headers):
    headers = make_user_headers("student1")
    make_milestones(client, headers, [("Only one", "2026-11-05T00:00:00+00:00")])

    body = client.get(f"{DAILY_GOAL}/today", headers=headers).get_json()
    assert len(body["items"]) == 1


def test_the_goal_is_stable_across_the_same_day(client, make_user_headers):
    headers = make_user_headers("student1")
    make_milestones(client, headers, [("First", "2026-11-05T00:00:00+00:00")])

    first = client.get(f"{DAILY_GOAL}/today", headers=headers).get_json()
    make_milestones(client, headers, [("Added later", "2026-11-04T00:00:00+00:00")])
    second = client.get(f"{DAILY_GOAL}/today", headers=headers).get_json()

    assert first["id"] == second["id"]
    assert second["items"] == first["items"]


def test_marking_an_item_done(client, make_user_headers):
    headers = make_user_headers("student1")
    make_milestones(client, headers, [("First", "2026-11-05T00:00:00+00:00")])
    client.get(f"{DAILY_GOAL}/today", headers=headers)

    response = client.patch(f"{DAILY_GOAL}/today/items/0", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["items"][0]["done"] is True
    assert body["done_count"] == 1


def test_marking_an_out_of_range_item_is_rejected(client, make_user_headers):
    headers = make_user_headers("student1")
    make_milestones(client, headers, [("First", "2026-11-05T00:00:00+00:00")])
    client.get(f"{DAILY_GOAL}/today", headers=headers)

    response = client.patch(f"{DAILY_GOAL}/today/items/5", headers=headers)
    assert response.status_code == 400


def test_marking_an_item_before_a_goal_exists_is_rejected(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.patch(f"{DAILY_GOAL}/today/items/0", headers=headers)
    assert response.status_code == 404


def test_the_goal_is_private_to_its_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    make_milestones(client, owner, [("Private", "2026-11-05T00:00:00+00:00")])
    client.get(f"{DAILY_GOAL}/today", headers=owner)

    intruder_goal = client.get(f"{DAILY_GOAL}/today", headers=intruder).get_json()
    assert intruder_goal["items"] == []


def test_done_milestones_are_never_picked_for_a_fresh_goal(client, make_user_headers):
    headers = make_user_headers("student1")
    make_milestones(client, headers, [("Finished", "2026-11-05T00:00:00+00:00")])
    milestone_id = (
        db.session.query(User).filter_by(email="student1@example.com").one().assignments[0].milestones[0].id
    )
    client.patch(f"/api/v1/milestones/{milestone_id}", json={"status": "done"}, headers=headers)

    body = client.get(f"{DAILY_GOAL}/today", headers=headers).get_json()
    assert body["items"] == []


def test_the_underlying_row_is_one_per_user_per_day(client, make_user_headers):
    headers = make_user_headers("student1")
    client.get(f"{DAILY_GOAL}/today", headers=headers)
    client.get(f"{DAILY_GOAL}/today", headers=headers)

    user = db.session.query(User).filter_by(email="student1@example.com").one()
    assert db.session.query(DailyGoal).filter_by(user_id=user.id).count() == 1
