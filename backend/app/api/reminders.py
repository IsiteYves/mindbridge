import datetime as dt

from flask import Blueprint, abort, g, jsonify, request

from app import scheduling
from app.api.auth import token_required
from app.api.common import iso_utc, json_body
from app.extensions import db
from app.models import Assignment, Milestone, Reminder, StudySession

reminders_bp = Blueprint("reminders", __name__, url_prefix="/reminders")

REMINDER_STATUSES = ("pending", "dismissed")
DEFAULT_WINDOW_HOURS = 72
MAX_WINDOW_HOURS = 720
OVERDUE_LOOKBACK = dt.timedelta(days=14)
URGENT_WITHIN = dt.timedelta(hours=24)
SOON_WITHIN = dt.timedelta(hours=72)
DEFAULT_SNOOZE_MINUTES = 30
MIN_SNOOZE_MINUTES = 5
MAX_SNOOZE_MINUTES = 1440


def reminder_json(reminder):
    session = reminder.study_session
    milestone = session.milestone
    assignment = milestone.assignment
    return {
        "id": reminder.id,
        "study_session_id": session.id,
        "remind_at": iso_utc(reminder.remind_at),
        "status": reminder.status,
        "session": {
            "start_time": iso_utc(session.start_time),
            "end_time": iso_utc(session.end_time),
            "status": session.status,
            "milestone_title": milestone.title,
            "assignment_title": assignment.title,
            "course": assignment.course,
        },
    }


def owned_reminder_or_404(reminder_id):
    reminder = db.session.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != g.current_user.id:
        abort(404)
    return reminder


def deadline_level(due_at, now):
    #Classifying how pressing a deadline is: overdue, urgent (24h), soon (72h) or upcoming.
    remaining = due_at - now
    if remaining < dt.timedelta(0):
        return "overdue"
    if remaining <= URGENT_WITHIN:
        return "urgent"
    if remaining <= SOON_WITHIN:
        return "soon"
    return "upcoming"


def _alert(kind, item_id, title, course, due_at, now, **extra):
    return {
        "kind": kind,
        "id": item_id,
        "title": title,
        "course": course,
        "due_at": iso_utc(due_at),
        "hours_remaining": round((due_at - now).total_seconds() / 3600, 1),
        "level": deadline_level(due_at, now),
        **extra,
    }


def deadline_alerts(user_id, now, window):
    #Opening assignments and milestones that are overdue (recently) or due within the window.
    earliest, latest = now - OVERDUE_LOOKBACK, now + window
    alerts = []

    assignments = (
        db.session.query(Assignment)
        .filter(
            Assignment.user_id == user_id,
            Assignment.status != "done",
            Assignment.deadline.isnot(None),
            Assignment.deadline >= earliest,
            Assignment.deadline <= latest,
        )
        .all()
    )
    for a in assignments:
        alerts.append(_alert("assignment", a.id, a.title, a.course, a.deadline, now, assignment_id=a.id))

    milestones = (
        db.session.query(Milestone)
        .join(Assignment, Milestone.assignment_id == Assignment.id)
        .filter(
            Assignment.user_id == user_id,
            Assignment.status != "done",
            Milestone.status != "done",
            Milestone.target_date >= earliest,
            Milestone.target_date <= latest,
        )
        .all()
    )
    for m in milestones:
        alerts.append(
            _alert("milestone", m.id, m.title, m.assignment.course, m.target_date, now, assignment_id=m.assignment_id)
        )

    alerts.sort(key=lambda a: (a["due_at"], a["kind"], a["id"]))
    return alerts


@reminders_bp.get("")
@token_required
def list_reminders():
    status = request.args.get("status")
    if status is not None and status not in REMINDER_STATUSES:
        return jsonify(error=f"status must be one of {', '.join(REMINDER_STATUSES)}"), 400

    query = db.session.query(Reminder).filter_by(user_id=g.current_user.id)
    if status:
        query = query.filter_by(status=status)
    reminders = query.order_by(Reminder.remind_at, Reminder.id).all()
    return jsonify([reminder_json(r) for r in reminders])


@reminders_bp.get("/upcoming")
@token_required
def upcoming():
    raw = request.args.get("hours", str(DEFAULT_WINDOW_HOURS))
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_WINDOW_HOURS:
        return jsonify(error=f"hours must be an integer from 1 to {MAX_WINDOW_HOURS}"), 400
    window = dt.timedelta(hours=int(raw))

    user_id = g.current_user.id
    now = scheduling.utc_now()

    pending = (
        db.session.query(Reminder)
        .join(StudySession, Reminder.study_session_id == StudySession.id)
        .filter(
            Reminder.user_id == user_id,
            Reminder.status == "pending",
            StudySession.status == "planned",
            StudySession.end_time > now,
            Reminder.remind_at <= now + window,
        )
        .order_by(Reminder.remind_at, Reminder.id)
        .all()
    )
    session_reminders = [{**reminder_json(r), "due": r.remind_at <= now} for r in pending]

    return jsonify(
        now=iso_utc(now),
        window_hours=int(raw),
        session_reminders=session_reminders,
        deadline_alerts=deadline_alerts(user_id, now, window),
    )


@reminders_bp.post("/<int:reminder_id>/dismiss")
@token_required
def dismiss(reminder_id):
    reminder = owned_reminder_or_404(reminder_id)
    reminder.status = "dismissed"
    db.session.commit()
    return jsonify(reminder_json(reminder))


@reminders_bp.post("/<int:reminder_id>/snooze")
@token_required
def snooze(reminder_id):
    reminder = owned_reminder_or_404(reminder_id)
    minutes = json_body().get("minutes", DEFAULT_SNOOZE_MINUTES)
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not MIN_SNOOZE_MINUTES <= minutes <= MAX_SNOOZE_MINUTES:
        return jsonify(error=f"minutes must be an integer from {MIN_SNOOZE_MINUTES} to {MAX_SNOOZE_MINUTES}"), 400

    remind_at = scheduling.utc_now() + dt.timedelta(minutes=minutes)
    if remind_at >= reminder.study_session.end_time:
        return jsonify(error="Snoozing that long would pass the end of the study session"), 400

    reminder.remind_at = remind_at
    reminder.status = "pending"
    db.session.commit()
    return jsonify(reminder_json(reminder))
