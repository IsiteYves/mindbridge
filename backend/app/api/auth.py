import datetime as dt
import hashlib
import re
import secrets
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import RefreshToken, ReminderPreference, User
from app.services.codes import check_code, issue_code, seconds_until_next_code
from app.services.mailer import MailError, send_code
from app.services.passwords import (
    MAX_PASSWORD_LENGTH,
    hash_password,
    password_needs_rehash,
    password_problems,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

MAX_NAME_LENGTH = 120
MAX_EMAIL_LENGTH = 255
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ACCESS_TOKEN_LIFETIME = dt.timedelta(minutes=15)
REFRESH_LIFETIME = dt.timedelta(days=30)
REFRESH_COOKIE = "mindbridge_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
REFRESH_REUSE_GRACE = dt.timedelta(seconds=30)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT = dt.timedelta(minutes=15)
DEFAULT_REMINDER_OFFSETS = (5, 2, 1, 0)


@auth_bp.errorhandler(MailError)
def handle_mail_error(error):
    return jsonify(error=str(error)), 503


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _issue_token(user):
    payload = {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) + ACCESS_TOKEN_LIFETIME}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _hash_refresh(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def _session_response(user, status=200):
    raw = secrets.token_urlsafe(32)
    # Only a hash of the refresh token is stored; the raw value goes to the cookie only.
    db.session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_refresh(raw),
            expires_at=dt.datetime.now(dt.timezone.utc) + REFRESH_LIFETIME,
        )
    )
    db.session.commit()
    response = jsonify(token=_issue_token(user))
    response.status_code = status
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=int(REFRESH_LIFETIME.total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=current_app.config["COOKIE_SECURE"],
        path=REFRESH_COOKIE_PATH,
    )
    return response


def _end_session_response(message):
    response = jsonify(error=message) if message else jsonify(message="Logged out")
    response.status_code = 401 if message else 200
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
        secure=current_app.config["COOKIE_SECURE"],
    )
    return response


def _refresh_row(raw):
    if not raw:
        return None
    return db.session.query(RefreshToken).filter_by(token_hash=_hash_refresh(raw)).first()


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

    existing = _find_user(email)
    if existing is not None:
        return jsonify(error="An account with this email already exists", unverified=not existing.email_verified), 409

    user = User(name=name, email=email, password_hash=hash_password(data["password"]), email_verified=False)
    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="An account with this email already exists"), 409

    db.session.add_all(
        ReminderPreference(user_id=user.id, offset_days=offset, enabled=True)
        for offset in DEFAULT_REMINDER_OFFSETS
    )

    code = issue_code(user, "signup")
    # Mail is sent before the commit, so a mail failure rolls the new account back.
    try:
        send_code(email, "signup", code)
    except MailError:
        db.session.rollback()
        raise
    db.session.commit()
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
    return _session_response(user)


@auth_bp.post("/resend-code")
def resend_code():
    email = _clean_email(_json_body().get("email"))
    user = _find_user(email)
    # The response is the same whether or not the account exists, so the endpoint cannot be used to find accounts.
    if user is not None and not user.email_verified:
        code = issue_code(user, "signup")
        if code is None:
            return (
                jsonify(error="Please wait before requesting another code", retry_after=seconds_until_next_code(user.id, "signup")),
                429,
            )
        db.session.commit()
        send_code(email, "signup", code)
    return jsonify(message="If that account is waiting for verification, a new code has been sent."), 200


@auth_bp.post("/login")
def login():
    data = _json_body()
    email = _clean_email(data.get("email"))
    password = data.get("password")
    user = _find_user(email)
    now = dt.datetime.now(dt.timezone.utc)

    locked = user is not None and user.locked_until is not None and user.locked_until > now
    if locked or user is None or not isinstance(password, str) or not verify_password(user.password_hash, password):
        if user is not None and not locked:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + LOGIN_LOCKOUT
            db.session.commit()
        return jsonify(error="Invalid email or password"), 401

    if not user.email_verified:
        return jsonify(error="Verify your email before signing in"), 403

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    return _session_response(user)


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

    user.password_hash = hash_password(data["password"])
    user.email_verified = True
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    return jsonify(message="Your password has been reset. You can sign in now."), 200


