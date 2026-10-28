"""Persistent database outbox + scheduled cleanup. Run separately from the API."""

import argparse
import json
import logging
import smtplib
import time
import re
from datetime import timedelta
from email.message import EmailMessage
from sqlalchemy import select, delete, exists
from app.db.session import SessionLocal
from app.models import (
    MailOutbox,
    Media,
    PostMedia,
    Story,
    MessageAttachment,
    Profile,
    Session,
    VerificationToken,
    ResetToken,
    now,
)
from app.core.config import settings
from app.integrations.storage import storage

log = logging.getLogger("luma.worker")


def deliver_mail(row):
    if settings.mail_backend == "file":
        settings.mail_root.mkdir(parents=True, exist_ok=True)
        path = settings.mail_root / f"{row.id}.eml"
        path.write_text(f"To: {row.recipient}\nSubject: {row.subject}\n\n{row.body}", encoding="utf-8")
        path.chmod(0o600)
        return
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.smtp_from, row.recipient, row.subject
    message.set_content(row.body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def tick():
    stats = {"mail_delivered": 0, "mail_failed": 0, "unused_assets_removed": 0}
    with SessionLocal.begin() as db:
        rows = db.scalars(
            select(MailOutbox)
            .where(MailOutbox.sent_at.is_(None), MailOutbox.attempts < 5)
            .order_by(MailOutbox.created_at)
            .limit(20)
            .with_for_update(skip_locked=True)
        )
        for row in rows:
            row.attempts += 1
            try:
                deliver_mail(row)
                row.sent_at = now()
                row.body = "[delivered; content removed]"
                stats["mail_delivered"] += 1
            except Exception as exc:
                stats["mail_failed"] += 1
                log.error(
                    json.dumps({"event": "mail_delivery_failed", "job_id": row.id, "error_type": type(exc).__name__})
                )
        db.execute(delete(Story).where(Story.expires_at < now()))
        for cls in (Session, VerificationToken, ResetToken):
            db.execute(delete(cls).where(cls.expires_at < now()))
        db.execute(
            delete(MailOutbox)
            .where(MailOutbox.created_at < now() - timedelta(days=7))
            .execution_options(synchronize_session=False)
        )
        unused = db.scalars(
            select(Media)
            .where(
                Media.created_at < now() - timedelta(days=1),
                ~exists().where(PostMedia.media_id == Media.id),
                ~exists().where(Story.media_id == Media.id),
                ~exists().where(MessageAttachment.media_id == Media.id),
                ~exists().where(Profile.avatar_id == Media.id),
            )
            .with_for_update(skip_locked=True)
        )
        for asset in unused:
            # Recheck after taking the row lock: a publisher may have committed
            # while the initial cleanup query was taking its snapshot.
            attached = any(
                db.scalar(select(column).where(column == asset.id).limit(1)) is not None
                for column in (PostMedia.media_id, Story.media_id, MessageAttachment.media_id, Profile.avatar_id)
            )
            if attached:
                continue
            storage().delete(asset.object_key)
            db.delete(asset)
            stats["unused_assets_removed"] += 1
    return stats


def sweep_orphans():
    """Dedicated Luma bucket only; recognize generated names and keep a 24-hour grace period."""
    with SessionLocal() as db:
        keys = set(db.scalars(select(Media.object_key)))
    cutoff = now() - timedelta(days=1)
    for key, modified in storage().keys():
        if key not in keys and modified < cutoff and re.fullmatch(r"[a-f0-9]{32}\.(jpg|mp4|webm)", key):
            storage().delete(key)
    if settings.mail_backend == "file":
        for path in settings.mail_root.glob("*.eml"):
            if path.stat().st_mtime < (now() - timedelta(days=7)).timestamp():
                path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=settings.log_level)
    iterations = 0
    while True:
        try:
            started = time.perf_counter()
            stats = tick()
            if iterations % 120 == 0:
                sweep_orphans()
            iterations += 1
            log.info(
                json.dumps(
                    {
                        "event": "worker_tick_complete",
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        **stats,
                    }
                )
            )
        except Exception:
            log.error("worker_tick_failed")
            if args.once:
                raise
        if args.once:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
