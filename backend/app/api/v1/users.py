from app.schemas.outputs import MeOut, ProfileOut, UserOut, PageOut
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select, delete, or_, and_, exists
from app.core.dependencies import DB, CurrentUser, CSRF
from app.core.security import password_hasher
from app.middleware.rate_limit import rate
from app.models import User, Follow, FollowRequest, Block, Mute, Post, Comment, Message, SavedPost, Collection, AuditLog
from app.policies.access import user_access
from app.repositories.common import insert_once, notify, paginate
from app.schemas.inputs import ProfileUpdate, DeleteAccount
from app.services.presenters import user_summary, self_summary, profile_summary
from app.services.social import follow, unfollow, block_user
from app.services.media import unbound_media

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me", dependencies=[CSRF], response_model=MeOut)
def edit_me(data: ProfileUpdate, db: DB, user: CurrentUser):
    values = data.model_dump(exclude_unset=True)
    for key in ("display_name", "bio", "website"):
        if key in values and values[key] is not None:
            setattr(user.profile, key, values[key])
    if "avatar_id" in values:
        if data.avatar_id:
            media = unbound_media(db, data.avatar_id, user.id)
            if not media.mime_type.startswith("image/"):
                raise HTTPException(422, "Avatar must be an image")
        user.profile.avatar_id = str(data.avatar_id) if data.avatar_id else None
    if data.is_private is not None:
        user.is_private = data.is_private
        if not data.is_private:
            requests = list(db.scalars(select(FollowRequest).where(FollowRequest.following_id == user.id)))
            for request in requests:
                insert_once(db, Follow, follower_id=request.follower_id, following_id=user.id)
                notify(db, request.follower_id, user.id, "follow_accepted", user.id)
                db.delete(request)
    db.flush()
    return self_summary(user)


@router.get("/me/export")
def export(db: DB, user: CurrentUser, request: Request):
    rate(request, "account-export", 2, user.id)
    return {
        "account": self_summary(user),
        "posts": [
            {"id": p.id, "caption": p.caption, "created_at": p.created_at, "media_ids": [m.media_id for m in p.media]}
            for p in db.scalars(select(Post).where(Post.author_id == user.id))
        ],
        "comments": [
            {"post_id": c.post_id, "body": c.body, "created_at": c.created_at}
            for c in db.scalars(select(Comment).where(Comment.author_id == user.id))
        ],
        "sent_messages": [
            {
                "conversation_id": m.conversation_id,
                "body": m.body,
                "created_at": m.created_at,
                "media_ids": [a.media_id for a in m.attachments],
            }
            for m in db.scalars(select(Message).where(Message.sender_id == user.id))
        ],
        "following": list(db.scalars(select(Follow.following_id).where(Follow.follower_id == user.id))),
        "saved_post_ids": list(db.scalars(select(SavedPost.post_id).where(SavedPost.user_id == user.id))),
        "collections": [
            {"id": c.id, "name": c.name} for c in db.scalars(select(Collection).where(Collection.user_id == user.id))
        ],
    }


@router.delete("/me", dependencies=[CSRF])
def delete_account(data: DeleteAccount, db: DB, user: CurrentUser):
    if not password_hasher.verify(data.password, user.password_hash):
        raise HTTPException(403, "Incorrect password")
    db.add(AuditLog(actor_id=None, action="account_deleted", target_id=user.id, detail={}))
    db.delete(user)
    return {"ok": True}


@router.get("/me/follow-requests")
def requests(db: DB, user: CurrentUser, cursor: str | None = None, limit: int = Query(20, ge=1, le=50)):
    rows, nxt = paginate(
        db, select(FollowRequest).where(FollowRequest.following_id == user.id), FollowRequest, cursor, limit
    )
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([r.follower_id for r in rows])))}
    return {"items": [{"id": r.id, "user": user_summary(users[r.follower_id])} for r in rows], "next_cursor": nxt}


