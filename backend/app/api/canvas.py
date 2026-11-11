from flask import Blueprint, current_app, g, jsonify
from sqlalchemy.exc import IntegrityError

from app.api.assignments import assignment_json
from app.api.auth import token_required
from app.api.common import clean_text, json_body, parse_deadline
from app.extensions import db
from app.models import Assignment
from app.services.canvas import CanvasClient, CanvasError

canvas_bp = Blueprint("canvas", __name__, url_prefix="/canvas")

MAX_TOKEN_LENGTH = 512
MAX_COURSES_PER_IMPORT = 50


@canvas_bp.errorhandler(CanvasError)
def handle_canvas_error(error):
    return jsonify(error=str(error)), error.status_code


def _client(token):
    base_url = current_app.config.get("CANVAS_BASE_URL")
    if not base_url:
        raise CanvasError("Canvas integration is not configured", 503)
    return CanvasClient(base_url, token)


def _token(data):
    return clean_text(data.get("token"), MAX_TOKEN_LENGTH)


@canvas_bp.post("/courses")
@token_required
def list_courses():
    data = json_body()
    token = _token(data)
    if token is None:
        return jsonify(error="token is required"), 400
    return jsonify(_client(token).list_courses())


@canvas_bp.post("/import")
@token_required
def import_assignments():
    data = json_body()
    token = _token(data)
    course_ids = data.get("course_ids")
    valid_ids = (
        isinstance(course_ids, list)
        and 0 < len(course_ids) <= MAX_COURSES_PER_IMPORT
        and all(isinstance(c, (int, str)) and not isinstance(c, bool) for c in course_ids)
    )
    if token is None or not valid_ids:
        return jsonify(error=f"token and 1 to {MAX_COURSES_PER_IMPORT} course_ids are required"), 400

    client = _client(token)
    course_names = {course["id"]: course["name"] for course in client.list_courses()}
    wanted = list(dict.fromkeys(str(c) for c in course_ids))
    unknown = [c for c in wanted if c not in course_names]
    if unknown:
        return jsonify(error=f"Not active Canvas courses for this account: {', '.join(unknown)}"), 400

    existing = {
        a.canvas_id: a
        for a in db.session.query(Assignment).filter(
            Assignment.user_id == g.current_user.id, Assignment.canvas_id.isnot(None)
        )
    }
    created, updated, skipped, imported = 0, 0, [], []
    for course_id in wanted:
        for item in client.list_assignments(course_id):
            is_valid, deadline = parse_deadline(item["deadline"])
            if not is_valid or deadline is None:
                skipped.append({"canvas_id": item["canvas_id"], "title": item["title"], "reason": "No due date"})
                continue

            assignment = existing.get(item["canvas_id"])
            if assignment is None:
                assignment = Assignment(user_id=g.current_user.id, canvas_id=item["canvas_id"])
                db.session.add(assignment)
                created += 1
            else:
                updated += 1
            assignment.course = course_names[course_id]
            assignment.title = item["title"]
            assignment.deadline = deadline
            assignment.rubric = item["rubric"]
            imported.append(assignment)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="The import conflicted with an existing assignment; try again"), 409

    return jsonify(
        created=created,
        updated=updated,
        skipped=skipped,
        assignments=[assignment_json(a) for a in imported],
    )
