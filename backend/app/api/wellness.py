import datetime as dt

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.api.auth import token_required
from app.api.common import json_body
from app.extensions import db
from app.models import WellnessCheckin

wellness_bp = Blueprint("wellness", __name__, url_prefix="/wellness")

MOODS = ("great", "good", "okay", "low", "stressed")
MIN_STRESS, MAX_STRESS = 1, 5
MAX_BACKDATE_DAYS = 7
DEFAULT_DAYS, MAX_DAYS = 7, 30


def checkin_json(checkin):
    return {
        "id": checkin.id,
        "checkin_date": checkin.checkin_date.isoformat(),
        "mood": checkin.mood,
        "stress_level": checkin.stress_level,
    }


def _today():
    return dt.datetime.now(dt.timezone.utc).date()


def _checkin_date(value):
    """Return (is_valid, date). A missing value means today."""
    if value is None:
        return True, _today()
    if not isinstance(value, str):
        return False, None
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        return False, None
    today = _today()
    if parsed > today or parsed < today - dt.timedelta(days=MAX_BACKDATE_DAYS):
        return False, None
    return True, parsed


def _stress_level(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if MIN_STRESS <= value <= MAX_STRESS else None


@wellness_bp.post("/checkins")
@token_required
def save_checkin():
    data = json_body()

    if data.get("mood") not in MOODS:
        return jsonify(error=f"mood must be one of {', '.join(MOODS)}"), 400
    stress_level = _stress_level(data.get("stress_level"))
    if stress_level is None:
        return jsonify(error=f"stress_level must be an integer from {MIN_STRESS} to {MAX_STRESS}"), 400
    is_valid, checkin_date = _checkin_date(data.get("checkin_date"))
    if not is_valid:
        return jsonify(error=f"checkin_date must be an ISO date from the last {MAX_BACKDATE_DAYS} days, not in the future"), 400

    # One check-in per day: saving again on the same day updates it.
    checkin = (
        db.session.query(WellnessCheckin)
        .filter_by(user_id=g.current_user.id, checkin_date=checkin_date)
        .first()
    )
    created = checkin is None
    if created:
        checkin = WellnessCheckin(user_id=g.current_user.id, checkin_date=checkin_date)
        db.session.add(checkin)
    checkin.mood = data["mood"]
    checkin.stress_level = stress_level

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="The check-in could not be saved. Try again."), 409
    return jsonify(checkin_json(checkin)), 201 if created else 200


@wellness_bp.get("/checkins")
@token_required
def list_checkins():
    try:
        days = int(request.args.get("days", DEFAULT_DAYS))
    except ValueError:
        days = 0
    if not 1 <= days <= MAX_DAYS:
        return jsonify(error=f"days must be an integer from 1 to {MAX_DAYS}"), 400

    earliest = _today() - dt.timedelta(days=days - 1)
    checkins = (
        db.session.query(WellnessCheckin)
        .filter(WellnessCheckin.user_id == g.current_user.id, WellnessCheckin.checkin_date >= earliest)
        .order_by(WellnessCheckin.checkin_date.desc())
        .all()
    )
    return jsonify([checkin_json(c) for c in checkins])
