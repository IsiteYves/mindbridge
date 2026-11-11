import pytest

from app.api import canvas as canvas_routes
from app.services.canvas import CanvasError

ASSIGNMENTS = "/api/v1/assignments"
CANVAS = "/api/v1/canvas"
TOKEN = "canvas-token-value-123"


class FakeCanvas:
    courses = [{"id": "101", "name": "Software Engineering"}]
    assignments = {
        "101": [
            {
                "canvas_id": "5001",
                "course_id": "101",
                "title": "Project report",
                "deadline": "2026-11-20T23:59:00Z",
                "rubric": [{"title": "Analysis", "points": 10}],
            },
            {"canvas_id": "5002", "course_id": "101", "title": "Reading log", "deadline": None, "rubric": []},
        ]
    }

    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    def list_courses(self):
        return list(FakeCanvas.courses)

    def list_assignments(self, course_id):
        return [dict(item) for item in FakeCanvas.assignments.get(course_id, [])]


@pytest.fixture
def canvas_app(app, monkeypatch):
    app.config["CANVAS_BASE_URL"] = "https://canvas.test"
    monkeypatch.setattr(canvas_routes, "CanvasClient", FakeCanvas)
    return app


def import_payload(**overrides):
    payload = {"token": TOKEN, "course_ids": ["101"]}
    payload.update(overrides)
    return payload


def test_courses_require_token(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/courses", json={}, headers=headers)

    assert response.status_code == 400


def test_courses_are_listed_for_a_valid_token(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/courses", json={"token": TOKEN}, headers=headers)

    assert response.status_code == 200
    assert response.get_json() == [{"id": "101", "name": "Software Engineering"}]


def test_import_creates_assignments_and_skips_items_without_due_date(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/import", json=import_payload(), headers=headers)

    body = response.get_json()
    assert response.status_code == 200
    assert body["created"] == 1
    assert body["updated"] == 0
    assert body["skipped"] == [{"canvas_id": "5002", "title": "Reading log", "reason": "No due date"}]
    assert body["assignments"][0]["course"] == "Software Engineering"
    assert body["assignments"][0]["deadline"] == "2026-11-20T23:59:00+00:00"
    assert body["assignments"][0]["rubric"] == [{"title": "Analysis", "points": 10}]


def test_reimport_updates_existing_rows_and_keeps_status(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/import", json=import_payload(), headers=headers)
    assignment_id = client.get(ASSIGNMENTS, headers=headers).get_json()[0]["id"]
    client.patch(f"{ASSIGNMENTS}/{assignment_id}", json={"status": "in_progress"}, headers=headers)
    FakeCanvas.assignments["101"][0]["title"] = "Final project report"

    response = client.post(f"{CANVAS}/import", json=import_payload(), headers=headers)

    assert response.get_json()["updated"] == 1
    assignment = client.get(f"{ASSIGNMENTS}/{assignment_id}", headers=headers).get_json()
    assert assignment["title"] == "Final project report"
    assert assignment["status"] == "in_progress"
    FakeCanvas.assignments["101"][0]["title"] = "Project report"


def test_import_rejects_course_the_account_is_not_enrolled_in(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/import", json=import_payload(course_ids=["999"]), headers=headers)

    assert response.status_code == 400
    assert "999" in response.get_json()["error"]


def test_import_rejects_invalid_course_ids(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")

    assert client.post(f"{CANVAS}/import", json=import_payload(course_ids=[]), headers=headers).status_code == 400
    assert client.post(f"{CANVAS}/import", json=import_payload(course_ids=[True]), headers=headers).status_code == 400
    assert client.post(f"{CANVAS}/import", json=import_payload(course_ids="101"), headers=headers).status_code == 400


def test_import_returns_503_when_canvas_is_not_configured(app, client, make_user_headers):
    app.config["CANVAS_BASE_URL"] = None
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/courses", json={"token": TOKEN}, headers=headers)

    assert response.status_code == 503
    assert response.get_json() == {"error": "Canvas integration is not configured"}


def test_canvas_errors_are_returned_as_json(canvas_app, client, make_user_headers, monkeypatch):
    def rejected(self):
        raise CanvasError("Canvas rejected the access token or its permissions", 401)

    monkeypatch.setattr(FakeCanvas, "list_courses", rejected)
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/courses", json={"token": TOKEN}, headers=headers)

    assert response.status_code == 401
    assert response.get_json()["error"].startswith("Canvas rejected")


def test_import_is_scoped_to_the_current_user(canvas_app, client, make_user_headers):
    client.post(f"{CANVAS}/import", json=import_payload(), headers=make_user_headers("student1"))

    response = client.post(f"{CANVAS}/import", json=import_payload(), headers=make_user_headers("student2"))

    assert response.get_json()["created"] == 1


def test_imported_rubric_is_saved_on_the_assignment(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/import", json=import_payload(), headers=headers)

    listed = client.get(ASSIGNMENTS, headers=headers).get_json()
    project = next(a for a in listed if a["canvas_id"] == "5001")
    assert project["rubric"] == [{"title": "Analysis", "points": 10}]
