import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from werkzeug.security import check_password_hash

MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128


def password_problems(password):
    """Return the rules the password breaks, as short phrases. An empty list means it is strong enough."""
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"[0-9]", password):
        problems.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a special character")
    return problems


_hasher = PasswordHasher()


def hash_password(password):
    return _hasher.hash(password)


# Legacy werkzeug hashes are still accepted so existing users can log in.
def verify_password(stored, password):
    if stored.startswith("$argon2"):
        try:
            return _hasher.verify(stored, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    return check_password_hash(stored, password)


# Any non-argon2 hash, or an argon2 hash with outdated parameters, should be rehashed.
def password_needs_rehash(stored):
    return not stored.startswith("$argon2") or _hasher.check_needs_rehash(stored)
