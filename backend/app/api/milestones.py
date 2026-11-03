from flask import Blueprint, abort, g, jsonify

from app.api.assignments import owned_assignment_or_404
from app.api.auth import token_required
from app.api.common import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    STATUSES,
    clean_text,
    iso_utc,
    json_body,
    parse_deadline,
)
from app.extensions import db
from app.models import Milestone

milestones_bp = Blueprint("milestones", __name__)


def milestone_json(milestone):
    return {
        "id": milestone.id,
        "assignment_id": milestone.assignment_id,
        "title": milestone.title,
        "description": milestone.description,
        "target_date": iso_utc(milestone.target_date),
        "status": milestone.status,
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
    milestones = sorted(assignment.milestones, key=lambda m: (m.target_date, m.id))
    return jsonify([milestone_json(m) for m in milestones])


@milestones_bp.post("/assignments/<int:assignment_id>/milestones")
@token_required
def create_milestone(assignment_id):
    assignment = owned_assignment_or_404(assignment_id)
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

    milestone = Milestone(
        assignment_id=assignment.id,
        title=title,
        description=description,
        target_date=target_date,
        status=status,
    )
    db.session.add(milestone)
    db.session.commit()
    return jsonify(milestone_json(milestone)), 201


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

    db.session.commit()
    return jsonify(milestone_json(milestone))


@milestones_bp.delete("/milestones/<int:milestone_id>")
@token_required
def delete_milestone(milestone_id):
    db.session.delete(owned_milestone_or_404(milestone_id))
    db.session.commit()
    return "", 204
