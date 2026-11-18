from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

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
    # Rubric criteria as a list of {"title", "description"?, "points"?} objects. Filled by the Canvas
    # import and replaced whenever the student generates milestones from edited criteria.
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

    user = db.relationship("User", back_populates="lms_integrations")


class SupportMessage(TimestampMixin, db.Model):
    __tablename__ = "support_messages"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(120), nullable=False)
    email = db.Column(String(255), nullable=False)
    message = db.Column(String(2000), nullable=False)
    status = db.Column(String(20), nullable=False, default="new", server_default="new")


 


class FocusSession(TimestampMixin, db.Model):
    """One focus-timer run (Pomodoro-style). Optionally tied to the milestone the
    student was working on, so time-on-task can later be shown per milestone.

    `milestone_id` uses ON DELETE SET NULL rather than CASCADE, unlike most
    foreign keys in this file: a student deleting a milestone from their plan
    should not erase the focus history they already logged against it.
    """

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
    """A student's 'today' checklist: at most a few small, concrete steps, picked
    once and then stable for the day even if the student edits their plan later.

    `items` is a JSON list of {"label", "kind", "ref_id", "done"} objects rather
    than its own table: a goal is read and rewritten as a whole, never joined or
    queried by field, so a child table would add a relationship with no real use.
    See app/services/goals.py for the pure helpers that read and update it.
    """

    __tablename__ = "daily_goals"
    __table_args__ = (UniqueConstraint("user_id", "goal_date", name="uq_daily_goal_user_date"),)

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_date = db.Column(Date, nullable=False)
    target_count = db.Column(Integer, nullable=False, default=3, server_default="3")
    items = db.Column(JSON, nullable=False, default=list)

    user = db.relationship("User", back_populates="daily_goals")
