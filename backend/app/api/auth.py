import datetime as dt
from functools import wraps

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

MAX_USERNAME_LENGTH = 64
MIN_PASSWORD_LENGTH = 8
TOKEN_LIFETIME = dt.timedelta(hours=1)


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _issue_token(user):
    payload = {"sub": str(user.id), "exp": dt.datetime.now(dt.timezone.utc) + TOKEN_LIFETIME}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


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
    username = data.get("username")
    username = username.strip() if isinstance(username, str) else ""
    password = data.get("password")
    password = password if isinstance(password, str) else ""

    if not username or len(username) > MAX_USERNAME_LENGTH:
        return jsonify(error=f"Username is required and must be at most {MAX_USERNAME_LENGTH} characters"), 400
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify(error=f"Password must be at least {MIN_PASSWORD_LENGTH} characters"), 400

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Username is already taken"), 409

    return jsonify(id=user.id, username=user.username), 201


@auth_bp.post("/login")
def login():
    data = _json_body()
    username = data.get("username")
    password = data.get("password")
    user = db.session.query(User).filter_by(username=username).first() if isinstance(username, str) else None

    if user is None or not isinstance(password, str) or not check_password_hash(user.password_hash, password):
        return jsonify(error="Invalid username or password"), 401

    return jsonify(token=_issue_token(user)), 200


@auth_bp.post("/logout")
def logout():
    # Tokens are stateless, so the client discards its token and it expires after one hour.
    return jsonify(message="Logged out"), 200
