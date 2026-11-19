"""Focus-timer sessions."""

import datetime as dt

from flask import Blueprint, abort, g, jsonify

from app.api.auth import token_required
from app.api.common import json_body
from app.extensions import db
from app.models import FocusSession, Milestone

focus_bp = Blueprint("focus", __name__, url_prefix="/focus-sessions")

DEFAULT_MINUTES = 25
MIN_MINUTES, MAX_MINUTES = 5, 120


def _now():
    return dt.datetime.now(dt.timezone.utc)


def session_json(session):
    return {
        "id": session.id,
        "milestone_id": session.milestone_id,
        "planned_minutes": session.planned_minutes,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "completed": session.completed,
    }


@focus_bp.post("")
@token_required
def start_session():
    data = json_body()

    planned_minutes = data.get("planned_minutes", DEFAULT_MINUTES)
    if isinstance(planned_minutes, bool) or not isinstance(planned_minutes, int):
        return jsonify(error="planned_minutes must be a whole number"), 400
    if not MIN_MINUTES <= planned_minutes <= MAX_MINUTES:
        return jsonify(error=f"planned_minutes must be from {MIN_MINUTES} to {MAX_MINUTES}"), 400

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

    data = json_body()
    completed = data.get("completed", True)
    if not isinstance(completed, bool):
        return jsonify(error="completed must be true or false"), 400

    session.ended_at = _now()
    session.completed = completed
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
