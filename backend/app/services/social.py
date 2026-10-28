import re
from fastapi import HTTPException
from sqlalchemy import select, delete, or_, and_
from app.models import User, Follow, FollowRequest, Block, Post, PostMedia, PostHashtag, Hashtag
from app.policies.access import user_access, blocked
from app.services.media import unbound_media
from app.repositories.common import insert_once, notify


def update_tags(db, post):
    db.execute(delete(PostHashtag).where(PostHashtag.post_id == post.id))
    for tag in set(re.findall(r"#([a-zA-Z0-9_]{1,50})", post.caption.lower())):
        insert_once(db, Hashtag, tag=tag)
        insert_once(db, PostHashtag, post_id=post.id, tag=tag)
    names = set(re.findall(r"@([a-zA-Z0-9_]{3,30})", post.caption.lower()))
    for user in db.scalars(select(User).where(User.username.in_(names), User.is_suspended.is_(False))):
        if not blocked(db, post.author_id, user.id):
            notify(db, user.id, post.author_id, "mention", post.id)


def create_post(db, user, data):
    if len({str(m.media_id) for m in data.media}) != len(data.media):
        raise HTTPException(422, "Duplicate media IDs")
    assets = [unbound_media(db, m.media_id, user.id) for m in data.media]
    if data.kind == "reel" and (len(assets) != 1 or not assets[0].mime_type.startswith("video/")):
        raise HTTPException(422, "A reel must contain exactly one video")
    post = Post(
        author_id=user.id,
        caption=data.caption,
        kind=data.kind,
        media=[PostMedia(media_id=a.id, position=i, alt_text=data.media[i].alt_text) for i, a in enumerate(assets)],
    )
    db.add(post)
    db.flush()
    update_tags(db, post)
    db.expire(post)
    return post


def follow(db, viewer, target):
    if viewer == target:
        raise HTTPException(422, "You cannot follow yourself")
    user = user_access(db, target, viewer, private=False)
    if db.get(Follow, (viewer, target)):
        return {"status": "following"}
    if user.is_private:
        insert_once(db, FollowRequest, follower_id=viewer, following_id=target)
        notify(db, target, viewer, "follow_request", viewer)
        return {"status": "requested"}
    insert_once(db, Follow, follower_id=viewer, following_id=target)
    notify(db, target, viewer, "follow", viewer)
    return {"status": "following"}


def unfollow(db, viewer, target):
    db.execute(delete(Follow).where(Follow.follower_id == viewer, Follow.following_id == target))
    db.execute(delete(FollowRequest).where(FollowRequest.follower_id == viewer, FollowRequest.following_id == target))


def block_user(db, viewer, target):
    if viewer == target:
        raise HTTPException(422, "You cannot block yourself")
    if not db.get(User, target):
        raise HTTPException(404, "Account not found")
    insert_once(db, Block, user_id=viewer, target_id=target)
    for model in (Follow, FollowRequest):
        db.execute(
            delete(model).where(
                or_(
                    and_(model.follower_id == viewer, model.following_id == target),
                    and_(model.follower_id == target, model.following_id == viewer),
                )
            )
        )
