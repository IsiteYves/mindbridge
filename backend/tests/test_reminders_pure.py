import datetime as dt

from app.services import reminders

TODAY = dt.date(2026, 11, 10)


def test_each_tracked_offset_is_detected_exactly():
    for days in (5, 2, 1, 0):
        assert reminders.offset_for(TODAY + dt.timedelta(days=days), TODAY) == days


def test_an_untracked_number_of_days_out_is_not_an_offset():
    for days in (3, 4, 6, 10, 30):
        assert reminders.offset_for(TODAY + dt.timedelta(days=days), TODAY) is None


def test_a_past_date_is_never_reported_as_an_offset():
    assert reminders.offset_for(TODAY - dt.timedelta(days=1), TODAY) is None
    assert reminders.offset_for(TODAY - dt.timedelta(days=5), TODAY) is None


def test_is_overdue_boundary():
    assert reminders.is_overdue(TODAY - dt.timedelta(days=1), TODAY) is True
    assert reminders.is_overdue(TODAY, TODAY) is False
    assert reminders.is_overdue(TODAY + dt.timedelta(days=1), TODAY) is False


def test_offset_zero_reads_as_due_today():
    assert "due today" in reminders._body_for("deadline", "Report", "CS101", TODAY, 0)


def test_offset_one_is_grammatically_singular():
    body = reminders._body_for("milestone", "Draft", "CS101", TODAY, 1)
    assert "in 1 day," in body
    assert "days" not in body


def test_offset_five_is_plural():
    assert "in 5 days" in reminders._body_for("deadline", "Report", "CS101", TODAY, 5)


def test_overdue_message_does_not_mention_an_offset():
    body = reminders._body_for("overdue", "Report", "CS101", TODAY, None)
    assert "still open" in body
    assert "in None day" not in body


def test_new_item_message_is_distinct_from_the_others():
    body = reminders._body_for("new_item", "Report", "CS101", TODAY, None)
    assert "just added" in body


def test_every_kind_has_its_own_subject():
    subjects = {reminders._subject_for(kind) for kind in ("deadline", "milestone", "overdue", "new_item")}
    assert len(subjects) == 4