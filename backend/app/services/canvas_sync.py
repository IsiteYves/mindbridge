"""Shared by POST /canvas/import (one-shot, token pasted every time),
/connect (first run of a persistent connection), /sync (the student's own
"sync now"), and the periodic `flask canvas sync-all` CLI command that
re-syncs every connected account.

Returns ORM Assignment objects under "assignments", not serialized dicts —
callers that need JSON (the routes) serialize with assignment_json
themselves; the CLI command just counts, with nothing to serialize for.
"""

from sqlalchemy.exc import IntegrityError

from app.api.common import parse_deadline
from app.extensions import db
from app.models import Assignment
from app.services.canvas import CanvasError


def sync_courses(user, client, course_ids):
    course_names = {course["id"]: course["name"] for course in client.list_courses()}
    wanted = list(dict.fromkeys(str(c) for c in course_ids))
    unknown = [c for c in wanted if c not in course_names]
    if unknown:
        raise CanvasError(f"Not active Canvas courses for this account: {', '.join(unknown)}", 400)

    existing = {
        a.canvas_id: a
        for a in db.session.query(Assignment).filter(Assignment.user_id == user.id, Assignment.canvas_id.isnot(None))
    }
    created, updated, skipped, imported, newly_created = 0, 0, [], [], []
    for course_id in wanted:
        for item in client.list_assignments(course_id):
            is_valid, deadline = parse_deadline(item["deadline"])
            if not is_valid or deadline is None:
                skipped.append({"canvas_id": item["canvas_id"], "title": item["title"], "reason": "No due date"})
                continue

            assignment = existing.get(item["canvas_id"])
            if assignment is None:
                assignment = Assignment(user_id=user.id, canvas_id=item["canvas_id"])
                db.session.add(assignment)
                created += 1
                newly_created.append(assignment)
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
        raise CanvasError("The import conflicted with an existing assignment; try again", 409)


    return {"created": created, "updated": updated, "skipped": skipped, "assignments": imported}
