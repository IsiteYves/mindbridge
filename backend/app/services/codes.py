import datetime as dt
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import VerificationCode

CODE_TTL = dt.timedelta(minutes=10)
RESEND_COOLDOWN = dt.timedelta(seconds=60)
MAX_ATTEMPTS = 5


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _latest(user_id, purpose):
    return (
        db.session.query(VerificationCode)
        .filter_by(user_id=user_id, purpose=purpose)
        .order_by(VerificationCode.created_at.desc(), VerificationCode.id.desc())
        .first()
    )


def issue_code(user, purpose):
    """Create a new 6-digit code for the user and return it, or None if one was sent within the cooldown.

    The caller commits the session. Only a hash of the code is stored.
    """
    latest = _latest(user.id, purpose)
    if latest is not None and _now() - latest.created_at < RESEND_COOLDOWN:
        return None

    db.session.query(VerificationCode).filter_by(user_id=user.id, purpose=purpose).delete()
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.session.add(
        VerificationCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=generate_password_hash(code),
            expires_at=_now() + CODE_TTL,
            attempts=0,
        )
    )
    return code


def check_code(user, purpose, code):
    """Return True if the code is correct, expired-free and within the attempt limit. A correct code is used up.

    Commits the session itself, because failed attempts must be remembered.
    """
    record = _latest(user.id, purpose)
    if record is None:
        return False

    if record.expires_at <= _now() or record.attempts >= MAX_ATTEMPTS:
        db.session.delete(record)
        db.session.commit()
        return False

    if check_password_hash(record.code_hash, code):
        db.session.query(VerificationCode).filter_by(user_id=user.id, purpose=purpose).delete()
        db.session.commit()
        return True

    record.attempts += 1
    db.session.commit()
    return False
