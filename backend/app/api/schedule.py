import datetime as dt

from flask import Blueprint, abort, g, jsonify
from sqlalchemy import func

from app import scheduling
from app.api.auth import token_required
from app.api.common import iso_utc, json_body
from app.extensions import db
from app.models import Assignment, Milestone, Reminder, StudyPlan, StudySession, WellnessCheckin

schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")

SESSION_STATUSES = ("planned", "completed", "skipped")
DEFAULT_REMINDER_LEAD_MINUTES = 15
MAX_REMINDER_LEAD_MINUTES = 1440
CHECKIN_MAX_AGE_DAYS = 2


def reminder_json(reminder):
    return {
        "id": reminder.id,
        "study_session_id": reminder.study_session_id,
        "remind_at": iso_utc(reminder.remind_at),
        "status": reminder.status,
    }


def session_json(session):
    milestone = session.milestone
    assignment = milestone.assignment
    reminder = min(session.reminders, key=lambda r: r.id) if session.reminders else None
    return {
        "id": session.id,
        "study_plan_id": session.study_plan_id,
        "milestone_id": milestone.id,
        "milestone_title": milestone.title,
        "milestone_target_date": iso_utc(milestone.target_date),
        "assignment_id": assignment.id,
        "assignment_title": assignment.title,
        "course": assignment.course,
        "start_time": iso_utc(session.start_time),
        "end_time": iso_utc(session.end_time),
        "status": session.status,
        "reminder": reminder_json(reminder) if reminder else None,
    }


def plan_json(plan):
    return {
        "id": plan.id,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "status": plan.status,
    }


def _int_option(data, key, default, low, high):
    #Return (is_valid, value). Booleans are rejected because they are ints in Python.
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return False, None
    return True, value


def _resolve_stress(data, user_id, today):
    #Pick the stress level: explicit request value, else a recent check-in, else neutral.
    if data.get("stress_level") is not None:
        return data["stress_level"], "request"
    checkin = (
        db.session.query(WellnessCheckin)
        .filter(
            WellnessCheckin.user_id == user_id,
            WellnessCheckin.checkin_date >= today - dt.timedelta(days=CHECKIN_MAX_AGE_DAYS),
        )
        .order_by(WellnessCheckin.checkin_date.desc())
        .first()
    )
    if checkin is not None and scheduling.STRESS_MIN <= checkin.stress_level <= scheduling.STRESS_MAX:
        return checkin.stress_level, "checkin"
    return scheduling.DEFAULT_STRESS, "default"


def _active_plan(user_id):
    return (
        db.session.query(StudyPlan)
        .filter_by(user_id=user_id, status="active")
        .order_by(StudyPlan.id.desc())
        .first()
    )


def _sorted_sessions(plan):
    return sorted(plan.study_sessions, key=lambda s: (s.start_time, s.id))


@schedule_bp.get("")
@token_required
def get_schedule():
    plan = _active_plan(g.current_user.id)
    if plan is None:
        return jsonify(plan=None, sessions=[])
    return jsonify(plan=plan_json(plan), sessions=[session_json(s) for s in _sorted_sessions(plan)])


