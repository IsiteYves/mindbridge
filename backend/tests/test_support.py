from app.models import SupportMessage


def valid_payload(**overrides):
    payload = {"name": "Ada Student", "email": "ada@example.com", "message": "The import button is not working."}
    payload.update(overrides)
    return payload


def test_creates_support_message(client, app):
    response = client.post("/api/v1/support", json=valid_payload(email="Ada@Example.com"))

    assert response.status_code == 201
    assert isinstance(response.get_json()["id"], int)
    with app.app_context():
        entry = SupportMessage.query.one()
        assert entry.email == "ada@example.com"
        assert entry.status == "new"


def test_rejects_missing_name(client):
    response = client.post("/api/v1/support", json=valid_payload(name="   "))
    assert response.status_code == 400
    assert "name" in response.get_json()["error"]


def test_rejects_invalid_email(client):
    response = client.post("/api/v1/support", json=valid_payload(email="not-an-email"))
    assert response.status_code == 400


def test_rejects_short_message(client):
    response = client.post("/api/v1/support", json=valid_payload(message="help"))
    assert response.status_code == 400


def test_rejects_overlong_message(client):
    response = client.post("/api/v1/support", json=valid_payload(message="x" * 2001))
    assert response.status_code == 400


def test_rejects_non_json_body(client):
    response = client.post("/api/v1/support", data="hello", content_type="text/plain")
    assert response.status_code == 400
