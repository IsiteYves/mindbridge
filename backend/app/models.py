from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(64), unique=True, nullable=False)
    password_hash = db.Column(String(255), nullable=False)

    assignments = db.relationship("Assignment", back_populates="user", cascade="all, delete-orphan")
    study_plans = db.relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    reminders = db.relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    wellness_checkins = db.relationship("WellnessCheckin", back_populates="user", cascade="all, delete-orphan")
    lms_integrations = db.relationship("LMSIntegration", back_populates="user", cascade="all, delete-orphan")


class Assignment(TimestampMixin, db.Model):
    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("user_id", "canvas_id", name="uq_assignments_user_canvas"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    canvas_id = db.Column(String(64))
    course = db.Column(String(255), nullable=False)
    title = db.Column(String(255), nullable=False)
    status = db.Column(String(20), nullable=False, default="not_started")
    deadline = db.Column(DateTime(timezone=True))

    user = db.relationship("User", back_populates="assignments")
    milestones = db.relationship("Milestone", back_populates="assignment", cascade="all, delete-orphan")


class Milestone(TimestampMixin, db.Model):
    __tablename__ = "milestones"

    id = db.Column(Integer, primary_key=True)
    assignment_id = db.Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(String(255), nullable=False)
    description = db.Column(String(2000))
    target_date = db.Column(DateTime(timezone=True), nullable=False)
    status = db.Column(String(20), nullable=False, default="not_started")

    assignment = db.relationship("Assignment", back_populates="milestones")
    study_sessions = db.relationship("StudySession", back_populates="milestone", cascade="all, delete-orphan")


class StudyPlan(TimestampMixin, db.Model):
    __tablename__ = "study_plans"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date = db.Column(Date, nullable=False)
    end_date = db.Column(Date, nullable=False)
    status = db.Column(String(20), nullable=False, default="active")

    user = db.relationship("User", back_populates="study_plans")
    study_sessions = db.relationship("StudySession", back_populates="study_plan", cascade="all, delete-orphan")


class StudySession(TimestampMixin, db.Model):
    __tablename__ = "study_sessions"

    id = db.Column(Integer, primary_key=True)
    study_plan_id = db.Column(Integer, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id = db.Column(Integer, ForeignKey("milestones.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = db.Column(DateTime(timezone=True), nullable=False)
    end_time = db.Column(DateTime(timezone=True), nullable=False)
    status = db.Column(String(20), nullable=False, default="planned")

    study_plan = db.relationship("StudyPlan", back_populates="study_sessions")
    milestone = db.relationship("Milestone", back_populates="study_sessions")
    reminders = db.relationship("Reminder", back_populates="study_session", cascade="all, delete-orphan")


class Reminder(TimestampMixin, db.Model):
    __tablename__ = "reminders"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    study_session_id = db.Column(Integer, ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    remind_at = db.Column(DateTime(timezone=True), nullable=False)
    status = db.Column(String(20), nullable=False, default="pending")

    user = db.relationship("User", back_populates="reminders")
    study_session = db.relationship("StudySession", back_populates="reminders")


class WellnessCheckin(TimestampMixin, db.Model):
    __tablename__ = "wellness_checkins"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uq_wellness_user_date"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    checkin_date = db.Column(Date, nullable=False)
    mood = db.Column(String(20), nullable=False)
    stress_level = db.Column(Integer, nullable=False)

    user = db.relationship("User", back_populates="wellness_checkins")


class LMSIntegration(TimestampMixin, db.Model):
    __tablename__ = "lms_integrations"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_lms_user_provider"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = db.Column(String(50), nullable=False)
    status = db.Column(String(20), nullable=False, default="connected")
    last_synced_at = db.Column(DateTime(timezone=True))

    user = db.relationship("User", back_populates="lms_integrations")