@schedule_bp.post("/generate")
@token_required
def generate_schedule():
    data = json_body()

    valid_stress = data.get("stress_level") is None or (
        isinstance(data["stress_level"], int)
        and not isinstance(data["stress_level"], bool)
        and scheduling.STRESS_MIN <= data["stress_level"] <= scheduling.STRESS_MAX
    )
    if not valid_stress:
        return jsonify(error=f"stress_level must be an integer from {scheduling.STRESS_MIN} to {scheduling.STRESS_MAX}"), 400

    options = {}
    for key, default, low, high in (
        ("daily_minutes", scheduling.DEFAULT_DAILY_MINUTES, scheduling.MIN_DAILY_MINUTES, scheduling.MAX_DAILY_MINUTES),
        ("horizon_days", scheduling.DEFAULT_HORIZON_DAYS, 1, scheduling.MAX_HORIZON_DAYS),
        ("blocks_per_milestone", scheduling.DEFAULT_BLOCKS_PER_MILESTONE, 1, scheduling.MAX_BLOCKS_PER_MILESTONE),
        ("start_hour", scheduling.DEFAULT_START_HOUR, 0, scheduling.MAX_START_HOUR),
        ("utc_offset_minutes", 0, -720, 840),
        ("reminder_lead_minutes", DEFAULT_REMINDER_LEAD_MINUTES, 0, MAX_REMINDER_LEAD_MINUTES),
    ):
        is_valid, value = _int_option(data, key, default, low, high)
        if not is_valid:
            return jsonify(error=f"{key} must be an integer from {low} to {high}"), 400
        options[key] = value

    user_id = g.current_user.id
    now = scheduling.utc_now()
    tz = dt.timezone(dt.timedelta(minutes=options["utc_offset_minutes"]))
    today = now.astimezone(tz).date()
    stress_level, stress_source = _resolve_stress(data, user_id, today)

    #  Retire the current plan: future planned sessions are dropped so they can be
    #  re-planned, planned sessions already in the past are kept as "missed", and
    #  completed or skipped sessions stay as history.
    missed = 0
    for old_plan in db.session.query(StudyPlan).filter_by(user_id=user_id, status="active").all():
        old_plan.status = "replaced"
        for session in list(old_plan.study_sessions):
            if session.status != "planned":
                continue
            if session.start_time < now:
                session.status = "missed"
                missed += 1
                for reminder in session.reminders:
                    reminder.status = "dismissed"
            else:
                db.session.delete(session)
    db.session.flush()

    open_milestones = (
        db.session.query(Milestone)
        .join(Assignment, Milestone.assignment_id == Assignment.id)
        .filter(Assignment.user_id == user_id, Assignment.status != "done", Milestone.status != "done")
        .all()
    )
    completed_counts = dict(
        db.session.query(StudySession.milestone_id, func.count(StudySession.id))
        .join(StudyPlan, StudySession.study_plan_id == StudyPlan.id)
        .filter(StudyPlan.user_id == user_id, StudySession.status == "completed")
        .group_by(StudySession.milestone_id)
        .all()
    )

    result = scheduling.plan_sessions(
        open_milestones,
        now=now,
        stress_level=stress_level,
        daily_minutes=options["daily_minutes"],
        horizon_days=options["horizon_days"],
        blocks_per_milestone=options["blocks_per_milestone"],
        utc_offset_minutes=options["utc_offset_minutes"],
        start_hour=options["start_hour"],
        completed_counts=completed_counts,
    )

    plan = StudyPlan(
        user_id=user_id,
        start_date=today,
        end_date=today + dt.timedelta(days=options["horizon_days"] - 1),
        status="active",
    )
    db.session.add(plan)
    db.session.flush()

    lead = dt.timedelta(minutes=options["reminder_lead_minutes"])
    for placement in result.placements:
        session = StudySession(
            study_plan_id=plan.id,
            milestone_id=placement.milestone_id,
            start_time=placement.start,
            end_time=placement.end,
            status="planned",
        )
        session.reminders.append(
            Reminder(user_id=user_id, remind_at=max(placement.start - lead, now), status="pending")
        )
        db.session.add(session)
    db.session.commit()

    milestones_by_id = {m.id: m for m in open_milestones}
    at_risk = [
        {
            **entry,
            "milestone_title": milestones_by_id[entry["milestone_id"]].title,
            "milestone_target_date": iso_utc(milestones_by_id[entry["milestone_id"]].target_date),
        }
        for entry in result.at_risk
    ]

    limits = result.limits
    return (
        jsonify(
            plan=plan_json(plan),
            sessions=[session_json(s) for s in _sorted_sessions(plan)],
            adaptation={
                "stress_level": stress_level,
                "stress_source": stress_source,
                "daily_minutes": options["daily_minutes"],
                "block_minutes": limits.block_minutes,
                "max_sessions_per_day": limits.max_sessions_per_day,
                "max_daily_study_minutes": limits.max_daily_study_minutes,
                "message": scheduling.adaptation_message(stress_level),
            },
            at_risk=at_risk,
            deferred_milestones=result.deferred,
            missed_sessions=missed,
        ),
        201,
    )


def owned_session_or_404(session_id):
    session = db.session.get(StudySession, session_id)
    if session is None or session.study_plan.user_id != g.current_user.id:
        abort(404)
    return session


@schedule_bp.patch("/sessions/<int:session_id>")
@token_required
def update_session(session_id):
    session = owned_session_or_404(session_id)
    status = json_body().get("status")
    if status not in SESSION_STATUSES:
        return jsonify(error=f"status must be one of {', '.join(SESSION_STATUSES)}"), 400

    session.status = status
    if status in ("completed", "skipped"):
        for reminder in session.reminders:
            reminder.status = "dismissed"
    db.session.commit()
    return jsonify(session_json(session))