@router.post("/me/follow-requests/{request_id}/accept", dependencies=[CSRF])
def accept(request_id: str, db: DB, user: CurrentUser):
    row = db.get(FollowRequest, request_id)
    if not row or row.following_id != user.id:
        raise HTTPException(404, "Request not found")
    user_access(db, row.follower_id, user.id, private=False)
    insert_once(db, Follow, follower_id=row.follower_id, following_id=user.id)
    notify(db, row.follower_id, user.id, "follow_accepted", user.id)
    db.delete(row)
    return {"ok": True}


@router.delete("/me/follow-requests/{request_id}", dependencies=[CSRF])
def reject(request_id: str, db: DB, user: CurrentUser):
    db.execute(delete(FollowRequest).where(FollowRequest.id == request_id, FollowRequest.following_id == user.id))
    return {"ok": True}


@router.get("/me/relationships/{kind}")
def relationships(kind: str, db: DB, user: CurrentUser):
    if kind not in {"blocks", "mutes"}:
        raise HTTPException(404, "Not found")
    model = Block if kind == "blocks" else Mute
    rows = db.scalars(select(User).join(model, model.target_id == User.id).where(model.user_id == user.id))
    return {"items": [user_summary(r) for r in rows]}


@router.put("/{target_id}/block", dependencies=[CSRF])
def block(target_id: str, db: DB, user: CurrentUser):
    block_user(db, user.id, target_id)
    return {"ok": True}


@router.delete("/{target_id}/block", dependencies=[CSRF])
def unblock(target_id: str, db: DB, user: CurrentUser):
    db.execute(delete(Block).where(Block.user_id == user.id, Block.target_id == target_id))
    return {"ok": True}


@router.put("/{target_id}/mute", dependencies=[CSRF])
def mute(target_id: str, db: DB, user: CurrentUser):
    user_access(db, target_id, user.id, private=False)
    if target_id == user.id:
        raise HTTPException(422, "You cannot mute yourself")
    insert_once(db, Mute, user_id=user.id, target_id=target_id)
    return {"ok": True}


@router.delete("/{target_id}/mute", dependencies=[CSRF])
def unmute(target_id: str, db: DB, user: CurrentUser):
    db.execute(delete(Mute).where(Mute.user_id == user.id, Mute.target_id == target_id))
    return {"ok": True}


@router.post("/{target_id}/follow", dependencies=[CSRF])
def do_follow(target_id: str, db: DB, user: CurrentUser):
    return follow(db, user.id, target_id)


@router.delete("/{target_id}/follow", dependencies=[CSRF])
def do_unfollow(target_id: str, db: DB, user: CurrentUser):
    unfollow(db, user.id, target_id)
    return {"status": "none"}


@router.get("/{username}", response_model=ProfileOut)
def profile(username: str, db: DB, viewer: CurrentUser):
    user = db.scalar(select(User).where(User.username == username.lower()))
    if not user:
        raise HTTPException(404, "Account not found")
    user_access(db, user.id, viewer.id, private=False)
    return profile_summary(db, user, viewer.id)


@router.get("/{username}/{direction}", response_model=PageOut[UserOut])
def follow_list(
    username: str,
    direction: str,
    db: DB,
    viewer: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=50),
):
    if direction not in {"followers", "following"}:
        raise HTTPException(404, "Not found")
    target = db.scalar(select(User).where(User.username == username.lower()))
    if not target:
        raise HTTPException(404, "Account not found")
    user_access(db, target.id, viewer.id)
    join_on, condition = (
        (Follow.follower_id == User.id, Follow.following_id == target.id)
        if direction == "followers"
        else (Follow.following_id == User.id, Follow.follower_id == target.id)
    )
    stmt = (
        select(User)
        .join(Follow, join_on)
        .where(
            condition,
            User.is_suspended.is_(False),
            ~exists().where(
                or_(
                    and_(Block.user_id == viewer.id, Block.target_id == User.id),
                    and_(Block.target_id == viewer.id, Block.user_id == User.id),
                )
            ),
        )
    )
    rows, nxt = paginate(db, stmt, User, cursor, limit)
    return {"items": [user_summary(r) for r in rows], "next_cursor": nxt}
