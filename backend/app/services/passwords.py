import re

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
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a special character")
    return problems
