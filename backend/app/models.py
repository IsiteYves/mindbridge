from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(120), nullable=False)
    email = db.Column(String(255), unique=True, nullable=False)
    email_verified = db.Column(Boolean, nullable=False, default=False, server_default="false")
    password_hash = db.Column(String(255), nullable=False)
    failed_login_attempts = db.Column(Integer, nullable=False, default=0, server_default="0")
    locked_until = db.Column(DateTime(timezone=True), nullable=True)

    assignments = db.relationship("Assignment", back_populates="user", cascade="all, delete-orphan")
    study_plans = db.relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    reminders = db.relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    reminder_preferences = db.relationship("ReminderPreference", back_populates="user", cascade="all, delete-orphan")
    wellness_checkins = db.relationship("WellnessCheckin", back_populates="user", cascade="all, delete-orphan")
    lms_integrations = db.relationship("LMSIntegration", back_populates="user", cascade="all, delete-orphan")
    focus_sessions = db.relationship("FocusSession", back_populates="user", cascade="all, delete-orphan")
    daily_goals = db.relationship("DailyGoal", back_populates="user", cascade="all, delete-orphan")


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
    rubric = db.Column(JSON, nullable=True)

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
    position = db.Column(Integer, nullable=False, default=0, server_default="0")
    weight = db.Column(Integer, nullable=True)

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


class Reminder(TimestampMixin, db.Model):
    """One reminder delivery. A row is written when a reminder actually fires, not
    when it becomes possible to fire, so this table is a record of what was sent,
    not a schedule of what will be.
    """

    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "assignment_id", "milestone_id", "kind", "offset_days", "fired_for_date",
            name="uq_reminder_delivery",
        ),
        # The constraint above does not protect an assignment-level reminder
        Index(
            "uq_reminder_delivery_no_milestone",
            "user_id", "assignment_id", "kind", "offset_days", "fired_for_date",
            unique=True,
            postgresql_where=db.text("milestone_id IS NULL"),
        ),
    )

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = db.Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    # Null for a reminder about the assignment deadline itself rather than one milestone.
    milestone_id = db.Column(Integer, ForeignKey("milestones.id", ondelete="CASCADE"), nullable=True, index=True)
    # "milestone" | "deadline" | "new_item" | "overdue"
    kind = db.Column(String(20), nullable=False)
    # Days before the target: 5, 2, 1 or 0. Null for "new_item" and "overdue", which are
    # not expressed as an offset from a date.
    offset_days = db.Column(Integer, nullable=True)
    fired_for_date = db.Column(Date, nullable=False)
    sent_at = db.Column(DateTime(timezone=True), nullable=True)
    dismissed_at = db.Column(DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="reminders")
    assignment = db.relationship("Assignment")
    milestone = db.relationship("Milestone")


class ReminderPreference(TimestampMixin, db.Model):
    """Which day-before offsets a student wants reminders for."""

    __tablename__ = "reminder_preferences"
    __table_args__ = (UniqueConstraint("user_id", "offset_days", name="uq_reminder_pref_user_offset"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    offset_days = db.Column(Integer, nullable=False)
    enabled = db.Column(Boolean, nullable=False, default=True, server_default="true")

    user = db.relationship("User", back_populates="reminder_preferences")


class WellnessCheckin(TimestampMixin, db.Model):
    __tablename__ = "wellness_checkins"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uq_wellness_user_date"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    checkin_date = db.Column(Date, nullable=False)
    mood = db.Column(String(20), nullable=False)
    stress_level = db.Column(Integer, nullable=False)

    user = db.relationship("User", back_populates="wellness_checkins")


class VerificationCode(TimestampMixin, db.Model):
    __tablename__ = "verification_codes"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = db.Column(String(20), nullable=False)
    code_hash = db.Column(String(255), nullable=False)
    expires_at = db.Column(DateTime(timezone=True), nullable=False)
    attempts = db.Column(Integer, nullable=False, default=0)


class LMSIntegration(TimestampMixin, db.Model):
    __tablename__ = "lms_integrations"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_lms_user_provider"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = db.Column(String(50), nullable=False)
    status = db.Column(String(20), nullable=False, default="connected")
    last_synced_at = db.Column(DateTime(timezone=True))
    access_token_encrypted = db.Column(String(1024), nullable=True)
    # The Canvas course ids chosen the last time this was connected, so a
    # later sync can re-pull the same courses without asking again.
    selected_course_ids = db.Column(JSON, nullable=True)

    user = db.relationship("User", back_populates="lms_integrations")


class FocusSession(TimestampMixin, db.Model):
    """One focus-timer run (Pomodoro-style)."""

    __tablename__ = "focus_sessions"

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_id = db.Column(Integer, ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    planned_minutes = db.Column(Integer, nullable=False, default=25, server_default="25")
    started_at = db.Column(DateTime(timezone=True), nullable=False)
    ended_at = db.Column(DateTime(timezone=True), nullable=True)
    completed = db.Column(Boolean, nullable=False, default=False, server_default="false")

    user = db.relationship("User", back_populates="focus_sessions")
    milestone = db.relationship("Milestone")


class DailyGoal(TimestampMixin, db.Model):
    """A student's 'today's checklist"""

    __tablename__ = "daily_goals"
    __table_args__ = (UniqueConstraint("user_id", "goal_date", name="uq_daily_goal_user_date"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_date = db.Column(Date, nullable=False)
    target_count = db.Column(Integer, nullable=False, default=3, server_default="3")
    items = db.Column(JSON, nullable=False, default=list)

    user = db.relationship("User", back_populates="daily_goals")
