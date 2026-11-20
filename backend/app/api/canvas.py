import datetime as dt

from flask import Blueprint, current_app, g, jsonify
from sqlalchemy.exc import IntegrityError

from app.api.assignments import assignment_json
from app.api.auth import token_required
from app.api.common import clean_text, iso_utc, json_body, parse_deadline
from app.extensions import db
from app.models import Assignment, LMSIntegration
from app.services.canvas import CanvasClient, CanvasError
from app.services.canvas_sync import sync_courses
from app.services.crypto import EncryptionNotConfigured, decrypt_secret, encrypt_secret

canvas_bp = Blueprint("canvas", __name__, url_prefix="/canvas")

MAX_TOKEN_LENGTH = 512
MAX_COURSES_PER_IMPORT = 50
PROVIDER = "canvas"


@canvas_bp.errorhandler(CanvasError)
def handle_canvas_error(error):
    return jsonify(error=str(error)), error.status_code


@canvas_bp.errorhandler(EncryptionNotConfigured)
def handle_encryption_not_configured(_error):
    # A deployment that has not set TOKEN_ENCRYPTION_KEY cannot safely store a
    # Canvas token at rest. That is a server configuration gap, not something
    # the student did wrong, so this is a 503, not a 400.
    return jsonify(error="Saving a Canvas connection is not configured on this server"), 503


def _client(token):
    base_url = current_app.config.get("CANVAS_BASE_URL")
    if not base_url:
        raise CanvasError("Canvas integration is not configured", 503)
    return CanvasClient(base_url, token)


def _token(data):
    return clean_text(data.get("token"), MAX_TOKEN_LENGTH)


def _valid_course_ids(course_ids):
    return (
        isinstance(course_ids, list)
        and 0 < len(course_ids) <= MAX_COURSES_PER_IMPORT
        and all(isinstance(c, (int, str)) and not isinstance(c, bool) for c in course_ids)
    )


def _integration_for(user_id):
    return db.session.query(LMSIntegration).filter_by(user_id=user_id, provider=PROVIDER).one_or_none()


def _integration_json(integration):
    if integration is None:
        return {"provider": PROVIDER, "status": "not_connected", "last_synced_at": None}
    return {
        "provider": PROVIDER,
        "status": integration.status,
        "last_synced_at": iso_utc(integration.last_synced_at),
    }


@canvas_bp.post("/courses")
@token_required
def list_courses():
    data = json_body()
    token = _token(data)
    if token is None:
        return jsonify(error="token is required"), 400
    return jsonify(_client(token).list_courses())


@canvas_bp.post("/import")
@token_required
def import_assignments():
    """One-shot import: the token is used for this call only and never
    stored. See /connect for a persistent connection that remembers it.
    """
    data = json_body()
    token = _token(data)
    course_ids = data.get("course_ids")
    if token is None or not _valid_course_ids(course_ids):
        return jsonify(error=f"token and 1 to {MAX_COURSES_PER_IMPORT} course_ids are required"), 400

    result = sync_courses(g.current_user, _client(token), course_ids)
    return jsonify(**{**result, "assignments": [assignment_json(a) for a in result["assignments"]]})


@canvas_bp.get("/status")
@token_required
def connection_status():
    return jsonify(_integration_json(_integration_for(g.current_user.id)))


@canvas_bp.post("/connect")
@token_required
def connect():
    """Store the token (encrypted) and the chosen courses, run the first
    import, and mark the connection active — so later syncs need neither the
    token pasted again nor the courses re-chosen. See app/services/crypto.py
    for how the token itself is protected at rest.
    """
    data = json_body()
    token = _token(data)
    course_ids = data.get("course_ids")
    if token is None or not _valid_course_ids(course_ids):
        return jsonify(error=f"token and 1 to {MAX_COURSES_PER_IMPORT} course_ids are required"), 400

    result = sync_courses(g.current_user, _client(token), course_ids)

    integration = _integration_for(g.current_user.id)
    if integration is None:
        integration = LMSIntegration(user_id=g.current_user.id, provider=PROVIDER)
        db.session.add(integration)
    integration.status = "connected"
    integration.access_token_encrypted = encrypt_secret(token)
    integration.selected_course_ids = list(dict.fromkeys(str(c) for c in course_ids))
    integration.last_synced_at = dt.datetime.now(dt.timezone.utc)
    db.session.commit()

    response = {**result, "assignments": [assignment_json(a) for a in result["assignments"]]}
    return jsonify(**response, connection=_integration_json(integration))


@canvas_bp.post("/sync")
@token_required
def sync():
    """Re-run the import using the stored token and course selection. No
    token or course_ids in the request body — if either is missing, the
    student has not connected yet (or disconnected since), and the right
    next step is /connect, not this.
    """
    integration = _integration_for(g.current_user.id)
    if integration is None or integration.status != "connected" or not integration.access_token_encrypted:
        return jsonify(error="Canvas is not connected yet. Connect it first."), 409

    token = decrypt_secret(integration.access_token_encrypted)
    if token is None:
        # The stored ciphertext cannot be read back — most likely the
        # encryption key changed since it was saved. The old token is
        # unrecoverable; reconnecting replaces it with a fresh one.
        integration.status = "disconnected"
        db.session.commit()
        return jsonify(error="Your Canvas connection could not be read back. Please reconnect."), 409

    course_ids = integration.selected_course_ids or []
    if not course_ids:
        return jsonify(error="No courses are selected for this connection. Reconnect to choose some."), 409

    result = sync_courses(g.current_user, _client(token), course_ids)
    integration.last_synced_at = dt.datetime.now(dt.timezone.utc)
    db.session.commit()

    response = {**result, "assignments": [assignment_json(a) for a in result["assignments"]]}
    return jsonify(**response, connection=_integration_json(integration))


@canvas_bp.delete("/connection")
@token_required
def disconnect():
    """Forget the stored token. Past imports are untouched — disconnecting
    stops future syncs, it does not undo anything already brought in.
    """
    integration = _integration_for(g.current_user.id)
    if integration is None:
        return jsonify(_integration_json(None))

    integration.status = "disconnected"
    integration.access_token_encrypted = None
    integration.selected_course_ids = None
    db.session.commit()
    return jsonify(_integration_json(integration))
