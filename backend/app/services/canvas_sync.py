import datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.api.common import parse_deadline
from app.extensions import db
from app.models import Assignment, User
from app.services.canvas import CanvasError
from app.services.reminders import fire_new_item_reminder

MAX_PARALLEL_COURSES = 6


def sync_courses(user, client, course_ids, notify_in_background=False):
    course_names = {course["id"]: course["name"] for course in client.list_courses()}
    # Dedupes course ids while keeping their original order.
    wanted = list(dict.fromkeys(str(c) for c in course_ids))
    unknown = [c for c in wanted if c not in course_names]
    # Reject the whole import if any requested course is not active for this account.
    if unknown:
        raise CanvasError(f"Not active Canvas courses for this account: {', '.join(unknown)}", 400)

    with ThreadPoolExecutor(max_workers=max(1, min(MAX_PARALLEL_COURSES, len(wanted)))) as pool:
        fetched = list(pool.map(client.list_assignments, wanted))

    existing = {
        a.canvas_id: a
        for a in db.session.query(Assignment).filter(Assignment.user_id == user.id, Assignment.canvas_id.isnot(None))
    }
    skipped, imported, newly_created, per_course = [], [], [], []
    for course_id, items in zip(wanted, fetched):
        stats = {"id": course_id, "name": course_names[course_id], "found": 0, "created": 0, "updated": 0, "skipped": 0, "pending": 0}
        per_course.append(stats)
        for item in items:
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
            # Canvas decides done state: submitted marks done, and a previously done item reopens if unsubmitted.
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

    if newly_created:
        if notify_in_background:
            _notify_new_items_in_background(user.id, [a.id for a in newly_created])
        else:
            for assignment in newly_created:
                fire_new_item_reminder(user, assignment)

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "courses": per_course,
        "assignments": imported,
    }


def _notify_new_items_in_background(user_id, assignment_ids):
    app = current_app._get_current_object()

    def send():
        with app.app_context():
            user = db.session.get(User, user_id)
            for assignment in db.session.query(Assignment).filter(Assignment.id.in_(assignment_ids)).all():
                fire_new_item_reminder(user, assignment)

    threading.Thread(target=send, daemon=True).start()
