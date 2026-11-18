"""The "today" checklist. See app/services/goals.py for the pure logic this
file is a thin wrapper around, and app/models.py's DailyGoal for why it is
stored as a JSON snapshot rather than its own child table.

A goal is created the first time a student asks for today's, picked from
their nearest-due open milestones, and is then stable for the rest of the day
even if they edit their plan afterwards.
"""

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
    """The nearest-due open milestones across all the student's assignments,
    soonest first — what a fresh "today" goal is picked from."""
    milestones = (
        db.session.query(Milestone)
        .join(Assignment)
        .filter(Assignment.user_id == user_id, Milestone.status != "done")
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



from __future__ import annotations

Item = dict


def progress(items: list[Item]) -> tuple[int, int]:
    """Return (done_count, total_count) for a goal's items."""
    items = items or []
    done = sum(1 for item in items if item.get("done"))
    return done, len(items)


def is_complete(items: list[Item]) -> bool:
    """A goal with no items is not complete; there is nothing to have finished."""
    done, total = progress(items)
    return total > 0 and done == total


def mark_done(items: list[Item], index: int) -> list[Item]:
    """Return a new list with item[index] marked done. Does not mutate the input.

    Raises IndexError if index is out of range; the API layer translates that
    into a 404 rather than silently ignoring an edit against a stale list.
    """
    if not 0 <= index < len(items):
        raise IndexError("goal item index out of range")
    updated = [dict(item) for item in items]
    updated[index] = {**updated[index], "done": True}
    return updated


def default_items(candidates: list[Item], target_count: int = 3) -> list[Item]:
   
    chosen = candidates[:target_count]
    return [{**item, "done": False} for item in chosen]
