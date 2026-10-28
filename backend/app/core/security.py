import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from pwdlib import PasswordHash
from fastapi import HTTPException, Request
from app.core.config import settings

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def token() -> str:
    return secrets.token_urlsafe(40)


def utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def expired(dt):
    return utc(dt) <= datetime.now(timezone.utc)


def sign(value):
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def csrf_token():
    v = token()
    return v + "." + sign(v)


def check_csrf(request: Request):
    origin = request.headers.get("origin")
    cookie = request.cookies.get("luma_csrf", "")
    header = request.headers.get("x-csrf-token", "")
    value, _, signature = header.partition(".")
    if (
        origin not in settings.origins
        or not cookie
        or not hmac.compare_digest(cookie, header)
        or not hmac.compare_digest(signature, sign(value))
    ):
        raise HTTPException(403, "Invalid CSRF token or origin")
