from datetime import timedelta
from sqlalchemy import select
from app.models import Session, MailOutbox, now
from app.core.security import digest
from app.workers.run import tick
from app.core.config import settings


def test_registration_login_logout(account):
    client, user = account()
    assert user["username"] == "alice"
    assert "password_hash" not in user and "refresh_token" not in user
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "alice@example.com"
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"login": "ALICE", "password": "CorrectHorse123!"}).status_code == 200


def test_csrf_and_origin(account):
    c, _ = account()
    c.headers.pop("X-CSRF-Token")
    assert c.patch("/api/v1/users/me", json={"bio": "Bad"}).status_code == 403
    csrf = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    c.headers["X-CSRF-Token"] = csrf
    c.headers["Origin"] = "https://evil.example"
    assert c.post("/api/v1/auth/logout").status_code == 403


def test_validation_and_uniqueness(account):
    c, _ = account()
    data = {"username": "bob", "email": "bob@example.com", "display_name": "Bob", "password": "short"}
    assert c.post("/api/v1/auth/register", json=data).status_code == 422
    data.update(password="CorrectHorse123!", username="ALICE")
    assert c.post("/api/v1/auth/register", json=data).status_code == 409
    assert c.patch("/api/v1/users/me", json={"role": "admin"}).status_code == 422
    assert c.patch("/api/v1/users/me", json={"website": "javascript:alert(1)"}).status_code == 422


def test_refresh_rotation_reuse_and_expiry(account, db):
    c, u = account()
    old_refresh = c.cookies.get("luma_refresh")
    old_access = c.cookies.get("luma_access")
    session = db.scalar(select(Session).where(Session.access_hash == digest(old_access)))
    session.access_expires_at = now() - timedelta(seconds=1)
    db.commit()
    assert c.get("/api/v1/auth/me").status_code == 401
    assert c.post("/api/v1/auth/refresh").status_code == 200
    assert c.cookies.get("luma_refresh") != old_refresh
    assert c.get("/api/v1/auth/me").status_code == 200
    c.cookies.clear()
    c.cookies.set("luma_refresh", old_refresh)
    csrf = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    c.headers["X-CSRF-Token"] = csrf
    assert c.post("/api/v1/auth/refresh").status_code == 401
    db.expire_all()
    assert all(s.revoked for s in db.scalars(select(Session).where(Session.user_id == u["id"])))


def test_verify_reset_and_outbox(account, db):
    c, u = account()
    mail = db.scalar(select(MailOutbox).where(MailOutbox.recipient == u["email"]))
    token = mail.body.split("token=")[1].split()[0]
    assert c.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    assert c.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 400
    assert c.get("/api/v1/auth/me").json()["is_verified"]
    assert c.post("/api/v1/auth/forgot-password", json={"email": u["email"]}).status_code == 200
    reset = db.scalar(select(MailOutbox).where(MailOutbox.subject.like("Reset%")))
    token = reset.body.split("token=")[1].split()[0]
    assert (
        c.post("/api/v1/auth/reset-password", json={"token": token, "password": "NewPassword123!"}).status_code == 200
    )
    assert c.get("/api/v1/auth/me").status_code == 401
    assert c.post("/api/v1/auth/login", json={"login": "alice", "password": "NewPassword123!"}).status_code == 200
    tick()
    assert list(settings.mail_root.glob("*.eml"))


def test_account_export_delete_and_logout_all(account, post):
    c, u = account()
    p = post(c)
    assert c.get("/api/v1/users/me/export").json()["posts"][0]["id"] == p["id"]
    assert c.post("/api/v1/auth/logout-all").status_code == 200
    assert c.get("/api/v1/auth/me").status_code == 401
    c.post("/api/v1/auth/login", json={"login": "alice", "password": "CorrectHorse123!"})
    assert c.request("DELETE", "/api/v1/users/me", json={"password": "incorrect"}).status_code == 403
    assert c.request("DELETE", "/api/v1/users/me", json={"password": "CorrectHorse123!"}).status_code == 200
    assert c.get("/api/v1/auth/me").status_code == 401


def test_login_throttle(account, monkeypatch):
    from types import SimpleNamespace
    from collections import defaultdict
    from app.middleware.rate_limit import limiter

    monkeypatch.setattr("app.middleware.rate_limit.time", SimpleNamespace(time=lambda: 120.0))
    monkeypatch.setattr(limiter, "local", defaultdict(int))
    c, _ = account()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    statuses = [
        c.post("/api/v1/auth/login", json={"login": "alice", "password": "wrong"}).status_code for _ in range(9)
    ]
    assert statuses[:8] == [401] * 8
    assert statuses[8] == 429
