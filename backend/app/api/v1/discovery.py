from fastapi import APIRouter, Query, Request, HTTPException
from sqlalchemy import select, or_, and_, exists, func, delete
from app.core.dependencies import DB, CurrentUser, CSRF
from app.models import User, Profile, Block, PostHashtag, Post, Collection, CollectionItem, SavedPost
from app.policies.access import visible_users, post_access
from app.repositories.common import insert_once
from app.services.presenters import user_summary
from app.schemas.inputs import CollectionInput
from app.middleware.rate_limit import rate
from app.api.v1.posts import listing

router = APIRouter(tags=["Discovery and collections"])


@router.get("/search")
def search(request: Request, db: DB, user: CurrentUser, q: str = Query("", max_length=80)):
    rate(request, "search", 90, user.id)
    text = q.strip().lower().lstrip("#")
    pattern = "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    stmt = (
        select(User)
        .join(Profile)
        .where(
            User.is_suspended.is_(False),
            User.id != user.id,
            ~exists().where(
                or_(
                    and_(Block.user_id == user.id, Block.target_id == User.id),
                    and_(Block.target_id == user.id, Block.user_id == User.id),
                )
            ),
        )
    )
    if text:
        stmt = stmt.where(
            or_(User.username.ilike(pattern, escape="\\"), Profile.display_name.ilike(pattern, escape="\\"))
        )
    users = db.scalars(stmt.order_by(User.username).limit(20))
    tags = db.execute(
        select(PostHashtag.tag, func.count())
        .join(Post, Post.id == PostHashtag.post_id)
        .join(User, User.id == Post.author_id)
        .where(visible_users(user.id), PostHashtag.tag.ilike(pattern, escape="\\"))
        .group_by(PostHashtag.tag)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    return {"users": [user_summary(u) for u in users], "hashtags": [{"tag": t, "count": n} for t, n in tags]}


@router.get("/saved")
def saved(db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(20, ge=1, le=50)):
    return listing(db, user.id, cursor, limit, saved=True)


@router.get("/collections")
def collections(db: DB, user: CurrentUser):
    rows = db.scalars(select(Collection).where(Collection.user_id == user.id).order_by(Collection.created_at.desc()))
    return {"items": [{"id": r.id, "name": r.name} for r in rows]}


@router.post("/collections", status_code=201, dependencies=[CSRF])
def create(data: CollectionInput, db: DB, user: CurrentUser):
    row = Collection(user_id=user.id, name=data.name)
    db.add(row)
    db.flush()
    return {"id": row.id, "name": row.name}


def owned_collection(db, id_, uid):
    row = db.get(Collection, id_)
    if not row or row.user_id != uid:
        raise HTTPException(404, "Collection not found")
    return row


@router.patch("/collections/{id_}", dependencies=[CSRF])
def rename(id_: str, data: CollectionInput, db: DB, user: CurrentUser):
    row = owned_collection(db, id_, user.id)
    row.name = data.name
    return {"id": row.id, "name": row.name}


@router.delete("/collections/{id_}", dependencies=[CSRF])
def remove(id_: str, db: DB, user: CurrentUser):
    db.delete(owned_collection(db, id_, user.id))
    return {"ok": True}


@router.get("/collections/{id_}/posts")
def contents(id_: str, db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(20, ge=1, le=50)):
    owned_collection(db, id_, user.id)
    return listing(db, user.id, cursor, limit, collection=id_)


@router.put("/collections/{id_}/posts/{post_id}", dependencies=[CSRF])
def add(id_: str, post_id: str, db: DB, user: CurrentUser):
    owned_collection(db, id_, user.id)
    post_access(db, post_id, user.id)
    insert_once(db, CollectionItem, collection_id=id_, post_id=post_id)
    insert_once(db, SavedPost, user_id=user.id, post_id=post_id)
    return {"ok": True}


@router.delete("/collections/{id_}/posts/{post_id}", dependencies=[CSRF])
def discard(id_: str, post_id: str, db: DB, user: CurrentUser):
    owned_collection(db, id_, user.id)
    db.execute(delete(CollectionItem).where(CollectionItem.collection_id == id_, CollectionItem.post_id == post_id))
    return {"ok": True}
