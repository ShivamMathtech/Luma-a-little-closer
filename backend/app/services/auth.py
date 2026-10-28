from datetime import timedelta
from urllib.parse import quote
from fastapi import HTTPException
from sqlalchemy import select, update, delete
from app.core.config import settings
from app.core.security import token, digest, password_hasher, expired, DUMMY_HASH
from app.models import User, Profile, Session, VerificationToken, ResetToken, MailOutbox, now, uid
from app.services.presenters import self_summary


def cookie(response, name, value, age, *, httponly=True):
    response.set_cookie(
        name,
        value,
        max_age=age,
        httponly=httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def create_session(db, user, response, family=None):
    access, refresh = token(), token()
    row = Session(
        user_id=user.id,
        family_id=family or uid(),
        access_hash=digest(access),
        refresh_hash=digest(refresh),
        access_expires_at=now() + timedelta(minutes=settings.access_minutes),
        expires_at=now() + timedelta(days=settings.refresh_days),
    )
    db.add(row)
    cookie(response, "luma_access", access, settings.access_minutes * 60)
    cookie(response, "luma_refresh", refresh, settings.refresh_days * 86400)
    return self_summary(user)


def queue_token(db, user, purpose):
    cls = VerificationToken if purpose == "verify-email" else ResetToken
    raw = token()
    db.execute(delete(cls).where(cls.user_id == user.id))
    db.add(
        cls(
            user_id=user.id,
            token_hash=digest(raw),
            expires_at=now() + timedelta(hours=24 if purpose == "verify-email" else 1),
        )
    )
    link = f"{settings.frontend_url}/{purpose}?token={quote(raw)}"
    db.add(
        MailOutbox(
            recipient=user.email,
            subject="Verify your Luma email" if purpose == "verify-email" else "Reset your Luma password",
            body=f"Open this link to {purpose.replace('-', ' ')}:\n{link}\nIf you did not request this, ignore this email.",
        )
    )


def register(db, data, response):
    username, email = data.username.lower(), data.email.lower()
    if db.scalar(select(User.id).where((User.username == username) | (User.email == email))):
        raise HTTPException(409, "Username or email is already registered")
    user = User(
        username=username,
        email=email,
        password_hash=password_hasher.hash(data.password),
        profile=Profile(display_name=data.display_name),
    )
    db.add(user)
    db.flush()
    queue_token(db, user, "verify-email")
    return create_session(db, user, response)


def login(db, data, response):
    ident = data.login.lower()
    user = db.scalar(select(User).where((User.username == ident) | (User.email == ident)))
    valid = password_hasher.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or user.is_suspended:
        raise HTTPException(401, "Invalid login or password")
    return create_session(db, user, response)


def refresh(db, raw, response):
    row = db.scalar(select(Session).where(Session.refresh_hash == digest(raw)).with_for_update())
    if not row or expired(row.expires_at):
        raise HTTPException(401, "Session expired")
    if row.revoked:
        db.execute(update(Session).where(Session.family_id == row.family_id).values(revoked=True))
        db.commit()
        raise HTTPException(401, "Session reuse detected; sign in again")
    user = db.get(User, row.user_id)
    if not user or user.is_suspended:
        raise HTTPException(401, "Account unavailable")
    row.revoked = True
    return create_session(db, user, response, row.family_id)


def consume_token(db, cls, raw):
    row = db.scalar(select(cls).where(cls.token_hash == digest(raw)).with_for_update())
    if not row or expired(row.expires_at):
        raise HTTPException(400, "This link is invalid or expired")
    user = db.get(User, row.user_id)
    if not user or user.is_suspended:
        raise HTTPException(400, "This link is invalid or expired")
    db.delete(row)
    return user
