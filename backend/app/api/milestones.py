import datetime as dt

from flask import Blueprint, abort, g, jsonify

from app.api.assignments import owned_assignment_or_404
from app.api.auth import token_required
from app.api.common import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    NOT_PENDING_MESSAGE,
    STATUSES,
    clean_text,
    is_pending,
    iso_utc,
    json_body,
    parse_deadline,
)
from app.extensions import db
from app.models import Milestone
from app.services.scheduling import weighted_targets

milestones_bp = Blueprint("milestones", __name__)

MAX_RUBRIC_CRITERIA = 30
MAX_MILESTONES = 30


def _weight(value):
    """Return (is_valid, weight). Null is valid and means "not weighted yet"."""
    if value is None:
        return True, None
    if isinstance(value, bool) or not isinstance(value, int):
        return False, None
    if not 0 <= value <= 100:
        return False, None
    return True, value


def _next_position(assignment):
    return max((m.position for m in assignment.milestones), default=-1) + 1


def _ordered(assignment):
    """Student order first, then target date, then id so the result is stable."""
    return sorted(assignment.milestones, key=lambda m: (m.position, m.target_date, m.id))


def _renumber(assignment):
    """Close gaps left by a delete so positions stay 0..n-1."""
    for index, milestone in enumerate(_ordered(assignment)):
        milestone.position = index


def milestone_json(milestone):
    return {
        "id": milestone.id,
        "assignment_id": milestone.assignment_id,
        "title": milestone.title,
        "description": milestone.description,
        "target_date": iso_utc(milestone.target_date),
        "status": milestone.status,
        "position": milestone.position,
        "weight": milestone.weight,
    }


def owned_milestone_or_404(milestone_id):
    milestone = db.session.get(Milestone, milestone_id)
    if milestone is None or milestone.assignment.user_id != g.current_user.id:
        abort(404)
    return milestone


def _description(value):
    """Return (is_valid, cleaned_value). A null description is valid and yields None."""
    if value is None:
        return True, None
    if not isinstance(value, str) or len(value) > MAX_DESCRIPTION_LENGTH:
        return False, None
    return True, value.strip() or None


def _past_deadline(assignment, target_date):
    return assignment.deadline is not None and target_date > assignment.deadline


@milestones_bp.get("/assignments/<int:assignment_id>/milestones")
@token_required
def list_milestones(assignment_id):
    assignment = owned_assignment_or_404(assignment_id)
    return jsonify([milestone_json(m) for m in _ordered(assignment)])


@milestones_bp.post("/assignments/<int:assignment_id>/milestones")
@token_required
def create_milestone(assignment_id):
    assignment = owned_assignment_or_404(assignment_id)
    if len(assignment.milestones) >= MAX_MILESTONES:
        return jsonify(error=f"An assignment can hold at most {MAX_MILESTONES} milestones"), 409
    data = json_body()

    title = clean_text(data.get("title"), MAX_TITLE_LENGTH)
    if title is None:
        return jsonify(error=f"title is required (at most {MAX_TITLE_LENGTH} characters)"), 400

    is_valid, target_date = parse_deadline(data.get("target_date"))
    if not is_valid or target_date is None:
        return jsonify(error="target_date is required as an ISO 8601 date-time with a timezone offset"), 400
    if _past_deadline(assignment, target_date):
        return jsonify(error="target_date cannot be after the assignment deadline"), 400

    is_valid, description = _description(data.get("description"))
    if not is_valid:
        return jsonify(error=f"description must be a string of at most {MAX_DESCRIPTION_LENGTH} characters"), 400

    status = data.get("status", "not_started")
    if status not in STATUSES:
        return jsonify(error=f"status must be one of {', '.join(STATUSES)}"), 400

    is_valid, weight = _weight(data.get("weight"))
    if not is_valid:
        return jsonify(error="weight must be a whole number from 0 to 100, or null"), 400

    milestone = Milestone(
        assignment_id=assignment.id,
        title=title,
        description=description,
        target_date=target_date,
        status=status,
        weight=weight,
        position=_next_position(assignment),
    )
    db.session.add(milestone)
    db.session.commit()
    return jsonify(milestone_json(milestone)), 201


