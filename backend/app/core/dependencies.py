from typing import Annotated
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models import Session, User
from app.core.security import digest, expired, check_csrf

DB = Annotated[DBSession, Depends(get_db)]


def current_user(request: Request, db: DB):
    raw = request.cookies.get("luma_access", "")
    session = db.scalar(select(Session).where(Session.access_hash == digest(raw), Session.revoked.is_(False)))
    if not session or expired(session.access_expires_at) or expired(session.expires_at):
        raise HTTPException(401, "Please sign in again")
    user = db.get(User, session.user_id)
    if not user or user.is_suspended:
        raise HTTPException(401, "Account is unavailable")
    request.state.session_id = session.id
    return user


CurrentUser = Annotated[User, Depends(current_user)]
CSRF = Depends(check_csrf)


def require_admin(user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


Admin = Annotated[User, Depends(require_admin)]
