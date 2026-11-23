"""Focus-timer sessions."""

import datetime as dt

from flask import Blueprint, abort, g, jsonify, request

from app.api.auth import token_required
from app.api.common import json_body
from app.extensions import db
from app.models import FocusSession, Milestone

focus_bp = Blueprint("focus", __name__, url_prefix="/focus-sessions")

DEFAULT_MINUTES = 25
PRESET_MINUTES = (15, 25, 45, 60)
HISTORY_DEFAULT_LIMIT = 20
HISTORY_MAX_LIMIT = 100


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _planned_end(session):
    return session.started_at + dt.timedelta(minutes=session.planned_minutes)


def _close_if_expired(session, now):
    if session.ended_at is None and now >= _planned_end(session):
        session.ended_at = _planned_end(session)
        session.completed = True
        db.session.commit()
    return session


def session_json(session, now=None):
    now = now or _now()
    payload = {
        "id": session.id,
        "milestone_id": session.milestone_id,
        "planned_minutes": session.planned_minutes,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "completed": session.completed,
        "actual_minutes": None,
        "remaining_seconds": None,
    }
    if session.ended_at is not None:
        payload["actual_minutes"] = round((session.ended_at - session.started_at).total_seconds() / 60)
    else:
        payload["remaining_seconds"] = max(0, int((_planned_end(session) - now).total_seconds()))
    return payload


def _int_arg(name, default, minimum, maximum):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        return None
    return value if minimum <= value <= maximum else None


@focus_bp.post("")
@token_required
def start_session():
    data = json_body()

    planned_minutes = data.get("planned_minutes", DEFAULT_MINUTES)
    if isinstance(planned_minutes, bool) or not isinstance(planned_minutes, int):
        return jsonify(error="planned_minutes must be a whole number"), 400
    if planned_minutes not in PRESET_MINUTES:
        return jsonify(error=f"planned_minutes must be one of {', '.join(map(str, PRESET_MINUTES))}"), 400

    open_session = _open_session(g.current_user.id)
    if open_session is not None:
        _close_if_expired(open_session, _now())
        if open_session.ended_at is None:
            return jsonify(error="A focus session is already running."), 409

    milestone_id = data.get("milestone_id")
    if milestone_id is not None:
        if isinstance(milestone_id, bool) or not isinstance(milestone_id, int):
            return jsonify(error="milestone_id must be an integer, or omitted"), 400
        milestone = db.session.get(Milestone, milestone_id)
        if milestone is None or milestone.assignment.user_id != g.current_user.id:
            return jsonify(error="milestone_id does not refer to one of your milestones"), 400

    session = FocusSession(
        user_id=g.current_user.id,
        milestone_id=milestone_id,
        planned_minutes=planned_minutes,
        started_at=_now(),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify(session_json(session)), 201


def _open_session(user_id):
    return (
        db.session.query(FocusSession)
        .filter(FocusSession.user_id == user_id, FocusSession.ended_at.is_(None))
        .order_by(FocusSession.started_at.desc())
        .first()
    )


@focus_bp.get("/active")
@token_required
def active_session():
    session = _open_session(g.current_user.id)
    if session is None:
        return jsonify(session=None)
    now = _now()
    _close_if_expired(session, now)
    if session.ended_at is not None:
        return jsonify(session=None)
    return jsonify(session=session_json(session, now))


def owned_session_or_404(session_id):
    session = db.session.get(FocusSession, session_id)
    if session is None or session.user_id != g.current_user.id:
        abort(404)
    return session


@focus_bp.patch("/<int:session_id>/end")
@token_required
def end_session(session_id):
    session = owned_session_or_404(session_id)
    if session.ended_at is not None:
        return jsonify(error="This focus session has already ended."), 409

    now = _now()
    planned_end = _planned_end(session)
    session.ended_at = min(now, planned_end)
    session.completed = now >= planned_end
    db.session.commit()
    return jsonify(session_json(session))


@focus_bp.get("/today")
@token_required
def today_sessions():
    today = _now().date()
    start = dt.datetime.combine(today, dt.time.min, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    sessions = (
        db.session.query(FocusSession)
        .filter(
            FocusSession.user_id == g.current_user.id,
            FocusSession.started_at >= start,
            FocusSession.started_at < end,
        )
        .order_by(FocusSession.started_at)
        .all()
    )
    return jsonify([session_json(session) for session in sessions])


@focus_bp.get("")
@token_required
def history():
    limit = _int_arg("limit", HISTORY_DEFAULT_LIMIT, 1, HISTORY_MAX_LIMIT)
    offset = _int_arg("offset", 0, 0, 10**9)
    if limit is None or offset is None:
        return jsonify(error=f"limit must be 1 to {HISTORY_MAX_LIMIT} and offset must be 0 or more"), 400
    query = db.session.query(FocusSession).filter(FocusSession.user_id == g.current_user.id)
    total = query.count()
    sessions = query.order_by(FocusSession.started_at.desc()).offset(offset).limit(limit).all()
    return jsonify(items=[session_json(session) for session in sessions], total=total, limit=limit, offset=offset)
