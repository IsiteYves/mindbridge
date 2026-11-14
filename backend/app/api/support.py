import re

from flask import Blueprint, jsonify

from app.api.common import clean_text, json_body
from app.extensions import db
from app.models import SupportMessage

support_bp = Blueprint("support", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_NAME_LENGTH = 120
MAX_EMAIL_LENGTH = 255
MIN_MESSAGE_LENGTH = 10
MAX_MESSAGE_LENGTH = 2000


@support_bp.post("/support")
def create_support_message():
    data = json_body()
    name = clean_text(data.get("name"), MAX_NAME_LENGTH)
    email = clean_text(data.get("email"), MAX_EMAIL_LENGTH)
    message = clean_text(data.get("message"), MAX_MESSAGE_LENGTH)

    if not name:
        return jsonify(error="Enter your name."), 400
    if not email or not EMAIL_PATTERN.match(email):
        return jsonify(error="Enter a valid email address."), 400
    if not message or len(message) < MIN_MESSAGE_LENGTH:
        return jsonify(error=f"Message must be at least {MIN_MESSAGE_LENGTH} characters."), 400

    entry = SupportMessage(name=name, email=email.lower(), message=message)
    db.session.add(entry)
    db.session.commit()
    return jsonify(id=entry.id), 201