@auth_bp.post("/logout")
def logout():
    row = _refresh_row(request.cookies.get(REFRESH_COOKIE))
    if row is not None and row.revoked_at is None:
        row.revoked_at = dt.datetime.now(dt.timezone.utc)
        db.session.commit()
    return _end_session_response(None)


@auth_bp.post("/refresh")
def refresh():
    row = _refresh_row(request.cookies.get(REFRESH_COOKIE))
    now = dt.datetime.now(dt.timezone.utc)
    ended = "Your session has ended. Please sign in again."
    if row is None or row.expires_at <= now:
        return _end_session_response(ended)
    # A token rotated moments ago is still accepted, so parallel refresh calls do not log the user out.
    if row.revoked_at is not None and now - row.revoked_at > REFRESH_REUSE_GRACE:
        return _end_session_response(ended)
    user = db.session.get(User, row.user_id)
    if user is None:
        return _end_session_response(ended)
    if row.revoked_at is None:
        row.revoked_at = now
    return _session_response(user)


def _user_json(user):
    return {"id": user.id, "name": user.name, "email": user.email}


@auth_bp.get("/me")
@token_required
def me():
    return jsonify(_user_json(g.current_user))


@auth_bp.patch("/me")
@token_required
def update_me():
    name = _clean_name(_json_body().get("name"))
    if name is None:
        return jsonify(error=f"Name is required (at most {MAX_NAME_LENGTH} characters)"), 400
    g.current_user.name = name
    db.session.commit()
    return jsonify(_user_json(g.current_user))


@auth_bp.post("/email/request-change")
@token_required
def request_email_change():
    data = _json_body()
    user = g.current_user
    new_email = _clean_email(data.get("new_email"))
    if new_email is None:
        return jsonify(error="Enter a valid email address"), 400
    if new_email == user.email:
        return jsonify(error="That is already your email address"), 400
    current = data.get("current_password")
    if not isinstance(current, str) or not verify_password(user.password_hash, current):
        return jsonify(error="Your current password is incorrect"), 400
    if _find_user(new_email) is not None:
        return jsonify(error="An account with this email already exists"), 409

    code = issue_code(user, "email_change")
    if code is None:
        return (
            jsonify(error="Please wait before requesting another code", retry_after=seconds_until_next_code(user.id, "email_change")),
            429,
        )
    user.pending_email = new_email
    try:
        send_code(new_email, "email_change", code)
    except MailError:
        db.session.rollback()
        raise
    db.session.commit()
    return jsonify(message="We sent a code to your new address."), 200


@auth_bp.post("/email/confirm")
@token_required
def confirm_email_change():
    user = g.current_user
    code = _json_body().get("code")
    if not user.pending_email or not isinstance(code, str) or not check_code(user, "email_change", code):
        return jsonify(error="The code is invalid or has expired. Request a new one."), 400
    if _find_user(user.pending_email) is not None:
        user.pending_email = None
        db.session.commit()
        return jsonify(error="An account with this email already exists"), 409
    user.email = user.pending_email
    user.pending_email = None
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="An account with this email already exists"), 409
    return jsonify(_user_json(user))


@auth_bp.patch("/password")
@token_required
def change_password():
    data = _json_body()
    user = g.current_user
    current = data.get("current_password")
    if not isinstance(current, str) or not verify_password(user.password_hash, current):
        return jsonify(error="Your current password is incorrect"), 400
    password_error = _password_error(data)
    if password_error:
        return jsonify(error=password_error), 400
    user.password_hash = hash_password(data["password"])
    db.session.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)).update(
        {"revoked_at": dt.datetime.now(dt.timezone.utc)}, synchronize_session=False
    )
    return _session_response(user)