"""Sign-up, email verification, login, password reset, logout, and "who am I"."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DB, guardian_out, student_out
from app.config import Settings
from app.models import EmailToken, Guardian, Student, utcnow
from app.security.auth import (
    GuardianDep,
    PrincipalDep,
    SettingsDep,
    _aware,
    clear_cookie,
    end_all_sessions,
    start_session,
)
from app.security.email import reset_email, send_email, verification_email
from app.security.passwords import DUMMY_HASH, hash_password, verify_password
from app.security.ratelimit import login_failures, signups
from app.security.tokens import hash_token, new_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VERIFY_HOURS, RESET_HOURS = 48, 1

GuardianPassword = Annotated[str, Field(min_length=10, max_length=128)]


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: GuardianPassword


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class GuardianLoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: GuardianPassword


class StudentLoginIn(BaseModel):
    username: str = Field(max_length=30)
    password: str = Field(max_length=128)


def _issue_link(db: Session, guardian: Guardian, purpose: str, settings: Settings) -> str:
    token, token_hash = new_token()
    hours = VERIFY_HOURS if purpose == "verify" else RESET_HOURS
    db.add(
        EmailToken(
            token_hash=token_hash,
            guardian_id=guardian.id,
            purpose=purpose,
            expires_at=utcnow() + timedelta(hours=hours),
        )
    )
    db.commit()
    path = "verify" if purpose == "verify" else "reset-password"
    return f"{settings.public_url.rstrip('/')}/{path}?token={token}"


def _consume(db: Session, token: str, purpose: str) -> Guardian:
    row = db.get(EmailToken, hash_token(token))
    if row is None or row.purpose != purpose or row.used_at is not None or _aware(row.expires_at) <= utcnow():
        raise HTTPException(400, "This link is invalid or has expired. Request a new one.")
    row.used_at = utcnow()
    return db.get(Guardian, row.guardian_id)


def _check_lockout(key: str) -> None:
    wait = login_failures.blocked(key)
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(429, f"Too many failed attempts. Try again in about {minutes} minute(s).")


@router.post("/guardian/signup", status_code=201)
def signup(body: SignupIn, response: Response, background: BackgroundTasks, db: DB, settings: SettingsDep):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    if signups.blocked("global"):
        raise HTTPException(429, "Sign-ups are busy right now. Please try again later.")
    if db.scalar(select(Guardian).where(Guardian.email == email)):
        raise HTTPException(409, "An account with this email already exists. Try logging in.")
    signups.hit("global")
    guardian = Guardian(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(guardian)
    db.commit()
    link = _issue_link(db, guardian, "verify", settings)
    background.add_task(send_email, settings, email, *verification_email(guardian.name, link))
    start_session(db, response, settings, guardian=guardian)
    return {
        "guardian": guardian_out(guardian, settings),
        "dev_verification_url": link if settings.dev_links_enabled else None,
    }


@router.post("/guardian/verify")
def verify(body: TokenIn, response: Response, db: DB, settings: SettingsDep):
    guardian = _consume(db, body.token, "verify")
    if guardian.email_verified_at is None:
        guardian.email_verified_at = utcnow()
    db.commit()
    start_session(db, response, settings, guardian=guardian)
    return {"guardian": guardian_out(guardian, settings)}


@router.post("/guardian/resend-verification")
def resend(guardian: GuardianDep, background: BackgroundTasks, db: DB, settings: SettingsDep):
    if guardian.email_verified_at is not None:
        return {"dev_verification_url": None}
    link = _issue_link(db, guardian, "verify", settings)
    background.add_task(send_email, settings, guardian.email, *verification_email(guardian.name, link))
    return {"dev_verification_url": link if settings.dev_links_enabled else None}


@router.post("/guardian/login")
def guardian_login(body: GuardianLoginIn, response: Response, db: DB, settings: SettingsDep):
    email = body.email.strip().lower()
    key = f"g:{email}"
    _check_lockout(key)
    guardian = db.scalar(select(Guardian).where(Guardian.email == email))
    # Always run one hash check so response time doesn't reveal whether the email exists.
    ok = verify_password(body.password, guardian.password_hash if guardian else DUMMY_HASH)
    if not (guardian and ok):
        login_failures.hit(key)
        raise HTTPException(401, "Email or password is incorrect.")
    login_failures.reset(key)
    start_session(db, response, settings, guardian=guardian)
    return {"guardian": guardian_out(guardian, settings)}


@router.post("/guardian/forgot-password", status_code=202)
def forgot(body: ForgotIn, background: BackgroundTasks, db: DB, settings: SettingsDep):
    email = body.email.strip().lower()
    guardian = db.scalar(select(Guardian).where(Guardian.email == email))
    link = None
    if guardian:
        link = _issue_link(db, guardian, "reset", settings)
        background.add_task(send_email, settings, email, *reset_email(guardian.name, link))
    # Same answer either way, so this can't be used to find out who has an account.
    return {"dev_reset_url": link if (link and settings.dev_links_enabled) else None}


@router.post("/guardian/reset-password")
def reset(body: ResetIn, response: Response, db: DB, settings: SettingsDep):
    guardian = _consume(db, body.token, "reset")
    guardian.password_hash = hash_password(body.password)
    if guardian.email_verified_at is None:  # they proved control of the inbox
        guardian.email_verified_at = utcnow()
    end_all_sessions(db, guardian_id=guardian.id)
    db.commit()
    login_failures.reset(f"g:{guardian.email}")
    start_session(db, response, settings, guardian=guardian)
    return {"guardian": guardian_out(guardian, settings)}


@router.post("/student/login")
def student_login(body: StudentLoginIn, response: Response, db: DB, settings: SettingsDep):
    username = body.username.strip().lower()
    key = f"s:{username}"
    _check_lockout(key)
    student = db.scalar(select(Student).where(Student.username == username))
    ok = verify_password(body.password, student.password_hash if student else DUMMY_HASH)
    if not (student and ok):
        login_failures.hit(key)
        raise HTTPException(401, "Username or password is incorrect.")
    login_failures.reset(key)
    start_session(db, response, settings, student=student)
    return {"student": student_out(student)}


@router.post("/logout", status_code=204)
def logout(p: PrincipalDep, response: Response, db: DB, settings: SettingsDep):
    from app.models import AuthSession

    row = db.get(AuthSession, p.token_hash)
    if row:
        db.delete(row)
        db.commit()
    clear_cookie(response, settings)
    response.status_code = 204
    return response


@router.get("/me")
def me(p: PrincipalDep, settings: SettingsDep):
    if p.role == "guardian":
        return {"role": "guardian", "guardian": guardian_out(p.guardian, settings)}
    return {"role": "student", "student": student_out(p.student)}
