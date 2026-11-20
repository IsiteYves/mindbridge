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


# ── Persistent connection: /canvas/status, /connect, /sync, /connection ────


@pytest.fixture
def encryption_key(monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())


def test_status_before_ever_connecting(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.get(f"{CANVAS}/status", headers=headers)
    assert response.status_code == 200
    assert response.get_json() == {"provider": "canvas", "status": "not_connected", "last_synced_at": None}


def test_connect_requires_the_encryption_key_to_be_configured(canvas_app, client, make_user_headers, monkeypatch):
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)
    assert response.status_code == 503


def test_connect_imports_and_marks_the_connection_active(canvas_app, client, make_user_headers, encryption_key):
    headers = make_user_headers("student1")

    response = client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["created"] == 1
    assert body["connection"]["status"] == "connected"
    assert body["connection"]["last_synced_at"] is not None

    status = client.get(f"{CANVAS}/status", headers=headers).get_json()
    assert status["status"] == "connected"


def test_connect_never_exposes_the_raw_token_anywhere_in_the_response(canvas_app, client, make_user_headers, encryption_key):
    headers = make_user_headers("student1")
    response = client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)
    assert TOKEN not in response.get_data(as_text=True)


def test_sync_reimports_using_the_stored_token_with_no_token_in_the_request(canvas_app, client, make_user_headers, encryption_key):
    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)
    FakeCanvas.assignments["101"][0]["title"] = "Final project report"

    response = client.post(f"{CANVAS}/sync", json={}, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["updated"] == 1
    assert response.get_json()["assignments"][0]["title"] == "Final project report"
    FakeCanvas.assignments["101"][0]["title"] = "Project report"


def test_sync_before_connecting_is_refused(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.post(f"{CANVAS}/sync", json={}, headers=headers)
    assert response.status_code == 409


def test_sync_after_disconnecting_is_refused(canvas_app, client, make_user_headers, encryption_key):
    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)
    client.delete(f"{CANVAS}/connection", headers=headers)

    response = client.post(f"{CANVAS}/sync", json={}, headers=headers)
    assert response.status_code == 409


def test_disconnect_clears_the_token_but_keeps_imported_assignments(canvas_app, client, make_user_headers, encryption_key):
    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)

    response = client.delete(f"{CANVAS}/connection", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["status"] == "disconnected"

    assignments = client.get(ASSIGNMENTS, headers=headers).get_json()
    assert len(assignments) == 1  # untouched by disconnecting


def test_disconnecting_with_no_connection_yet_is_a_harmless_no_op(canvas_app, client, make_user_headers):
    headers = make_user_headers("student1")
    response = client.delete(f"{CANVAS}/connection", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["status"] == "not_connected"


def test_a_token_that_cannot_be_decrypted_forces_a_reconnect(canvas_app, client, make_user_headers, encryption_key, monkeypatch):
    from cryptography.fernet import Fernet

    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)

    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    response = client.post(f"{CANVAS}/sync", json={}, headers=headers)
    assert response.status_code == 409
    assert "reconnect" in response.get_json()["error"].lower()

    status = client.get(f"{CANVAS}/status", headers=headers).get_json()
    assert status["status"] == "disconnected"


def test_the_connection_is_private_to_its_owner(canvas_app, client, make_user_headers, encryption_key):
    owner = make_user_headers("student1")
    intruder = make_user_headers("student2")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=owner)

    status = client.get(f"{CANVAS}/status", headers=intruder).get_json()
    assert status["status"] == "not_connected"


def test_reconnecting_replaces_the_previously_selected_courses(canvas_app, client, make_user_headers, encryption_key):
    headers = make_user_headers("student1")
    FakeCanvas.courses.append({"id": "202", "name": "Databases"})
    FakeCanvas.assignments["202"] = [
        {"canvas_id": "6001", "course_id": "202", "title": "Schema design", "deadline": "2026-12-01T00:00:00Z", "rubric": []}
    ]
    try:
        client.post(f"{CANVAS}/connect", json=import_payload(course_ids=["101"]), headers=headers)
        response = client.post(f"{CANVAS}/connect", json=import_payload(course_ids=["202"]), headers=headers)
        assert response.status_code == 200
        sync_response = client.post(f"{CANVAS}/sync", json={}, headers=headers)
        titles = {a["title"] for a in sync_response.get_json()["assignments"]}
        assert "Schema design" in titles
    finally:
        FakeCanvas.courses.pop()
        del FakeCanvas.assignments["202"]




def test_sync_all_resyncs_every_connected_account(canvas_app, client, make_user_headers, encryption_key, monkeypatch):
    import app.cli as cli_module

    monkeypatch.setattr(cli_module, "CanvasClient", FakeCanvas)

    student1 = make_user_headers("student1")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=student1)
    FakeCanvas.assignments["101"][0]["title"] = "Renamed by sync-all"

    runner = canvas_app.test_cli_runner()
    result = runner.invoke(args=["canvas", "sync-all"])

    assert "synced=1 failed=0" in result.output
    assignments = client.get(ASSIGNMENTS, headers=student1).get_json()
    project = next(a for a in assignments if a["canvas_id"] == "5001")
    assert project["title"] == "Renamed by sync-all"
    FakeCanvas.assignments["101"][0]["title"] = "Project report"


def test_sync_all_skips_accounts_with_no_courses_selected(canvas_app, encryption_key, monkeypatch):
    import app.cli as cli_module

    monkeypatch.setattr(cli_module, "CanvasClient", FakeCanvas)

    runner = canvas_app.test_cli_runner()
    result = runner.invoke(args=["canvas", "sync-all"])
    assert "synced=0 failed=0" in result.output


def test_sync_all_does_nothing_when_canvas_is_not_configured(app):
    app.config["CANVAS_BASE_URL"] = None
    runner = app.test_cli_runner()
    result = runner.invoke(args=["canvas", "sync-all"])
    assert "not configured" in result.output


def test_sync_all_disconnects_and_continues_past_a_broken_connection(canvas_app, client, make_user_headers, encryption_key, monkeypatch):
    import app.cli as cli_module

    monkeypatch.setattr(cli_module, "CanvasClient", FakeCanvas)

    headers = make_user_headers("student1")
    client.post(f"{CANVAS}/connect", json=import_payload(), headers=headers)

    from cryptography.fernet import Fernet
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())

    runner = canvas_app.test_cli_runner()
    result = runner.invoke(args=["canvas", "sync-all"])
    assert "synced=0 failed=1" in result.output

    status = client.get(f"{CANVAS}/status", headers=headers).get_json()
    assert status["status"] == "disconnected"