from __future__ import annotations

class EmailNotValidError(ValueError):
    """Fallback error used when email-validator package is unavailable."""


def validate_email(email: str, *args, **kwargs):
    if not isinstance(email, str) or "@" not in email:
        raise EmailNotValidError("Invalid email format")
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise EmailNotValidError("Invalid email format")

    class _Result:
        def __init__(self, email: str) -> None:
            self.email = email
            self.ascii_email = email
            self.local_part = local
            self.domain = domain

    return _Result(email)