@milestones_bp.post("/assignments/<int:assignment_id>/milestones/from-rubric")
@token_required
def create_milestones_from_rubric(assignment_id):
    assignment = owned_assignment_or_404(assignment_id)
    data = json_body()

    criteria = data.get("criteria")
    if not isinstance(criteria, list) or not 0 < len(criteria) <= MAX_RUBRIC_CRITERIA:
        return jsonify(error=f"criteria must be a list of 1 to {MAX_RUBRIC_CRITERIA} items"), 400
    cleaned = []
    for criterion in criteria:
        if not isinstance(criterion, dict):
            return jsonify(error="each criterion must be an object with a title"), 400
        title = clean_text(criterion.get("title"), MAX_TITLE_LENGTH)
        is_valid, description = _description(criterion.get("description"))
        if title is None or not is_valid:
            return jsonify(error="each criterion needs a title and a valid description"), 400
        is_valid, weight = _weight(criterion.get("weight"))
        if not is_valid:
            return jsonify(error="each criterion weight must be a whole number from 0 to 100, or null"), 400
        cleaned.append((title, description, weight))

    replace = data.get("replace", False)
    if not isinstance(replace, bool):
        return jsonify(error="replace must be true or false"), 400

    now = dt.datetime.now(dt.timezone.utc)
    if not is_pending(assignment, now):
        return jsonify(error=NOT_PENDING_MESSAGE), 400
    if assignment.milestones and not replace:
        return jsonify(error="Milestones already exist; send choose ' Replace existing milestones' to regenerate them"), 409

    for existing in list(assignment.milestones):
        db.session.delete(existing)
    # Keep the criteria the student generated from, so the rubric review shows them on a later visit.
    assignment.rubric = [
        {"title": title, "description": description, "weight": weight} for title, description, weight in cleaned
    ]
    # Weighted spacing gives a heavier criterion more working time
    targets = weighted_targets([weight for _, _, weight in cleaned], now, assignment.deadline)
    created = [
        Milestone(
            assignment_id=assignment.id,
            title=title,
            description=description,
            target_date=target,
            weight=weight,
            position=index,
        )
        for index, ((title, description, weight), target) in enumerate(zip(cleaned, targets))
    ]
    db.session.add_all(created)
    db.session.commit()
    return jsonify([milestone_json(m) for m in created]), 201


@milestones_bp.get("/milestones/<int:milestone_id>")
@token_required
def get_milestone(milestone_id):
    return jsonify(milestone_json(owned_milestone_or_404(milestone_id)))


@milestones_bp.patch("/milestones/<int:milestone_id>")
@token_required
def update_milestone(milestone_id):
    milestone = owned_milestone_or_404(milestone_id)
    data = json_body()

    if "title" in data:
        title = clean_text(data["title"], MAX_TITLE_LENGTH)
        if title is None:
            return jsonify(error=f"title must be non-empty and at most {MAX_TITLE_LENGTH} characters"), 400
        milestone.title = title

    if "description" in data:
        is_valid, description = _description(data["description"])
        if not is_valid:
            return jsonify(error=f"description must be a string of at most {MAX_DESCRIPTION_LENGTH} characters"), 400
        milestone.description = description

    if "target_date" in data:
        is_valid, target_date = parse_deadline(data["target_date"])
        if not is_valid or target_date is None:
            return jsonify(error="target_date must be an ISO 8601 date-time with a timezone offset"), 400
        if _past_deadline(milestone.assignment, target_date):
            return jsonify(error="target_date cannot be after the assignment deadline"), 400
        milestone.target_date = target_date

    if "status" in data:
        if data["status"] not in STATUSES:
            return jsonify(error=f"status must be one of {', '.join(STATUSES)}"), 400
        milestone.status = data["status"]
        # Starting work on a milestone also moves an unstarted assignment to in_progress.
        if milestone.status == "in_progress" and milestone.assignment.status == "not_started":
            milestone.assignment.status = "in_progress"

    if "weight" in data:
        is_valid, weight = _weight(data["weight"])
        if not is_valid:
            return jsonify(error="weight must be a whole number from 0 to 100, or null"), 400
        milestone.weight = weight

    db.session.commit()
    return jsonify(milestone_json(milestone))


@milestones_bp.delete("/milestones/<int:milestone_id>")
@token_required
def delete_milestone(milestone_id):
    milestone = owned_milestone_or_404(milestone_id)
    assignment = milestone.assignment
    db.session.delete(milestone)
    db.session.flush()
    _renumber(assignment)
    db.session.commit()
    return "", 204


@milestones_bp.put("/assignments/<int:assignment_id>/milestones/order")
@token_required
def reorder_milestones(assignment_id):
    """Set the reading order of a plan in one call.

    The body carries every milestone id for this assignment exactly once, in the
    order the student wants. Taking the whole list rather than a from/to pair
    keeps the operation idempotent and means a dropped request can simply be
    resent. Target dates are untouched: reordering changes how the plan reads,
    never when the work is due.
    """
    assignment = owned_assignment_or_404(assignment_id)
    data = json_body()

    ids = data.get("milestone_ids")
    if not isinstance(ids, list) or any(isinstance(i, bool) or not isinstance(i, int) for i in ids):
        return jsonify(error="milestone_ids must be a list of milestone ids"), 400

    existing = {m.id for m in assignment.milestones}
    if len(set(ids)) != len(ids):
        return jsonify(error="milestone_ids cannot repeat an id"), 400
    if set(ids) != existing:
        return jsonify(error="milestone_ids must list every milestone of this assignment exactly once"), 400

    by_id = {m.id: m for m in assignment.milestones}
    for index, milestone_id in enumerate(ids):
        by_id[milestone_id].position = index
    db.session.commit()
    return jsonify([milestone_json(m) for m in _ordered(assignment)])
