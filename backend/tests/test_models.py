from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Assignment,
    DailyGoal,
    FocusSession,
    LMSIntegration,
    Milestone,
    Reminder,
    ReminderPreference,
    StudyPlan,
    StudySession,
    User,
    WellnessCheckin,
)

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def build_user_graph(name="student1"):
    user = User(name=name, email=f"{name}@example.com", password_hash="hash")
    assignment = Assignment(user=user, course="HCI", title="Report", deadline=NOW, canvas_id="42")
    milestone = Milestone(assignment=assignment, title="Outline", target_date=NOW)
    plan = StudyPlan(user=user, start_date=date(2026, 11, 1), end_date=date(2026, 11, 7))
    session = StudySession(study_plan=plan, milestone=milestone, start_time=NOW, end_time=NOW)
    Reminder(user=user, assignment=assignment, milestone=milestone, kind="milestone",
              offset_days=1, fired_for_date=date(2026, 11, 1))
    ReminderPreference(user=user, offset_days=1)
    WellnessCheckin(user=user, checkin_date=date(2026, 11, 1), mood="calm", stress_level=2)
    LMSIntegration(user=user, provider="canvas")
    FocusSession(user=user, milestone=milestone, started_at=NOW)
    DailyGoal(user=user, goal_date=date(2026, 11, 1), items=[{"label": "Outline", "done": False}])
    db.session.add(user)
    db.session.commit()
    return user


def test_deleting_user_removes_all_related_rows(app):
    user = build_user_graph()

    db.session.delete(user)
    db.session.commit()

    for model in (
        Assignment, Milestone, StudyPlan, StudySession, Reminder, ReminderPreference,
        WellnessCheckin, LMSIntegration, FocusSession, DailyGoal,
    ):
        assert db.session.query(model).count() == 0


def test_deleting_milestone_removes_its_study_sessions(app):
    user = build_user_graph()
    milestone = db.session.query(Milestone).one()

    db.session.delete(milestone)
    db.session.commit()

    assert db.session.query(StudySession).count() == 0
    assert db.session.query(StudyPlan).count() == 1


def test_email_must_be_unique(app):
    build_user_graph("same")
    db.session.add(User(name="A", email="same@example.com", password_hash="hash"))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_one_wellness_checkin_per_user_per_day(app):
    build_user_graph()
    user = db.session.query(User).one()
    db.session.add(WellnessCheckin(user=user, checkin_date=date(2026, 11, 1), mood="low", stress_level=4))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_deleting_milestone_keeps_focus_history_but_clears_the_link(app):
    build_user_graph()
    milestone = db.session.query(Milestone).one()
    session_id = db.session.query(FocusSession).one().id

    db.session.delete(milestone)
    db.session.commit()

    # Deleting a milestone should not erase time the student already logged against it.
    kept = db.session.get(FocusSession, session_id)
    assert kept is not None
    assert kept.milestone_id is None


def test_one_daily_goal_per_user_per_day(app):
    build_user_graph()
    user = db.session.query(User).one()
    db.session.add(DailyGoal(user=user, goal_date=date(2026, 11, 1), items=[]))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_one_reminder_preference_per_user_per_offset(app):
    build_user_graph()
    user = db.session.query(User).one()
    db.session.add(ReminderPreference(user=user, offset_days=1))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_a_reminder_cannot_be_delivered_twice_for_the_same_day(app):
    user = build_user_graph()
    assignment = db.session.query(Assignment).one()
    milestone = db.session.query(Milestone).one()
    db.session.add(Reminder(
        user=user, assignment=assignment, milestone=milestone, kind="milestone",
        offset_days=1, fired_for_date=date(2026, 11, 1),
    ))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()