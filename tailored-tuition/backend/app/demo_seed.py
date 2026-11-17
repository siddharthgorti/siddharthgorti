"""Development-only demo accounts, so in-person demos need no email server.

Creates (once) a verified guardian and three students with random passwords,
and writes the logins to backend/data/demo-accounts.txt (git-ignored). Refused
in production (see Settings.production_problems).
"""

from __future__ import annotations

import contextlib
import logging
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Guardian, Student, utcnow
from app.security.passwords import hash_password

log = logging.getLogger(__name__)

DEMO_EMAIL = "demo-guardian@example.com"
DEMO_STUDENTS = [("Asha", "demo1"), ("Ravi", "demo2"), ("Meera", "demo3")]
WORDS = [
    "maple",
    "river",
    "cobalt",
    "orbit",
    "lantern",
    "pepper",
    "summit",
    "falcon",
    "velvet",
    "quartz",
    "harbor",
    "meadow",
]


def _password() -> str:
    # e.g. "maple-orbit-3f9a2c": easy to type on a phone, ~2 billion combinations,
    # and login lockout (10 tries / 15 min) makes online guessing impractical.
    return f"{secrets.choice(WORDS)}-{secrets.choice(WORDS)}-{secrets.token_hex(3)}"


def seed_demo_accounts(db: Session, settings: Settings) -> None:
    if settings.app_env != "development":
        return
    if db.scalar(select(Guardian).where(Guardian.email == DEMO_EMAIL)):
        return  # already seeded; logins are in demo-accounts.txt
    lines = ["Tailored Tuition demo logins (development only; delete backend/data to reset)", ""]
    g_pw = _password()
    guardian = Guardian(
        name="Demo Guardian", email=DEMO_EMAIL, password_hash=hash_password(g_pw), email_verified_at=utcnow()
    )
    db.add(guardian)
    db.flush()
    lines += ["Parent/guardian login", f"  email:    {DEMO_EMAIL}", f"  password: {g_pw}", "", "Student logins"]
    for name, username in DEMO_STUDENTS:
        pw = _password()
        db.add(
            Student(
                guardian_id=guardian.id,
                name=name,
                username=username,
                password_hash=hash_password(pw),
                grade=settings.default_grade,
                board=settings.default_board,
                consent_given_at=utcnow(),
                consent_policy_version=settings.privacy_policy_version,
            )
        )
        lines.append(f"  {name:<6} username: {username}   password: {pw}")
    db.commit()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = settings.data_dir / "demo-accounts.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with contextlib.suppress(OSError):  # Windows ignores POSIX modes
        path.chmod(0o600)
    log.info("Demo accounts created. Logins are in %s", path)
