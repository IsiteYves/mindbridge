import datetime as dt

ASSIGNMENTS = "/api/v1/assignments"


def future_deadline(days=10):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)).isoformat()


def make_assignment(client, headers, deadline=None):
    payload = {"course": "CS", "title": "Report"}
    if deadline is not None:
        payload["deadline"] = deadline
    return client.post(ASSIGNMENTS, json=payload, headers=headers).get_json()["id"]


def generate(client, headers, assignment_id, criteria=None, **extra):
    if criteria is None:
        criteria = [{"title": "Problem statement"}, {"title": "Method", "description": "Describe the design"}]
    payload = {"criteria": criteria, **extra}
    return client.post(f"{ASSIGNMENTS}/{assignment_id}/milestones/from-rubric", json=payload, headers=headers)


def test_generates_one_milestone_per_criterion_inside_the_window(client, make_user_headers):
    headers = make_user_headers("student1")
    deadline = future_deadline()
    assignment_id = make_assignment(client, headers, deadline)

    response = generate(client, headers, assignment_id)

    assert response.status_code == 201
    milestones = response.get_json()
    assert [m["title"] for m in milestones] == ["Problem statement", "Method"]
    assert milestones[1]["description"] == "Describe the design"
    assert all(m["status"] == "not_started" for m in milestones)
    now = dt.datetime.now(dt.timezone.utc)
    deadline_value = dt.datetime.fromisoformat(deadline)
    for milestone in milestones:
        target = dt.datetime.fromisoformat(milestone["target_date"])
        assert now < target < deadline_value


def test_second_generation_requires_replace(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, future_deadline())
    generate(client, headers, assignment_id)

    assert generate(client, headers, assignment_id).status_code == 409

    replaced = generate(client, headers, assignment_id, criteria=[{"title": "Only one"}], replace=True)
    assert replaced.status_code == 201
    listed = client.get(f"{ASSIGNMENTS}/{assignment_id}/milestones", headers=headers).get_json()
    assert [m["title"] for m in listed] == ["Only one"]


def test_generation_needs_a_future_deadline(client, make_user_headers):
    headers = make_user_headers("student1")
    no_deadline = make_assignment(client, headers)
    past = make_assignment(client, headers, (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat())

    assert generate(client, headers, no_deadline).status_code == 400
    assert generate(client, headers, past).status_code == 400


def test_generation_validates_criteria(client, make_user_headers):
    headers = make_user_headers("student1")
    assignment_id = make_assignment(client, headers, future_deadline())

    assert generate(client, headers, assignment_id, criteria=[]).status_code == 400
    assert generate(client, headers, assignment_id, criteria=[{"title": "  "}]).status_code == 400
    assert generate(client, headers, assignment_id, criteria=["Method"]).status_code == 400
    assert generate(client, headers, assignment_id, criteria=[{"title": "x"}] * 31).status_code == 400
    assert generate(client, headers, assignment_id, replace="yes").status_code == 400


def test_other_users_cannot_generate_milestones(client, make_user_headers):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    assignment_id = make_assignment(client, owner, future_deadline())

    assert generate(client, intruder, assignment_id).status_code == 404
