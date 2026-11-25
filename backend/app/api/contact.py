from flask import Blueprint, current_app, g, jsonify

from app.api.auth import EMAIL_PATTERN, token_required, _clean_email
from app.api.common import clean_text, json_body
from app.services.mailer import MailError, send_contact_message

contact_bp = Blueprint("contact", __name__, url_prefix="/contact")

MAX_NAME_LENGTH = 120
MAX_SUBJECT_LENGTH = 150
MAX_MESSAGE_LENGTH = 5000


@contact_bp.errorhandler(MailError)
def handle_mail_error(error):
    return jsonify(error=str(error)), 503


def _one_line(value):
    return value if value and "\n" not in value and "\r" not in value else None


def _deliver(name, sender_email, subject, message):
    to = current_app.config.get("CONTACT_EMAIL")
    if not to:
        raise MailError("Contact email is not configured on this server")
    send_contact_message(to, name, sender_email, subject, message)
    return jsonify(sent=True)


@contact_bp.post("")
def contact():
    data = json_body()
    name = clean_text(data.get("name"), MAX_NAME_LENGTH)
    email = _clean_email(data.get("email"))
    subject = _one_line(clean_text(data.get("subject"), MAX_SUBJECT_LENGTH))
    message = clean_text(data.get("message"), MAX_MESSAGE_LENGTH)
    if not name:
        return jsonify(error=f"Enter your name (at most {MAX_NAME_LENGTH} characters)"), 400
    if not email:
        return jsonify(error="Enter a valid email address"), 400
    if not subject:
        return jsonify(error=f"Enter a subject (at most {MAX_SUBJECT_LENGTH} characters)"), 400
    if not message:
        return jsonify(error=f"Enter a message (at most {MAX_MESSAGE_LENGTH} characters)"), 400
    return _deliver(name, email, subject, message)


@contact_bp.post("/feedback")
@token_required
def feedback():
    data = json_body()
    subject = _one_line(clean_text(data.get("subject"), MAX_SUBJECT_LENGTH))
    message = clean_text(data.get("message"), MAX_MESSAGE_LENGTH)
    if not subject:
        return jsonify(error=f"Enter a subject (at most {MAX_SUBJECT_LENGTH} characters)"), 400
    if not message:
        return jsonify(error=f"Enter a message (at most {MAX_MESSAGE_LENGTH} characters)"), 400
    return _deliver(g.current_user.name, g.current_user.email, subject, message)
