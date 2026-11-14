import datetime as dt

from flask import Blueprint, g, jsonify, request

from app.api.auth import token_required
from app.api.common import iso_utc
from app.extensions import db
from app.models import Assignment, Milestone, WellnessCheckin
from app.services.adaptive import (
    RECENT_CHECKINS,
    STRESS_WINDOW_DAYS,
    in_window,
    slack_fraction,
    stress_average,
    suggested_target,
)

schedule_bp = Blueprint("schedule", __name__)

DEFAULT_DAYS, MAX_DAYS = 14, 60
DEFAULT_HOURS, MAX_HOURS = 72, 336


def _int_arg(name, default, maximum):
    #Return (is_valid, value) for an integer query argument between 1 and maximum.
    try:
        value = int(request.args.get(name, default))
    except ValueError:
        return False, None
    return (1 <= value <= maximum), value


def _recent_stress(user_id, now):
    today = now.date()
    checkins = (
        db.session.query(WellnessCheckin)
        .filter(
            WellnessCheckin.user_id == user_id,
            WellnessCheckin.checkin_date >= today - dt.timedelta(days=STRESS_WINDOW_DAYS),
            WellnessCheckin.checkin_date <= today,
        )
        .order_by(WellnessCheckin.checkin_date.desc())
        .limit(RECENT_CHECKINS)
        .all()
    )
    return stress_average(c.stress_level for c in checkins)


def _open_milestones(user_id, now):
    """Open milestones of the user's assignments whose target is still in the future."""
    return (
        db.session.query(Milestone)
        .join(Assignment)
        .filter(
            Assignment.user_id == user_id,
            Milestone.status != "done",
            Milestone.target_date >= now,
        )
        .all()
    )


def _milestone_json(milestone, suggested):
    return {
        "id": milestone.id,
        "assignment_id": milestone.assignment_id,
        "course": milestone.assignment.course,
        "assignment_title": milestone.assignment.title,
        "title": milestone.title,
        "status": milestone.status,
        "target_date": iso_utc(milestone.target_date),
        "suggested_date": iso_utc(suggested),
    }


@schedule_bp.get("/schedule")
@token_required
def get_schedule():
    is_valid, days = _int_arg("days", DEFAULT_DAYS, MAX_DAYS)
    if not is_valid:
        return jsonify(error=f"days must be an integer from 1 to {MAX_DAYS}"), 400

    now = dt.datetime.now(dt.timezone.utc)
    average = _recent_stress(g.current_user.id, now)
    slack = slack_fraction(average)

    milestones = []
    for milestone in _open_milestones(g.current_user.id, now):
        if not in_window(milestone.target_date, now, days * 24):
            continue
        suggested = suggested_target(milestone.target_date, now, slack)
        milestones.append(_milestone_json(milestone, suggested))
    milestones.sort(key=lambda item: (item["suggested_date"], item["id"]))

    return jsonify(
        stress_average=None if average is None else round(average, 2),
        slack_fraction=slack,
        milestones=milestones,
    )


@schedule_bp.get("/reminders")
@token_required
def get_reminders():
    is_valid, hours = _int_arg("hours", DEFAULT_HOURS, MAX_HOURS)
    if not is_valid:
        return jsonify(error=f"hours must be an integer from 1 to {MAX_HOURS}"), 400

    now = dt.datetime.now(dt.timezone.utc)
    average = _recent_stress(g.current_user.id, now)
    slack = slack_fraction(average)
    reminders = []

    # A milestone is due when its suggested date falls in the window.
    for milestone in _open_milestones(g.current_user.id, now):
        suggested = suggested_target(milestone.target_date, now, slack)
        if in_window(suggested, now, hours):
            reminders.append(
                {
                    "kind": "milestone",
                    "id": milestone.id,
                    "title": milestone.title,
                    "course": milestone.assignment.course,
                    "due_at": iso_utc(suggested),
                    "hours_left": round((suggested - now).total_seconds() / 3600, 1),
                }
            )

    deadlines = (
        db.session.query(Assignment)
        .filter(
            Assignment.user_id == g.current_user.id,
            Assignment.status != "done",
            Assignment.deadline >= now,
        )
        .all()
    )
    for assignment in deadlines:
        if in_window(assignment.deadline, now, hours):
            reminders.append(
                {
                    "kind": "deadline",
                    "id": assignment.id,
                    "title": assignment.title,
                    "course": assignment.course,
                    "due_at": iso_utc(assignment.deadline),
                    "hours_left": round((assignment.deadline - now).total_seconds() / 3600, 1),
                }
            )

    reminders.sort(key=lambda item: (item["due_at"], item["kind"], item["id"]))
    return jsonify(reminders)
