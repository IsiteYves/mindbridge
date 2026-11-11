import pytest
import requests

from app.services.canvas import CanvasClient, CanvasError

BASE_URL = "https://canvas.test"
TOKEN = "canvas-token-value-123"


class FakeResponse:
    def __init__(self, payload, status_code=200, links=None):
        self._payload = payload
        self.status_code = status_code
        self.links = links or {}

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def client_with(*responses):
    session = FakeSession(responses)
    return CanvasClient(BASE_URL + "/", TOKEN, session=session), session


def test_requests_send_bearer_token_and_timeout():
    client, session = client_with(FakeResponse([]))

    client.list_courses()

    assert session.headers["Authorization"] == f"Bearer {TOKEN}"
    assert session.calls[0][2] is not None


def test_list_courses_keeps_named_active_courses_only():
    client, _ = client_with(
        FakeResponse(
            [
                {"id": 101, "name": "Software Engineering"},
                {"id": 102},
                {"id": None, "name": "Broken"},
            ]
        )
    )

    assert client.list_courses() == [{"id": "101", "name": "Software Engineering"}]


def test_list_assignments_follows_next_links_on_the_same_host():
    first = FakeResponse(
        [{"id": 1, "name": "Lab 1", "due_at": "2026-11-10T09:00:00Z"}],
        links={"next": {"url": f"{BASE_URL}/api/v1/courses/7/assignments?page=2"}},
    )
    second = FakeResponse([{"id": 2, "name": "Lab 2", "due_at": None}])
    client, session = client_with(first, second)

    items = client.list_assignments("7")

    assert [item["canvas_id"] for item in items] == ["1", "2"]
    assert session.calls[0][1]["include[]"] == "rubric"
    assert session.calls[1][1] is None


def test_next_link_to_another_host_is_refused_before_sending_the_token():
    first = FakeResponse([], links={"next": {"url": "https://evil.example/api/v1/courses"}})
    client, session = client_with(first)

    with pytest.raises(CanvasError) as error:
        client.list_courses()

    assert error.value.status_code == 502
    assert len(session.calls) == 1


def test_assignment_is_normalized_with_rubric_and_truncated_title():
    long_title = "x" * 400
    client, _ = client_with(
        FakeResponse(
            [
                {
                    "id": 55,
                    "name": long_title,
                    "due_at": "2026-11-12T23:59:00Z",
                    "rubric": [{"description": "Methodology", "points": 10}, {"points": 5}],
                }
            ]
        )
    )

    (item,) = client.list_assignments("9")

    assert item["canvas_id"] == "55"
    assert item["course_id"] == "9"
    assert len(item["title"]) == 255
    assert item["deadline"] == "2026-11-12T23:59:00Z"
    assert item["rubric"] == [
        {"title": "Methodology", "points": 10},
        {"title": "Criterion", "points": 5},
    ]


def test_unauthorized_token_maps_to_401_without_echoing_the_token():
    client, _ = client_with(FakeResponse({"errors": "bad"}, status_code=401))

    with pytest.raises(CanvasError) as error:
        client.list_courses()

    assert error.value.status_code == 401
    assert TOKEN not in str(error.value)


def test_network_failure_maps_to_502():
    client, _ = client_with(requests.ConnectionError("down"))

    with pytest.raises(CanvasError) as error:
        client.list_courses()

    assert error.value.status_code == 502
