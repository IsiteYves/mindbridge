import datetime as dt
import re
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User
from app.services.codes import check_code, issue_code
from app.services.mailer import MailError, send_code
from app.services.passwords import MAX_PASSWORD_LENGTH, password_problems

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

MAX_NAME_LENGTH = 120
MAX_EMAIL_LENGTH = 255
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOKEN_LIFETIME = dt.timedelta(hours=1)


@auth_bp.errorhandler(MailError)
def handle_mail_error(error):
    return jsonify(error=str(error)), 503


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _issue_token(user):
    payload = {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) + TOKEN_LIFETIME}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _clean_name(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if 0 < len(value) <= MAX_NAME_LENGTH else None


def _clean_email(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if len(value) <= MAX_EMAIL_LENGTH and EMAIL_PATTERN.match(value) else None


def _find_user(email):
    return db.session.query(User).filter_by(email=email).first() if email else None


def _password_error(data):
    """Return an error message if the password or its confirmation is not acceptable, else None."""
    password = data.get("password")
    if not isinstance(password, str) or not password:
        return "Password is required"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters"
    problems = password_problems(password)
    if problems:
        return "Password must include " + ", ".join(problems)
    if data.get("confirm_password") != password:
        return "Passwords do not match"
    return None


def token_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme != "Bearer" or not token:
            return jsonify(error="Missing bearer token"), 401

        try:
            payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify(error="Invalid or expired token"), 401

        subject = str(payload.get("sub", ""))
        user = db.session.get(User, int(subject)) if subject.isdigit() else None
        if user is None:
            return jsonify(error="Invalid or expired token"), 401

        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


@auth_bp.post("/register")
def register():
    data = _json_body()
    name = _clean_name(data.get("name"))
    email = _clean_email(data.get("email"))
    if name is None:
        return jsonify(error=f"Name is required (at most {MAX_NAME_LENGTH} characters)"), 400
    if email is None:
        return jsonify(error="Enter a valid email address"), 400
    password_error = _password_error(data)
    if password_error:
        return jsonify(error=password_error), 400

    if _find_user(email) is not None:
        return jsonify(error="An account with this email already exists"), 409

    user = User(name=name, email=email, password_hash=generate_password_hash(data["password"]), email_verified=False)
    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="An account with this email already exists"), 409

    code = issue_code(user, "signup")
    db.session.commit()
    send_code(email, "signup", code)
    return jsonify(email=email), 201


@auth_bp.post("/verify-email")
def verify_email():
    data = _json_body()
    email = _clean_email(data.get("email"))
    code = data.get("code")
    user = _find_user(email)
    if user is None or user.email_verified or not isinstance(code, str) or not check_code(user, "signup", code):
        return jsonify(error="The code is invalid or has expired. Request a new one."), 400

    user.email_verified = True
    db.session.commit()
    return jsonify(token=_issue_token(user)), 200


@auth_bp.post("/resend-code")
def resend_code():
    email = _clean_email(_json_body().get("email"))
    user = _find_user(email)
    # The response is the same whether or not the account exists, so the endpoint cannot be used to find accounts.
    if user is not None and not user.email_verified:
        code = issue_code(user, "signup")
        if code is None:
            return jsonify(error="Wait a minute before requesting another code"), 429
        db.session.commit()
        send_code(email, "signup", code)
    return jsonify(message="If that account is waiting for verification, a new code has been sent."), 200


@auth_bp.post("/login")
def login():
    data = _json_body()
    email = _clean_email(data.get("email"))
    password = data.get("password")
    user = _find_user(email)

    if user is None or not isinstance(password, str) or not check_password_hash(user.password_hash, password):
        return jsonify(error="Invalid email or password"), 401
    if not user.email_verified:
        return jsonify(error="Verify your email before signing in"), 403

    return jsonify(token=_issue_token(user)), 200


@auth_bp.post("/forgot-password")
def forgot_password():
    email = _clean_email(_json_body().get("email"))
    user = _find_user(email)
    # Always answer the same way, so the endpoint cannot be used to find accounts.
    if user is not None and user.email_verified:
        code = issue_code(user, "reset")
        if code is not None:
            db.session.commit()
            send_code(email, "reset", code)
    return jsonify(message="If an account exists for that email, a reset code has been sent."), 200


@auth_bp.post("/reset-password")
def reset_password():
    data = _json_body()
    email = _clean_email(data.get("email"))
    code = data.get("code")
    password_error = _password_error(data)
    if password_error:
        return jsonify(error=password_error), 400

    user = _find_user(email)
    if user is None or not isinstance(code, str) or not check_code(user, "reset", code):
        return jsonify(error="The code is invalid or has expired. Request a new one."), 400

    user.password_hash = generate_password_hash(data["password"])
    # Resetting the password also proves the email belongs to the user.
    user.email_verified = True
    db.session.commit()
    return jsonify(message="Your password has been reset. You can sign in now."), 200


@auth_bp.post("/logout")
def logout():
    # Tokens are stateless, so the client discards its token and it expires after one hour.
    return jsonify(message="Logged out"), 200
