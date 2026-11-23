from tests.conftest import STRONG_PASSWORD

AUTH = "/api/v1/auth"


def test_refresh_issues_a_new_access_token_from_the_cookie(client, make_user_headers):
    make_user_headers("alice")
    response = client.post(f"{AUTH}/refresh")
    assert response.status_code == 200
    assert response.get_json()["token"]


def test_refresh_without_a_cookie_is_rejected(app):
    response = app.test_client().post(f"{AUTH}/refresh")
    assert response.status_code == 401


def test_logout_ends_the_session(client, make_user_headers):
    make_user_headers("alice")
    assert client.post(f"{AUTH}/logout").status_code == 200
    assert client.post(f"{AUTH}/refresh").status_code == 401


def test_update_name(client, make_user_headers):
    headers = make_user_headers("alice")
    response = client.patch(f"{AUTH}/me", json={"name": "Alice Mukamana"}, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Alice Mukamana"


def test_update_name_rejects_blank(client, make_user_headers):
    headers = make_user_headers("alice")
    assert client.patch(f"{AUTH}/me", json={"name": "  "}, headers=headers).status_code == 400


def test_email_change_needs_the_current_password(client, make_user_headers):
    headers = make_user_headers("alice")
    response = client.post(
        f"{AUTH}/email/request-change",
        json={"new_email": "alice.new@example.com", "current_password": "Wrong-pass1"},
        headers=headers,
    )
    assert response.status_code == 400


def test_email_change_is_confirmed_with_the_code_sent_to_the_new_address(app, client, make_user_headers):
    headers = make_user_headers("alice")
    requested = client.post(
        f"{AUTH}/email/request-change",
        json={"new_email": "alice.new@example.com", "current_password": STRONG_PASSWORD},
        headers=headers,
    )
    assert requested.status_code == 200
    sent = app.config["SENT_CODES"][-1]
    assert sent["to"] == "alice.new@example.com" and sent["purpose"] == "email_change"

    confirmed = client.post(f"{AUTH}/email/confirm", json={"code": sent["code"]}, headers=headers)
    assert confirmed.status_code == 200
    assert confirmed.get_json()["email"] == "alice.new@example.com"
    assert client.get(f"{AUTH}/me", headers=headers).get_json()["email"] == "alice.new@example.com"


def test_email_change_rejects_a_wrong_code(client, make_user_headers):
    headers = make_user_headers("alice")
    client.post(
        f"{AUTH}/email/request-change",
        json={"new_email": "alice.new@example.com", "current_password": STRONG_PASSWORD},
        headers=headers,
    )
    response = client.post(f"{AUTH}/email/confirm", json={"code": "000000"}, headers=headers)
    assert response.status_code == 400


def test_email_change_is_rate_limited(client, make_user_headers):
    headers = make_user_headers("alice")
    body = {"new_email": "alice.new@example.com", "current_password": STRONG_PASSWORD}
    assert client.post(f"{AUTH}/email/request-change", json=body, headers=headers).status_code == 200
    again = client.post(f"{AUTH}/email/request-change", json=body, headers=headers)
    assert again.status_code == 429
    assert 0 < again.get_json()["retry_after"] <= 300


def test_password_change_requires_the_current_password(client, make_user_headers):
    headers = make_user_headers("alice")
    response = client.patch(
        f"{AUTH}/password",
        json={"current_password": "Wrong-pass1", "password": "Newer-pass2", "confirm_password": "Newer-pass2"},
        headers=headers,
    )
    assert response.status_code == 400


def test_password_change_applies_the_new_password(client, make_user_headers):
    headers = make_user_headers("alice")
    response = client.patch(
        f"{AUTH}/password",
        json={"current_password": STRONG_PASSWORD, "password": "Newer-pass2", "confirm_password": "Newer-pass2"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "token" in response.get_json()
    login = client.post(f"{AUTH}/login", json={"email": "alice@example.com", "password": "Newer-pass2"})
    assert login.status_code == 200
