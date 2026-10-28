from datetime import timedelta
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select, exists, or_, func
from app.core.dependencies import DB, CurrentUser, CSRF
from app.models import Story, StoryView, User, Follow, now
from app.policies.access import visible_users, user_access, owner
from app.repositories.common import insert_once, paginate
from app.services.media import unbound_media
from app.services.presenters import user_summary, asset_summary
from app.schemas.inputs import StoryInput
from app.core.security import expired
from app.middleware.rate_limit import rate

router = APIRouter(prefix="/stories", tags=["Stories"])


@router.get("/feed")
def feed(db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(30, ge=1, le=50)):
    stmt = (
        select(Story)
        .join(User, Story.author_id == User.id)
        .where(
            Story.expires_at > now(),
            visible_users(user.id, hide_muted=True),
            or_(
                Story.author_id == user.id,
                exists().where(Follow.follower_id == user.id, Follow.following_id == Story.author_id),
            ),
        )
    )
    rows, nxt = paginate(db, stmt, Story, cursor, limit)
    ids = [r.id for r in rows]
    counts = dict(
        db.execute(
            select(StoryView.story_id, func.count()).where(StoryView.story_id.in_(ids)).group_by(StoryView.story_id)
        ).all()
    )
    seen = set(db.scalars(select(StoryView.story_id).where(StoryView.story_id.in_(ids), StoryView.user_id == user.id)))
    return {
        "items": [
            {
                "id": r.id,
                "author": user_summary(r.author),
                "media": asset_summary(r.media),
                "caption": r.caption,
                "expires_at": r.expires_at,
                "is_viewed": r.id in seen,
                "views_count": counts.get(r.id, 0) if r.author_id == user.id else None,
            }
            for r in rows
        ],
        "next_cursor": nxt,
    }


@router.post("", status_code=201, dependencies=[CSRF])
def create(data: StoryInput, db: DB, user: CurrentUser, request: Request):
    rate(request, "stories", 20, user.id)
    media = unbound_media(db, data.media_id, user.id)
    row = Story(author_id=user.id, media_id=media.id, caption=data.caption, expires_at=now() + timedelta(hours=24))
    db.add(row)
    db.flush()
    return {"id": row.id}


@router.post("/{story_id}/view", dependencies=[CSRF])
def view(story_id: str, db: DB, user: CurrentUser):
    row = db.get(Story, story_id)
    if not row or expired(row.expires_at):
        raise HTTPException(404, "Story expired or not found")
    user_access(db, row.author_id, user.id)
    insert_once(db, StoryView, story_id=row.id, user_id=user.id)
    return {"ok": True}


@router.get("/{story_id}/viewers")
def viewers(story_id: str, db: DB, user: CurrentUser):
    row = db.get(Story, story_id)
    if not row or row.author_id != user.id:
        raise HTTPException(404, "Story not found")
    rows = db.scalars(select(User).join(StoryView, StoryView.user_id == User.id).where(StoryView.story_id == story_id))
    return {"items": [user_summary(r) for r in rows]}


@router.delete("/{story_id}", dependencies=[CSRF])
def remove(story_id: str, db: DB, user: CurrentUser):
    row = db.get(Story, story_id)
    if not row:
        raise HTTPException(404, "Story not found")
    owner(row.author_id, user.id)
    db.delete(row)
    return {"ok": True}
