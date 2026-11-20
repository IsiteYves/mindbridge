import datetime as dt

ASSIGNMENTS = "/api/v1/assignments"
WORKLOAD = "/api/v1/schedule/workload"


def iso(days_from_now):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days_from_now)).isoformat()


def make_assignment(client, headers, deadline_days, status=None):
    assignment_id = client.post(
        ASSIGNMENTS, json={"course": "CS", "title": "Report", "deadline": iso(deadline_days)}, headers=headers
    ).get_json()["id"]
    if status:
        client.patch(f"{ASSIGNMENTS}/{assignment_id}", json={"status": status}, headers=headers)
    return assignment_id


def add_milestone(client, headers, assignment_id, target_days, status=None):
    milestone_id = client.post(
        f"{ASSIGNMENTS}/{assignment_id}/milestones",
        json={"title": "Draft", "target_date": iso(target_days)},
        headers=headers,
    ).get_json()["id"]
    if status:
        client.patch(f"/api/v1/milestones/{milestone_id}", json={"status": status}, headers=headers)
    return milestone_id


def test_requires_a_token(client):
    assert client.get(WORKLOAD).status_code == 401


def test_an_empty_plan_returns_an_empty_days_list(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.get(WORKLOAD, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["days"] == []


def test_a_milestone_and_a_deadline_on_different_days_each_appear(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, 20)
    add_milestone(client, headers, assignment_id, 5)

    days = client.get(WORKLOAD, headers=headers).get_json()["days"]
    assert len(days) == 2
    assert all(d["count"] == 1 for d in days)


def test_two_items_on_the_same_day_are_counted_together(client, make_user_headers):
    headers = make_user_headers("student1")
    a1 = make_assignment(client, headers, 10)
    a2 = make_assignment(client, headers, 20)
    # Put both assignments' only milestone on the same day.
    add_milestone(client, headers, a1, 7)
    add_milestone(client, headers, a2, 7)

    days = client.get(WORKLOAD, headers=headers).get_json()["days"]
    assert len(days) == 1
    assert days[0]["count"] == 2
    assert len(days[0]["items"]) == 2


def test_done_milestones_and_done_assignments_are_excluded(client, make_user_headers):
    headers = make_user_headers("student1")
    done_assignment = make_assignment(client, headers, 10, status="done")
    add_milestone(client, headers, done_assignment, 5, status="done")

    open_assignment = make_assignment(client, headers, 30)
    add_milestone(client, headers, open_assignment, 15)

    days = client.get(WORKLOAD, headers=headers).get_json()["days"]
    assert len(days) == 1  # only the open milestone's day


def test_items_outside_the_requested_range_are_excluded(client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment(client, headers, 200)  # far beyond the default 60-day window

    days = client.get(WORKLOAD, headers=headers).get_json()["days"]
    assert days == []


def test_a_custom_start_and_end_narrows_the_range(client, make_user_headers):
    headers = make_user_headers("student1")
    make_assignment(client, headers, 5)
    make_assignment(client, headers, 50)

    today = dt.datetime.now(dt.timezone.utc).date()
    response = client.get(
        WORKLOAD,
        query_string={"start": today.isoformat(), "end": (today + dt.timedelta(days=10)).isoformat()},
        headers=headers,
    )
    assert len(response.get_json()["days"]) == 1


def test_the_count_stays_true_even_once_the_items_list_is_capped(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, 30)
    for _ in range(13):
        add_milestone(client, headers, assignment_id, 10)

    days = client.get(WORKLOAD, headers=headers).get_json()["days"]
    assert len(days) == 1
    assert days[0]["count"] == 13
    assert len(days[0]["items"]) == 10  # capped, but the count above is not


def test_end_before_start_is_rejected(client, make_user_headers):
    headers = make_user_headers("student1")
    today = dt.datetime.now(dt.timezone.utc).date()
    response = client.get(
        WORKLOAD,
        query_string={"start": today.isoformat(), "end": (today - dt.timedelta(days=1)).isoformat()},
        headers=headers,
    )
    assert response.status_code == 400


def test_a_span_beyond_the_maximum_is_rejected(client, make_user_headers):
    headers = make_user_headers("student1")
    today = dt.datetime.now(dt.timezone.utc).date()
    response = client.get(
        WORKLOAD,
        query_string={"start": today.isoformat(), "end": (today + dt.timedelta(days=200)).isoformat()},
        headers=headers,
    )
    assert response.status_code == 400


def test_a_malformed_date_is_rejected(client, make_user_headers):
    headers = make_user_headers("student1")
    assert client.get(WORKLOAD, query_string={"start": "not-a-date"}, headers=headers).status_code == 400


def test_assignment_id_filters_to_just_that_assignments_items(client, make_user_headers):
    headers = make_user_headers("student1")
    a1 = make_assignment(client, headers, 10)
    a2 = make_assignment(client, headers, 10)
    add_milestone(client, headers, a1, 5)
    add_milestone(client, headers, a2, 5)

    response = client.get(WORKLOAD, query_string={"assignment_id": a1}, headers=headers)
    days = response.get_json()["days"]
    assert len(days) == 1
    assert days[0]["count"] == 1  # only a1's milestone, not a2's on the same day
    assert days[0]["items"][0]["assignment_id"] == a1


def test_assignment_id_for_someone_elses_assignment_returns_nothing_not_an_error(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner, 5)

    response = client.get(WORKLOAD, query_string={"assignment_id": assignment_id}, headers=intruder)
    assert response.status_code == 200
    assert response.get_json()["days"] == []


def test_a_non_integer_assignment_id_is_rejected(client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.get(WORKLOAD, query_string={"assignment_id": "not-a-number"}, headers=headers)
    assert response.status_code == 400


def test_workload_is_private_to_its_owner(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    make_assignment(client, owner, 5)

    assert client.get(WORKLOAD, headers=intruder).get_json()["days"] == []
