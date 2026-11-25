import datetime as dt

DASHBOARD = "/api/v1/dashboard/summary"
ASSIGNMENTS = "/api/v1/assignments"


def test_summary_requires_a_token(client):
    assert client.get(DASHBOARD).status_code == 401


def test_summary_counts_pending_in_progress_and_closed(client, make_user_headers):
    headers = make_user_headers("student1")
    future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=10)).isoformat()
    started = client.post(ASSIGNMENTS, json={"course": "CS", "title": "A", "deadline": future}, headers=headers).get_json()
    client.patch(f"{ASSIGNMENTS}/{started['id']}", json={"status": "in_progress"}, headers=headers)
    done = client.post(ASSIGNMENTS, json={"course": "CS", "title": "B", "deadline": future}, headers=headers).get_json()
    client.patch(f"{ASSIGNMENTS}/{done['id']}", json={"status": "done"}, headers=headers)

    body = client.get(DASHBOARD, headers=headers).get_json()
    assert body["counts"] == {"total": 2, "pending": 1, "in_progress": 1, "closed": 1}
    assert len(body["deadlines"]) == 4
    assert len(body["focus"]) == 7


def test_summary_is_private_to_the_student(client, make_user_headers):
    owner = make_user_headers("student1")
    other = make_user_headers("student2")
    future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=3)).isoformat()
    client.post(ASSIGNMENTS, json={"course": "CS", "title": "A", "deadline": future}, headers=owner)
    assert client.get(DASHBOARD, headers=other).get_json()["counts"]["total"] == 0
