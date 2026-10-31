from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Assignment, LMSIntegration, Milestone, Reminder, StudyPlan, StudySession, User, WellnessCheckin

NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def build_user_graph(username="student1"):
    user = User(username=username, password_hash="hash")
    assignment = Assignment(user=user, course="HCI", title="Report", deadline=NOW, canvas_id="42")
    milestone = Milestone(assignment=assignment, title="Outline", target_date=NOW)
    plan = StudyPlan(user=user, start_date=date(2026, 11, 1), end_date=date(2026, 11, 7))
    session = StudySession(study_plan=plan, milestone=milestone, start_time=NOW, end_time=NOW)
    Reminder(user=user, study_session=session, remind_at=NOW)
    WellnessCheckin(user=user, checkin_date=date(2026, 11, 1), mood="calm", stress_level=2)
    LMSIntegration(user=user, provider="canvas")
    db.session.add(user)
    db.session.commit()
    return user


def test_deleting_user_removes_all_related_rows(app):
    user = build_user_graph()

    db.session.delete(user)
    db.session.commit()

    for model in (Assignment, Milestone, StudyPlan, StudySession, Reminder, WellnessCheckin, LMSIntegration):
        assert db.session.query(model).count() == 0


def test_deleting_milestone_removes_its_study_sessions(app):
    user = build_user_graph()
    milestone = db.session.query(Milestone).one()

    db.session.delete(milestone)
    db.session.commit()

    assert db.session.query(StudySession).count() == 0
    assert db.session.query(StudyPlan).count() == 1


def test_username_must_be_unique(app):
    build_user_graph("same")
    db.session.add(User(username="same", password_hash="hash"))

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
