"""Reminder preferences, and the inbox of reminders actually delivered.

Nothing writes a Reminder row yet. That is the worker's job
"""

import datetime as dt

from flask import Blueprint, abort, g, jsonify

from app.api.auth import token_required
from app.api.common import json_body
from app.extensions import db
from app.models import Reminder, ReminderPreference

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")

# The only offsets a student can toggle. Overdue and new-item reminders are not
# covered here and are not optional — see ReminderPreference's docstring.
ALLOWED_OFFSETS = (5, 2, 1, 0)


def preference_json(preference):
    return {"offset_days": preference.offset_days, "enabled": preference.enabled}


def reminder_json(reminder):
    return {
        "id": reminder.id,
        "assignment_id": reminder.assignment_id,
        "milestone_id": reminder.milestone_id,
        "kind": reminder.kind,
        "offset_days": reminder.offset_days,
        "fired_for_date": reminder.fired_for_date.isoformat(),
        "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
    }


@notifications_bp.get("/preferences")
@token_required
def list_preferences():
    existing = {
        preference.offset_days: preference
        for preference in db.session.query(ReminderPreference).filter_by(user_id=g.current_user.id)
    }
    # One row per allowed offset, every time. An account created before this
    # feature shipped has no ReminderPreference rows at all; defaulting a
    # missing offset to enabled=True means it still sees a complete, correct
    # list rather than a gap the UI would have to explain.
    return jsonify(
        [
            preference_json(existing[offset]) if offset in existing else {"offset_days": offset, "enabled": True}
            for offset in ALLOWED_OFFSETS
        ]
    )


@notifications_bp.patch("/preferences")
@token_required
def update_preference():
    data = json_body()
    offset_days = data.get("offset_days")
    enabled = data.get("enabled")

    if offset_days not in ALLOWED_OFFSETS:
        return jsonify(error=f"offset_days must be one of {', '.join(map(str, ALLOWED_OFFSETS))}"), 400
    if not isinstance(enabled, bool):
        return jsonify(error="enabled must be true or false"), 400

    preference = (
        db.session.query(ReminderPreference)
        .filter_by(user_id=g.current_user.id, offset_days=offset_days)
        .one_or_none()
    )
    if preference is None:
        preference = ReminderPreference(user_id=g.current_user.id, offset_days=offset_days, enabled=enabled)
        db.session.add(preference)
    else:
        preference.enabled = enabled
    db.session.commit()
    return jsonify(preference_json(preference))


@notifications_bp.put("/preferences")
@token_required
def replace_preferences():
    items = json_body().get("preferences")
    if not isinstance(items, list) or not items:
        return jsonify(error="preferences must be a non-empty list"), 400
    wanted = {}
    for item in items:
        if not isinstance(item, dict) or item.get("offset_days") not in ALLOWED_OFFSETS:
            return jsonify(error=f"offset_days must be one of {', '.join(map(str, ALLOWED_OFFSETS))}"), 400
        if not isinstance(item.get("enabled"), bool):
            return jsonify(error="enabled must be true or false"), 400
        wanted[item["offset_days"]] = item["enabled"]

    existing = {
        preference.offset_days: preference
        for preference in db.session.query(ReminderPreference).filter_by(user_id=g.current_user.id)
    }
    for offset_days, enabled in wanted.items():
        if offset_days in existing:
            existing[offset_days].enabled = enabled
        else:
            db.session.add(ReminderPreference(user_id=g.current_user.id, offset_days=offset_days, enabled=enabled))
    db.session.commit()
    return list_preferences()


@notifications_bp.get("")
@token_required
def list_notifications():
    # Delivered and not yet dismissed: an inbox of what the student has
    # actually been told, not a preview of what will fire later.
    reminders = (
        db.session.query(Reminder)
        .filter(
            Reminder.user_id == g.current_user.id,
            Reminder.sent_at.isnot(None),
            Reminder.dismissed_at.is_(None),
        )
        .order_by(Reminder.sent_at.desc())
        .all()
    )
    return jsonify([reminder_json(reminder) for reminder in reminders])


def owned_reminder_or_404(reminder_id):
    reminder = db.session.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != g.current_user.id:
        abort(404)
    return reminder


@notifications_bp.post("/<int:reminder_id>/dismiss")
@token_required
def dismiss(reminder_id):
    reminder = owned_reminder_or_404(reminder_id)
    if reminder.sent_at is None:
        # Nothing reachable through list_notifications() has a null sent_at, so
        # this only guards a guessed or stale id, not a real user flow.
        abort(409, description="This reminder has not been delivered yet.")
    reminder.dismissed_at = dt.datetime.now(dt.timezone.utc)
    db.session.commit()
    return jsonify(reminder_json(reminder))
