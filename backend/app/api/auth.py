from __future__ import annotations

import hmac
import secrets

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ratelimit
from ..config import settings
from ..db import get_db
from ..errors import ApiError
from ..models import User
from ..schemas import DemoIn, LoginIn, OnboardingIn, RegisterIn, UserOut
from ..security import COOKIE_NAME, current_user, end_session, hash_password, start_session, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
DEFAULT_PREFERENCES = {"share_anonymous_outcomes": True, "auto_hints": True}


def to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role, is_demo=user.is_demo, experience_level=user.experience_level, goal=user.goal,
                   onboarding_completed=user.onboarding_completed, research_consent=user.research_consent, preferences=user.preferences or {})


def _limit(request: Request, action: str) -> None:
    host = request.client.host if request.client else "unknown"
    ratelimit.check(f"auth:{action}:{host}", settings.rate_auth_per_minute)


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    _limit(request, "register")
    email = payload.email.lower()
    if payload.role == "teacher":
        code = settings.teacher_invite_code
        if not code:
            raise ApiError(403, "teacher_signup_disabled", "Teacher sign-up is turned off on this server. Ask the administrator for access.")
        if not hmac.compare_digest(payload.invite_code or "", code):
            raise ApiError(403, "bad_invite_code", "That teacher invite code is not correct.")
    if db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "email_taken", "An account with this email already exists. Try signing in.")
    user = User(email=email, name=payload.name.strip(), password_hash=hash_password(payload.password), role=payload.role, preferences=dict(DEFAULT_PREFERENCES), onboarding_completed=payload.role == "teacher")
    db.add(user)
    db.commit()
    start_session(db, user, response)
    return to_user_out(user)


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    _limit(request, "login")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not verify_password(payload.password, user.password_hash if user else None) or user is None:
        raise ApiError(401, "bad_credentials", "That email and password do not match. Please check them and try again.")
    start_session(db, user, response)
    return to_user_out(user)


@router.post("/demo", response_model=UserOut)
def demo(payload: DemoIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    """Demo access is not authentication. It creates a throwaway account, and the UI labels it clearly."""
    if not settings.demo_mode:
        raise ApiError(403, "demo_disabled", "Demo access is turned off on this server.")
    _limit(request, "demo")
    if payload.role == "teacher":
        from ..seed import DEMO_TEACHER_EMAIL

        teacher = db.scalar(select(User).where(User.email == DEMO_TEACHER_EMAIL))
        if not teacher:
            raise ApiError(503, "demo_not_seeded", "Demo data has not been set up. Run: python -m app.seed")
        start_session(db, teacher, response)
        return to_user_out(teacher)
    token = secrets.token_hex(6)
    user = User(email=f"demo-{token}@demo.invalid", name="Demo learner", role="student", is_demo=True, preferences=dict(DEFAULT_PREFERENCES))
    db.add(user)
    db.commit()
    start_session(db, user, response)
    return to_user_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, csmasf_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> None:
    end_session(db, csmasf_session, response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return to_user_out(user)


@router.post("/onboarding", response_model=UserOut)
def onboarding(payload: OnboardingIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserOut:
    row = db.get(User, user.id)
    row.experience_level, row.goal, row.research_consent, row.onboarding_completed = payload.experience_level, payload.goal, payload.research_consent, True
    preferences = dict(row.preferences or {})
    preferences["show_walkthroughs"] = not payload.skip_walkthroughs and payload.experience_level in ("new", "some")
    preferences["density"] = "compact" if payload.experience_level == "advanced" else preferences.get("density", "comfortable")
    row.preferences = preferences
    db.commit()
    return to_user_out(row)


_ = COOKIE_NAME
