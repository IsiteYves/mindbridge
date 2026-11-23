import datetime as dt

from flask import request

STATUSES = ("not_started", "in_progress", "done")
MAX_TITLE_LENGTH = 255
MAX_CANVAS_ID_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 2000


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def clean_text(value, max_length):
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value and len(value) <= max_length else None


def parse_deadline(value):
    """Return (is_valid, datetime). A missing or null value is valid and yields None."""
    if value is None:
        return True, None
    if not isinstance(value, str):
        return False, None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return False, None
    if parsed.tzinfo is None:
        return False, None
    return True, parsed.astimezone(dt.timezone.utc)


def iso_utc(value):
    return value.astimezone(dt.timezone.utc).isoformat() if value else None


def is_pending(assignment, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    return assignment.status != "done" and assignment.deadline is not None and assignment.deadline > now


NOT_PENDING_MESSAGE = "This assignment is not pending: it is submitted, or its deadline has passed."
