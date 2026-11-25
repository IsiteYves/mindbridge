import datetime as dt

from flask import Blueprint, abort, g, jsonify, request
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError

from app.api.auth import token_required
from app.api.common import (
    MAX_CANVAS_ID_LENGTH,
    MAX_TITLE_LENGTH,
    STATUSES,
    clean_text,
    iso_utc,
    json_body,
    parse_deadline,
)
from app.extensions import db
from app.models import Assignment

assignments_bp = Blueprint("assignments", __name__, url_prefix="/assignments")


LIST_DEFAULT_LIMIT = 15
LIST_MAX_LIMIT = 100
LIST_STATES = ("all", "pending", "closed")
LIST_SORTS = ("deadline_asc", "deadline_desc")
MAX_QUERY_LENGTH = 255


def _list_int(name, default, minimum, maximum):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        return None
    return value if minimum <= value <= maximum else None


# Returns (value, is_valid); a missing param is valid and yields None.
def _list_date(name):
    raw = request.args.get(name)
    if not raw:
        return None, True
    try:
        return dt.date.fromisoformat(raw), True
    except ValueError:
        return None, False


def assignment_json(assignment):
    return {
        "id": assignment.id,
        "canvas_id": assignment.canvas_id,
        "course": assignment.course,
        "title": assignment.title,
        "status": assignment.status,
        "deadline": iso_utc(assignment.deadline),
        "rubric": assignment.rubric or [],
    }


def owned_assignment_or_404(assignment_id):
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None or assignment.user_id != g.current_user.id:
        abort(404)
    return assignment


@assignments_bp.get("")
@token_required
def list_assignments():
    limit = _list_int("limit", LIST_DEFAULT_LIMIT, 1, LIST_MAX_LIMIT)
    offset = _list_int("offset", 0, 0, 10**9)
    state = request.args.get("state", "all")
    sort = request.args.get("sort", "deadline_asc")
    query_text = (request.args.get("q") or "").strip()[:MAX_QUERY_LENGTH]
    status = request.args.get("status")
    start, start_ok = _list_date("from")
    end, end_ok = _list_date("to")
    if limit is None or offset is None:
        return jsonify(error=f"limit must be 1 to {LIST_MAX_LIMIT} and offset must be 0 or more"), 400
    if state not in LIST_STATES or sort not in LIST_SORTS or not start_ok or not end_ok:
        return jsonify(error="state, sort, from or to is not valid"), 400
    if status is not None and status not in STATUSES:
        return jsonify(error=f"status must be one of {', '.join(STATUSES)}"), 400

    now = dt.datetime.now(dt.timezone.utc)
    query = db.session.query(Assignment).filter(Assignment.user_id == g.current_user.id)
    if state == "pending":
        query = query.filter(and_(Assignment.status != "done", Assignment.deadline > now))
    elif state == "closed":
        query = query.filter(or_(Assignment.status == "done", Assignment.deadline.is_(None), Assignment.deadline <= now))
    if status is not None:
        query = query.filter(Assignment.status == status)
    if query_text:
        query = query.filter(
            or_(
                Assignment.title.icontains(query_text, autoescape=True),
                Assignment.course.icontains(query_text, autoescape=True),
            )
        )
    if start is not None:
        query = query.filter(Assignment.deadline >= dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc))
    if end is not None:
        query = query.filter(Assignment.deadline < dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc))

    total = query.count()
    order = Assignment.deadline.desc() if sort == "deadline_desc" else Assignment.deadline.asc()
    # Assignments without a deadline sort last in either direction.
    items = query.order_by(Assignment.deadline.is_(None), order, Assignment.id).offset(offset).limit(limit).all()
    return jsonify(items=[assignment_json(a) for a in items], total=total, limit=limit, offset=offset)


@assignments_bp.post("")
@token_required
def create_assignment():
    data = json_body()
    course = clean_text(data.get("course"), MAX_TITLE_LENGTH)
    title = clean_text(data.get("title"), MAX_TITLE_LENGTH)
    if course is None or title is None:
        return jsonify(error=f"course and title are required (at most {MAX_TITLE_LENGTH} characters)"), 400

    canvas_id = data.get("canvas_id")
    if canvas_id is not None:
        canvas_id = clean_text(canvas_id, MAX_CANVAS_ID_LENGTH)
        if canvas_id is None:
            return jsonify(error=f"canvas_id must be a non-empty string of at most {MAX_CANVAS_ID_LENGTH} characters"), 400

    status = data.get("status", "not_started")
    if status not in STATUSES:
        return jsonify(error=f"status must be one of {', '.join(STATUSES)}"), 400

    is_valid, deadline = parse_deadline(data.get("deadline"))
    if not is_valid or deadline is None:
        return jsonify(error="deadline is required and must be an ISO 8601 date-time with a timezone offset"), 400

    assignment = Assignment(
        user_id=g.current_user.id,
        canvas_id=canvas_id,
        course=course,
        title=title,
        status=status,
        deadline=deadline,
    )
    db.session.add(assignment)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="An assignment with this canvas_id already exists"), 409

    return jsonify(assignment_json(assignment)), 201


@assignments_bp.get("/<int:assignment_id>")
@token_required
def get_assignment(assignment_id):
    return jsonify(assignment_json(owned_assignment_or_404(assignment_id)))


@assignments_bp.patch("/<int:assignment_id>")
@token_required
def update_assignment(assignment_id):
    assignment = owned_assignment_or_404(assignment_id)
    data = json_body()

    if "course" in data:
        course = clean_text(data["course"], MAX_TITLE_LENGTH)
        if course is None:
            return jsonify(error=f"course must be non-empty and at most {MAX_TITLE_LENGTH} characters"), 400
        assignment.course = course

    if "title" in data:
        title = clean_text(data["title"], MAX_TITLE_LENGTH)
        if title is None:
            return jsonify(error=f"title must be non-empty and at most {MAX_TITLE_LENGTH} characters"), 400
        assignment.title = title

    if "status" in data:
        if data["status"] not in STATUSES:
            return jsonify(error=f"status must be one of {', '.join(STATUSES)}"), 400
        assignment.status = data["status"]

    if "deadline" in data:
        is_valid, deadline = parse_deadline(data["deadline"])
        if not is_valid or deadline is None:
            return jsonify(error="deadline is required and must be an ISO 8601 date-time with a timezone offset"), 400
        if any(m.target_date > deadline for m in assignment.milestones):
            return jsonify(error="deadline cannot be earlier than an existing milestone"), 400
        assignment.deadline = deadline

    db.session.commit()
    return jsonify(assignment_json(assignment))


@assignments_bp.delete("/<int:assignment_id>")
@token_required
def delete_assignment(assignment_id):
    db.session.delete(owned_assignment_or_404(assignment_id))
    db.session.commit()
    return "", 204
