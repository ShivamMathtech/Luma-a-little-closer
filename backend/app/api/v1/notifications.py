from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select, update, func, exists, or_, and_
from app.core.dependencies import DB, CurrentUser, CSRF
from app.models import Notification, Block, User
from app.repositories.common import paginate
from app.services.presenters import user_summary

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def eligible(user_id):
    return [
        Notification.user_id == user_id,
        ~exists().where(
            or_(
                and_(Block.user_id == user_id, Block.target_id == Notification.actor_id),
                and_(Block.target_id == user_id, Block.user_id == Notification.actor_id),
            )
        ),
        exists().where(User.id == Notification.actor_id, User.is_suspended.is_(False)),
    ]


@router.get("")
def notifications(db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(30, ge=1, le=50)):
    rows, nxt = paginate(db, select(Notification).where(*eligible(user.id)), Notification, cursor, limit)
    unread = db.scalar(
        select(func.count()).select_from(Notification).where(*eligible(user.id), Notification.is_read.is_(False))
    )
    return {
        "items": [
            {
                "id": r.id,
                "actor": user_summary(r.actor),
                "kind": r.kind,
                "target_id": r.target_id,
                "is_read": r.is_read,
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "unread_count": unread,
        "next_cursor": nxt,
    }


@router.post("/read-all", dependencies=[CSRF])
def read_all(db: DB, user: CurrentUser):
    db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    return {"ok": True}


@router.patch("/{id_}", dependencies=[CSRF])
def set_read(id_: str, db: DB, user: CurrentUser, is_read: bool = True):
    row = db.get(Notification, id_)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    row.is_read = is_read
    return {"ok": True}
