from typing import cast, Callable
import backend.app.core.security as security
import backend.app.db.session as db_session
from sqlalchemy.orm import Session
from backend.app.models import User


# typed helper for session factory resolution
def _get_session_factory() -> "Callable[[], Session]":
    fac = getattr(db_session, "SessionLocal", None)
    if fac is None:
        raise AttributeError("SessionLocal not found in backend.app.db.session")
    return fac  # type: ignore[return-value]

# runtime shim to support either naming in security module
def hash_password(pw: str) -> str:
    fn = getattr(security, "get_password_hash", None) or getattr(security, "hash_password", None)
    if fn is None:
        raise AttributeError("No password hash function found in backend.app.core.security")
    return fn(pw)  # type: ignore[misc]

SEED = {
    "biuro@work-host.com": "ChangeMe123!",
    "valentyna.l@work-host.com": "ChangeMe123!",
    "roman.k@work-host.com": "ChangeMe123!",
    "olha.p@work-host.com": "ChangeMe123!",
    "anastasiya.d@work-host.com": "ChangeMe123!",
    "iryna.y@work-host.com": "ChangeMe123!",
    "victoria.t@work-host.com": "ChangeMe123!",
}


def run():
    SessionFactory = _get_session_factory()
    with SessionFactory() as s_obj:
        s: Session = cast(Session, s_obj)
        for email, pw in SEED.items():
            u = s.query(User).filter(User.email == email).first()
            if u and not u.password_hash:
                u.password_hash = hash_password(pw)
                s.add(u)
        s.commit()
        print("✅ Password seed ensured")


if __name__ == "__main__":
    run()
