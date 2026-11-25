import datetime as dt

from flask import Blueprint, g, jsonify

from app.api.auth import token_required
from app.extensions import db
from app.models import Assignment, FocusSession, Milestone

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

DEADLINE_WEEKS = 4
FOCUS_DAYS = 7


@dashboard_bp.get("/summary")
@token_required
def summary():
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    user_id = g.current_user.id

    assignments = db.session.query(Assignment).filter(Assignment.user_id == user_id).all()
    counts = {"total": len(assignments), "pending": 0, "in_progress": 0, "closed": 0}
    weekly = [0] * DEADLINE_WEEKS
    for assignment in assignments:
        if assignment.status == "done" or assignment.deadline is None or assignment.deadline <= now:
            counts["closed"] += 1
            continue
        counts["pending"] += 1
        if assignment.status == "in_progress":
            counts["in_progress"] += 1
        # Week index counts 7-day blocks from today; 0 is the coming week.
        week = (assignment.deadline.date() - today).days // 7
        if 0 <= week < DEADLINE_WEEKS:
            weekly[week] += 1

    milestones = db.session.query(Milestone).join(Assignment).filter(Assignment.user_id == user_id).all()
    milestone_totals = {
        "done": sum(1 for milestone in milestones if milestone.status == "done"),
        "total": len(milestones),
    }

    first_day = today - dt.timedelta(days=FOCUS_DAYS - 1)
    since = dt.datetime.combine(first_day, dt.time.min, tzinfo=dt.timezone.utc)
    sessions = (
        db.session.query(FocusSession)
        .filter(
            FocusSession.user_id == user_id,
            FocusSession.ended_at.isnot(None),
            FocusSession.started_at >= since,
        )
        .all()
    )
    minutes = {first_day + dt.timedelta(days=offset): 0 for offset in range(FOCUS_DAYS)}
    for session in sessions:
        day = session.started_at.date()
        if day in minutes:
            minutes[day] += round((session.ended_at - session.started_at).total_seconds() / 60)

    return jsonify(
        counts=counts,
        deadlines=[
            {"week_start": (today + dt.timedelta(days=7 * week)).isoformat(), "count": weekly[week]}
            for week in range(DEADLINE_WEEKS)
        ],
        milestones=milestone_totals,
        focus=[{"date": day.isoformat(), "minutes": minutes[day]} for day in sorted(minutes)],
    )
