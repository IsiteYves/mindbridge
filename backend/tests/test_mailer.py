import smtplib

from app.services import mailer
from app.services.email_templates import code_email, message_email


def test_a_code_email_shows_the_code_in_both_parts():
    subject, text, html = code_email("signup", "482913")
    assert subject == "Verify your MindBridge email"
    assert "482913" in text
    assert "482913" in html
    assert "<img" not in html


def test_each_code_purpose_has_its_own_heading():
    headings = {code_email(purpose, "000000")[2] for purpose in ("signup", "email_change", "reset")}
    assert len(headings) == 3


def test_a_reminder_escapes_user_supplied_titles_in_the_html():
    _, html = message_email("Due soon", "<script>alert(1)</script> is due tomorrow.")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_a_message_becomes_one_paragraph_per_block():
    _, html = message_email("Heads up", "First line.\n\nSecond line.")
    assert html.count("<p ") == 2


def test_delivery_sends_a_multipart_message(app, monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["host"] = host

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    subject, text, html = code_email("reset", "123456")
    with app.app_context():
        app.config["SMTP_HOST"] = "smtp.test"
        app.config["SMTP_FROM"] = "MindBridge <no-reply@example.com>"
        mailer._deliver("student@example.com", subject, text, html)
    message = sent["message"]
    assert message.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in message.iter_parts()] == ["text/plain", "text/html"]
