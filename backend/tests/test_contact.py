def test_a_visitor_contact_message_reaches_the_team_with_reply_to(app, client):
    sent = []
    app.config["CONTACT_EMAIL"] = "team@example.com"
    app.config["CONTACT_MAILER"] = lambda *args: sent.append(args)
    response = client.post(
        "/api/v1/contact",
        json={"name": "Ada", "email": "Ada@Example.com", "subject": "Question", "message": "Hello team."},
    )
    assert response.status_code == 200
    assert sent == [("team@example.com", "Ada", "ada@example.com", "Question", "Hello team.")]


def test_a_contact_message_needs_every_field(app, client):
    app.config["CONTACT_EMAIL"] = "team@example.com"
    app.config["CONTACT_MAILER"] = lambda *args: None
    response = client.post("/api/v1/contact", json={"name": "Ada", "email": "bad", "subject": "Hi", "message": "Hi"})
    assert response.status_code == 400
    assert "email" in response.get_json()["error"]


def test_a_subject_cannot_span_lines(app, client):
    app.config["CONTACT_EMAIL"] = "team@example.com"
    app.config["CONTACT_MAILER"] = lambda *args: None
    response = client.post(
        "/api/v1/contact",
        json={"name": "Ada", "email": "ada@example.com", "subject": "Hi\nBcc: x@example.com", "message": "Hi"},
    )
    assert response.status_code == 400


def test_contact_without_a_configured_inbox_is_503(app, client):
    app.config["CONTACT_EMAIL"] = None
    response = client.post(
        "/api/v1/contact",
        json={"name": "Ada", "email": "ada@example.com", "subject": "Hi", "message": "Hi"},
    )
    assert response.status_code == 503


def test_feedback_requires_sign_in(client):
    response = client.post("/api/v1/contact/feedback", json={"subject": "Hi", "message": "Hi"})
    assert response.status_code == 401


def test_signed_in_feedback_uses_the_account_identity(app, client, make_user_headers):
    sent = []
    app.config["CONTACT_EMAIL"] = "team@example.com"
    app.config["CONTACT_MAILER"] = lambda *args: sent.append(args)
    headers = make_user_headers("Grace")
    response = client.post(
        "/api/v1/contact/feedback", headers=headers, json={"subject": "Idea", "message": "Add dark mode."}
    )
    assert response.status_code == 200
    assert sent == [("team@example.com", "Grace", "grace@example.com", "Idea", "Add dark mode.")]
