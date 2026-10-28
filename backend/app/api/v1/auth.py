from app.schemas.outputs import MeOut
from fastapi import APIRouter, Response, Request
from sqlalchemy import select, update
from app.core.dependencies import DB, CurrentUser, CSRF
from app.core.security import csrf_token, digest, password_hasher
from app.models import User, Session, VerificationToken, ResetToken
from app.schemas.inputs import Register, Login, EmailInput, TokenInput, Reset
from app.services import auth as service
from app.services.presenters import self_summary
from app.middleware.rate_limit import rate

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf")
def csrf(response: Response):
    value = csrf_token()
    service.cookie(response, "luma_csrf", value, 86400, httponly=True)
    return {"csrf_token": value}


@router.post("/register", status_code=201, dependencies=[CSRF], response_model=MeOut)
def register(data: Register, response: Response, request: Request, db: DB):
    rate(request, "register", 8)
    return service.register(db, data, response)


@router.post("/login", dependencies=[CSRF], response_model=MeOut)
def login(data: Login, response: Response, request: Request, db: DB):
    rate(request, "login-ip", 30)
    rate(request, "login-account", 8, data.login.lower())
    return service.login(db, data, response)


@router.post("/refresh", dependencies=[CSRF], response_model=MeOut)
def refresh(request: Request, response: Response, db: DB):
    rate(request, "refresh", 60)
    return service.refresh(db, request.cookies.get("luma_refresh", ""), response)


@router.post("/logout", dependencies=[CSRF])
def logout(request: Request, response: Response, db: DB):
    db.execute(
        update(Session)
        .where(Session.refresh_hash == digest(request.cookies.get("luma_refresh", "")))
        .values(revoked=True)
    )
    response.delete_cookie("luma_access", path="/")
    response.delete_cookie("luma_refresh", path="/")
    return {"ok": True}


@router.post("/logout-all", dependencies=[CSRF])
def logout_all(user: CurrentUser, db: DB, response: Response):
    db.execute(update(Session).where(Session.user_id == user.id).values(revoked=True))
    response.delete_cookie("luma_access", path="/")
    response.delete_cookie("luma_refresh", path="/")
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser):
    return self_summary(user)


@router.post("/verify-email", dependencies=[CSRF])
def verify(data: TokenInput, db: DB, request: Request):
    rate(request, "verify", 15)
    user = service.consume_token(db, VerificationToken, data.token)
    user.is_verified = True
    return {"ok": True}


@router.post("/resend-verification", dependencies=[CSRF])
def resend(user: CurrentUser, db: DB, request: Request):
    rate(request, "verification-mail", 3, user.id)
    if not user.is_verified:
        service.queue_token(db, user, "verify-email")
    return {"ok": True}


@router.post("/forgot-password", dependencies=[CSRF])
def forgot(data: EmailInput, db: DB, request: Request):
    rate(request, "password-recovery", 5)
    user = db.scalar(select(User).where(User.email == data.email.lower(), User.is_suspended.is_(False)))
    if user:
        service.queue_token(db, user, "reset-password")
    return {"ok": True, "message": "If an account exists, a recovery email will be delivered."}


@router.post("/reset-password", dependencies=[CSRF])
def reset(data: Reset, db: DB, request: Request):
    rate(request, "password-reset", 10)
    user = service.consume_token(db, ResetToken, data.token)
    user.password_hash = password_hasher.hash(data.password)
    db.execute(update(Session).where(Session.user_id == user.id).values(revoked=True))
    return {"ok": True}
