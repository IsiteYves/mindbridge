"""The "today" checklist."""

import datetime as dt

from flask import Blueprint, g, jsonify

from app.api.auth import token_required
from app.extensions import db
from app.models import Assignment, DailyGoal, Milestone
from app.services import goals as goal_rules

daily_goal_bp = Blueprint("daily_goal", __name__, url_prefix="/daily-goal")

DEFAULT_TARGET = 3


def _today():
    return dt.datetime.now(dt.timezone.utc).date()


def goal_json(goal):
    done, total = goal_rules.progress(goal.items)
    return {
        "id": goal.id,
        "goal_date": goal.goal_date.isoformat(),
        "target_count": goal.target_count,
        "items": goal.items,
        "done_count": done,
        "total_count": total,
    }


def _candidate_tasks(user_id, limit):
    """The nearest-due open milestones across all the student's assignments"""
    milestones = (
        db.session.query(Milestone)
        .join(Assignment)
        .filter(Assignment.user_id == user_id, Milestone.status != "done", Assignment.status != "done")
        .order_by(Milestone.target_date)
        .limit(limit)
        .all()
    )
    return [{"label": milestone.title, "kind": "milestone", "ref_id": milestone.id} for milestone in milestones]


def _existing_goal():
    return db.session.query(DailyGoal).filter_by(user_id=g.current_user.id, goal_date=_today()).one_or_none()


@daily_goal_bp.get("/today")
@token_required
def get_today():
    goal = _existing_goal()
    if goal is None:
        items = goal_rules.default_items(_candidate_tasks(g.current_user.id, DEFAULT_TARGET), target_count=DEFAULT_TARGET)
        goal = DailyGoal(user_id=g.current_user.id, goal_date=_today(), target_count=DEFAULT_TARGET, items=items)
        db.session.add(goal)
        db.session.commit()
    elif not goal.items:
        goal.items = goal_rules.default_items(_candidate_tasks(g.current_user.id, DEFAULT_TARGET), target_count=DEFAULT_TARGET)
        db.session.commit()
    return jsonify(goal_json(goal))


@daily_goal_bp.patch("/today/items/<int:item_index>")
@token_required
def mark_item_done(item_index):
    goal = _existing_goal()
    if goal is None:
        return jsonify(error="Today's goal has not been created yet. GET /daily-goal/today first."), 404
    try:
        goal.items = goal_rules.mark_done(goal.items, item_index)
    except IndexError:
        return jsonify(error="item_index is out of range for today's goal."), 400
    db.session.commit()
    return jsonify(goal_json(goal))
