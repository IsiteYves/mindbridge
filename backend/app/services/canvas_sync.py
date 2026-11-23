import datetime as dt

from sqlalchemy.exc import IntegrityError

from app.api.common import parse_deadline
from app.extensions import db
from app.models import Assignment
from app.services.canvas import CanvasError
from app.services.reminders import fire_new_item_reminder


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
    skipped, imported, newly_created, per_course = [], [], [], []
    for course_id in wanted:
        stats = {"id": course_id, "name": course_names[course_id], "found": 0, "created": 0, "updated": 0, "skipped": 0, "pending": 0}
        per_course.append(stats)
        for item in client.list_assignments(course_id):
            stats["found"] += 1
            is_valid, deadline = parse_deadline(item["deadline"])
            if not is_valid or deadline is None:
                stats["skipped"] += 1
                skipped.append({"canvas_id": item["canvas_id"], "title": item["title"], "reason": "No due date"})
                continue

            assignment = existing.get(item["canvas_id"])
            if assignment is None:
                assignment = Assignment(user_id=user.id, canvas_id=item["canvas_id"])
                db.session.add(assignment)
                existing[item["canvas_id"]] = assignment
                stats["created"] += 1
                newly_created.append(assignment)
            else:
                stats["updated"] += 1
            assignment.course = course_names[course_id]
            assignment.title = item["title"]
            assignment.deadline = deadline
            assignment.rubric = item["rubric"]
            submitted = bool(item.get("submitted"))
            if submitted:
                assignment.status = "done"
            elif assignment.status == "done":
                assignment.status = "not_started"
            if not submitted and deadline > dt.datetime.now(dt.timezone.utc):
                stats["pending"] += 1
            imported.append(assignment)

    created = sum(stats["created"] for stats in per_course)
    updated = sum(stats["updated"] for stats in per_course)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise CanvasError("The import conflicted with an existing assignment; try again", 409)

    for assignment in newly_created:
        fire_new_item_reminder(user, assignment)

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "courses": per_course,
        "assignments": imported,
    }