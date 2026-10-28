import base64
import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models import Notification


def insert_once(db, model, **values):
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    stmt = insert(model).values(**values).on_conflict_do_nothing()
    return db.execute(stmt).rowcount > 0


def notify(db, recipient, actor, kind, target=None, key=None):
    if recipient != actor:
        insert_once(
            db,
            Notification,
            user_id=recipient,
            actor_id=actor,
            kind=kind,
            target_id=target,
            dedupe_key=key or f"{kind}:{recipient}:{actor}:{target}",
        )


def paginate(db, stmt, model, cursor=None, limit=20):
    if cursor:
        try:
            dt, id_ = json.loads(base64.urlsafe_b64decode(cursor.encode()))
            dt = datetime.fromisoformat(dt)
            stmt = stmt.where(or_(model.created_at < dt, and_(model.created_at == dt, model.id < id_)))
        except (ValueError, TypeError, KeyError):
            raise HTTPException(422, "Invalid pagination cursor")
    rows = list(db.scalars(stmt.order_by(model.created_at.desc(), model.id.desc()).limit(limit + 1)).unique())
    more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        base64.urlsafe_b64encode(json.dumps([rows[-1].created_at.isoformat(), rows[-1].id]).encode()).decode()
        if more
        else None
    )
    return rows, next_cursor
