"""Passwords (Argon2id) and revocable server-side sessions in an HttpOnly cookie."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Cookie, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .errors import ApiError, forbidden
from .models import AuthSession, ClassMember, Classroom, User

COOKIE_NAME = "csmasf_session"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        # Spend similar time on unknown accounts, to reduce account discovery by timing.
        _hasher.hash(password)
        return False
    try:
        return _hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(days=settings.session_days)
    db.add(AuthSession(token_hash=_hash_token(token), user_id=user.id, expires_at=expires))
    db.commit()
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.is_production,
        max_age=settings.session_days * 86400, path="/",
    )


def end_session(db: Session, token: str | None, response: Response) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _hash_token(token)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


def current_user(csmasf_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not csmasf_session:
        raise ApiError(401, "not_signed_in", "Please sign in to continue.")
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == _hash_token(csmasf_session)))
    if not row or row.expires_at < datetime.now(UTC):
        raise ApiError(401, "session_expired", "Your session has ended. Please sign in again.")
    user = db.get(User, row.user_id)
    if not user:
        raise ApiError(401, "session_expired", "Your session has ended. Please sign in again.")
    return user


def require_teacher(user: User = Depends(current_user)) -> User:
    if user.role != "teacher":
        raise forbidden("This page is only for teachers.")
    return user


def teacher_can_view_student(db: Session, teacher: User, student_id: str) -> bool:
    """A teacher sees a student only if that student joined one of the teacher's classes."""
    query = (
        select(ClassMember.user_id)
        .join(Classroom, Classroom.id == ClassMember.class_id)
        .where(Classroom.teacher_id == teacher.id, ClassMember.user_id == student_id)
    )
    return db.scalar(query) is not None
