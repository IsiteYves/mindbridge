from __future__ import annotations

import datetime as dt

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Assignment, Milestone, Reminder, ReminderPreference, User
from app.services.mailer import MailError, send_reminder_email

TRACKED_OFFSETS = (5, 2, 1, 0)


def offset_for(target: dt.date, today: dt.date) -> int | None:
   
    days = (target - today).days
    return days if days in TRACKED_OFFSETS else None


def is_overdue(target: dt.date, today: dt.date) -> bool:
    return target < today


def _subject_for(kind: str) -> str:
    return {
        "deadline": "Upcoming Deadline — MindBridge",
        "milestone": "Upcoming Milestone — MindBridge",
        "overdue": "Overdue: Still Open — MindBridge",
        "new_item": "New Item Added to Your Plan — MindBridge",
    }[kind]


def _body_for(kind: str, title: str, course: str, when: dt.date, offset_days: int | None) -> str:
    if kind == "overdue":
        return f'"{title}" ({course}) is still open and was due on {when:%d %b %Y}.'
    if kind == "new_item":
        return f'"{title}" ({course}) was just added to your plan, due {when:%d %b %Y}.'
    if offset_days == 0:
        return f'"{title}" ({course}) is due today, {when:%d %b %Y}.'
    plural = "s" if offset_days != 1 else ""
    return f'"{title}" ({course}) is due in {offset_days} day{plural}, on {when:%d %b %Y}.'


NO_OFFSET_SENTINEL = -1  # stored in place of NULL for overdue and new-item reminders


def _enabled_offsets(user_id: int) -> set[int]:
   
    rows = {p.offset_days: p.enabled for p in db.session.query(ReminderPreference).filter_by(user_id=user_id)}
    return {offset for offset in TRACKED_OFFSETS if rows.get(offset, True)}


def _claim_and_send(*, user, assignment, milestone, kind, offset_days, today, title, course, when) -> bool:
    
    reminder = Reminder(
        user_id=user.id,
        assignment_id=assignment.id,
        milestone_id=milestone.id if milestone else None,
        kind=kind,
        # NULL never collides in a unique index, so overdue/new-item rows would be
        # stored again on every run. Store a sentinel so the dedupe constraint holds.
        offset_days=NO_OFFSET_SENTINEL if offset_days is None else offset_days,
        fired_for_date=today,
        sent_at=None,
    )
    # Insert first so a duplicate run hits the unique constraint and skips the send.
    db.session.add(reminder)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False  

    # If sending fails, release the claim so a later run can retry.
    try:
        send_reminder_email(user.email, _subject_for(kind), _body_for(kind, title, course, when, offset_days))
    except MailError:
        db.session.delete(reminder)
        db.session.commit()
        return False

    reminder.sent_at = dt.datetime.now(dt.timezone.utc)
    db.session.commit()
    return True


def send_due_reminders(today: dt.date | None = None) -> dict:
    
    today = today or dt.datetime.now(dt.timezone.utc).date()
    sent = 0
    considered = 0

    for user in db.session.query(User).filter_by(email_verified=True):
        enabled = _enabled_offsets(user.id)

        for assignment in user.assignments:
            if assignment.status == "done" or assignment.deadline is None:
                continue
            deadline_date = assignment.deadline.date()
            considered += 1

            if is_overdue(deadline_date, today):
                if _claim_and_send(
                    user=user, assignment=assignment, milestone=None, kind="overdue", offset_days=None,
                    today=today, title=assignment.title, course=assignment.course, when=deadline_date,
                ):
                    sent += 1
                continue

            offset = offset_for(deadline_date, today)
            if offset is not None and offset in enabled:
                if _claim_and_send(
                    user=user, assignment=assignment, milestone=None, kind="deadline", offset_days=offset,
                    today=today, title=assignment.title, course=assignment.course, when=deadline_date,
                ):
                    sent += 1

            for milestone in assignment.milestones:
                if milestone.status == "done":
                    continue
                target_date = milestone.target_date.date()
                considered += 1

                if is_overdue(target_date, today):
                    if _claim_and_send(
                        user=user, assignment=assignment, milestone=milestone, kind="overdue", offset_days=None,
                        today=today, title=milestone.title, course=assignment.course, when=target_date,
                    ):
                        sent += 1
                    continue

                m_offset = offset_for(target_date, today)
                if m_offset is not None and m_offset in enabled:
                    if _claim_and_send(
                        user=user, assignment=assignment, milestone=milestone, kind="milestone", offset_days=m_offset,
                        today=today, title=milestone.title, course=assignment.course, when=target_date,
                    ):
                        sent += 1

    return {"considered": considered, "sent": sent}


def fire_new_item_reminder(user: User, assignment: Assignment, milestone: Milestone | None = None) -> None:
    
    today = dt.datetime.now(dt.timezone.utc).date()
    target = milestone.target_date if milestone else assignment.deadline
    if target is None:
        return
    # A reminder failure must never break the caller's save, so errors are rolled back and ignored.
    try:
        _claim_and_send(
            user=user, assignment=assignment, milestone=milestone, kind="new_item", offset_days=None,
            today=today, title=(milestone.title if milestone else assignment.title),
            course=assignment.course, when=target.date(),
        )
    except Exception:  
        db.session.rollback()